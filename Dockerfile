FROM python:3.9

WORKDIR /app

# 1. Install standard runtime tools and hardware packages
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# 2. Compile nrsc5 without any complex path flags
RUN git clone https://github.com/theori-io/nrsc5.git /tmp/nrsc5 && \
    cd /tmp/nrsc5 && \
    mkdir build && cd build && \
    cmake .. && \
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
