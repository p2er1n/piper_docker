# 需要保证：
# 1. pika_ros已经下载到当前文件夹
# 2. 切换到ros2分支
# 3. 递归下载了submodules
# 5. 宿主机配置了udev
# 6. 容器以privileged模式运行，并且挂载了/dev

FROM ros:humble AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV CONDA_DIR=/conda
ENV PATH=${CONDA_DIR}/bin:${PATH}

WORKDIR /pika
RUN apt-get update && apt install -y tar && rm -rf /var/lib/apt/lists/*
COPY ./pika_ros.tar.gz .
RUN tar -xzf ./pika_ros.tar.gz

WORKDIR ./pika_ros
RUN apt-get update && apt install -y software-properties-common && add-apt-repository ppa:ubuntu-toolchain-r/test -y && apt-get update && apt install -y \
    libjsoncpp-dev libpcap-dev python3-pcl build-essential zlib1g-dev libx11-dev libusb-1.0-0-dev \
    freeglut3-dev liblapacke-dev libopenblas-dev libatlas-base-dev cmake git libssl-dev pkg-config \
    libgtk-3-dev libglfw3-dev libgl1-mesa-dev libglu1-mesa-dev g++  python3-pip  libopenvr-dev \
    ros-humble-diagnostic-updater cutecom \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt install -y gcc-13 g++-13 libstdc++6 libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install opencv-python

WORKDIR /tmp
RUN cp /pika/pika_ros/source/librealsense-2.55.1.zip /pika/pika_ros/source/curl-7.75.0.zip .
RUN apt-get update && apt install -y unzip cmake \
    && rm -rf /var/lib/apt/lists/*
RUN unzip curl-7.75.0.zip && unzip librealsense-2.55.1.zip
RUN sed -i 's|/home/agilex/pika_ros/source/curl-7.75.0|/tmp/curl-7.75.0|g' ./librealsense-2.55.1/CMake/external_libcurl.cmake
WORKDIR ./librealsense-2.55.1
RUN mkdir build && cd build && cmake .. && make install

WORKDIR /pika/pika_ros/source
RUN unzip ./install.zip
RUN mv ./install ../
RUN chmod 777 -R ./install

RUN apt-get update && apt install -y ethtool can-utils \
    && rm -rf /var/lib/apt/lists/*

# 安装miniconda
WORKDIR /tmp
RUN apt-get update && apt install-y --no-install-recommends wget bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p ${CONDA_DIR} \
    && wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -u -p ${CONDA_DIR} \
    && rm /tmp/miniconda.sh \
    && conda config --system --set auto_activate_base false \
    && conda clean -afy
RUN conda --version && python --version

RUN conda create -y -n pika python=3.10
ENV ORIGIN_PATH=$PATH
ENV PATH=$CONDA_DIR/envs/pika/bin:$PATH
RUN conda install -y -n pika pinocchio==3.2.0 casadi==3.6.7 -c conda-forge \
    && conda clean -afy
RUN pip install lark numpy==2.0.2 empy==3.3.4 meshcat pyyaml piper-sdk opencv-python ur-rtde netifaces catkin_pkg
ENV PATH=$ORIGIN_PATH


FROM base AS pika
WORKDIR /pika/pika_api
COPY ./pika_api .
RUN pip install -r requirements.txt
CMD source /pika/pika_ros/install/setup.bash && python main.py --host 0.0.0.0 --port 8080

FROM base AS pika_remote_piper
WORKDIR /pika/pika_remote_piper
COPY ./pika_remote_piper_api .
RUN pip install -r requirements.txt
CMD source /pika/pika_ros/install/setup.bash && PATH=${CONDA_DIR}/envs/pika/bin:$PATH python main.py --host 0.0.0.0 --port 8080