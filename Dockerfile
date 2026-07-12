FROM python:3.9-slim

WORKDIR /app

# 1. Install standard build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    cmake \
    pkg-config \
    libao-dev \
    libfftw3-dev \
    librtlsdr-dev \
    ffmpeg \
    usbutils \
    udev \
    hwdata \
    libudev1 \
    nano \
    smbclient \
    && rm -rf /var/lib/apt/lists/*

# 2. Simplistic code compilation using generic root fallback paths
RUN git clone https://github.com/theori-io/nrsc5.git /tmp/nrsc5 && \
    mkdir -p /tmp/nrsc5/build && \
    cd /tmp/nrsc5/build && \
    cmake -DCMAKE_FIND_ROOT_PATH=/usr .. && \
    make && \
    make install && \
    ldconfig && \
    rm -rf /tmp/nrsc5

# 3. Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir Pillow

# 4. Copy app code and execute
COPY . .
RUN sed -i 's/\r$//' ttnhere.sh

CMD ["bash", "ttnhere.sh"]
