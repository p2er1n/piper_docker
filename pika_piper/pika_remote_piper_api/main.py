import argparse
import os
import queue
import subprocess
import threading
from collections import deque

from flask import Flask, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)


class ProcessManager:
    def __init__(self, buffer_lines=500):
        self._lock = threading.Lock()
        self._proc = None
        self._reader = None
        self._clients = set()
        self._buffer = deque(maxlen=buffer_lines)

    def start(self, cmd, cwd=None, env=None):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                raise RuntimeError("process already running")

            popen_env = os.environ.copy()
            if env:
                popen_env.update(env)

            self._proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=popen_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=isinstance(cmd, str),
            )
            self._reader = threading.Thread(target=self._read_output, daemon=True)
            self._reader.start()
            return self._proc.pid

    def stop(self, timeout=5):
        with self._lock:
            proc = self._proc
        if not proc or proc.poll() is not None:
            return None

        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=timeout)

        return proc.returncode

    def register_client(self):
        q = queue.Queue()
        with self._lock:
            self._clients.add(q)
            buffer_snapshot = list(self._buffer)
        return q, buffer_snapshot

    def unregister_client(self, q):
        with self._lock:
            self._clients.discard(q)

    def status(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                return {"running": True, "pid": self._proc.pid}
            return {"running": False, "pid": None}

    def _broadcast(self, line):
        with self._lock:
            self._buffer.append(line)
            clients = list(self._clients)
        for q in clients:
            try:
                q.put_nowait(line)
            except queue.Full:
                pass

    def _read_output(self):
        proc = self._proc
        if not proc or not proc.stdout:
            return

        for line in proc.stdout:
            self._broadcast(line.rstrip("\n"))

        code = proc.poll()
        self._broadcast(f"[process exited] code={code}")
        with self._lock:
            self._proc = None


manager = ProcessManager()


@app.post("/start")
def start_process():
    cmd = [
        "ros2", "launch", "pika_remote_piper", "teleop_rand_single_piper.launch.py",
    ]
    try:
        pid = manager.start(cmd)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"pid": pid})


@app.post("/stop")
def stop_process():
    code = manager.stop()
    if code is None:
        return jsonify({"status": "not running"}), 200
    return jsonify({"status": "stopped", "code": code})


@sock.route("/log")
def log_stream(ws):
    q, buffer_snapshot = manager.register_client()
    try:
        for line in buffer_snapshot:
            ws.send(line)

        while True:
            try:
                line = q.get(timeout=1.0)
                ws.send(line)
            except queue.Empty:
                if not ws.connected:
                    break
    finally:
        manager.unregister_client(q)


@app.get("/status")
def status():
    return jsonify(manager.status())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pika Remote Piper API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port)
