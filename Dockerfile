FROM python:3.9

WORKDIR /app

# 1. Added libjpeg-dev and zlib1g-dev for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    cmake \
    build-essential \
    libao-dev \
    libfftw3-dev \
    librtlsdr-dev \
    libjpeg-dev \
    zlib1g-dev \
    ffmpeg \
    usbutils \
    udev \
    hwdata \
    libudev1 \
    nano \
    smbclient \
    && rm -rf /var/lib/apt/lists/*

# 2. Compile nrsc5
RUN git clone https://github.com /tmp/nrsc5 && \
    cd /tmp/nrsc5 && \
    mkdir build && cd build && \
    cmake .. && \
    make && \
    make install && \
    ldconfig && \
    rm -rf /tmp/nrsc5

# 3. Force pip to rebuild Pillow with the new image libraries
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --force-reinstall Pillow

# 4. Copy app code and execute
COPY . .
RUN sed -i 's/\r$//' ttnhere.sh

CMD ["bash", "ttnhere.sh"]
COPY . .
RUN sed -i 's/\r$//' ttnhere.sh

CMD ["bash", "ttnhere.sh"]
CMD ["bash", "ttnhere.sh"]
