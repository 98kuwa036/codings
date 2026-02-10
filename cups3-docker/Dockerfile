# =============================================================================
# Dockerfile: OpenPrinting CUPS 3.0 Build Environment
# =============================================================================
# Builds the three CUPS 3.0 components from source:
#   1. libcups  (v3.0.0 stable)  - CUPS 3.x library and tools
#   2. PAPPL   (v2.x master)     - Printer Application Framework (libcups3-only)
#   3. cups-local (master)       - Local printing server
#   4. cups-sharing (master)     - Sharing/network printing server
#
# Architecture: x86_64 (amd64) Linux
# Base: Ubuntu 24.04 LTS
#
# References:
#   https://openprinting.github.io/cups/cups3.html
#   https://github.com/OpenPrinting/libcups
#   https://github.com/OpenPrinting/cups-local
#   https://github.com/OpenPrinting/cups-sharing
#   https://github.com/michaelrsweet/pappl
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build all CUPS 3.0 components from source
# ---------------------------------------------------------------------------
FROM ubuntu:24.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
ARG LIBCUPS_VERSION=v3.0.0
ARG PAPPL_BRANCH=master
ARG CUPS_LOCAL_BRANCH=master
ARG CUPS_SHARING_BRANCH=master

# Install all build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf \
    build-essential \
    git \
    ca-certificates \
    pkg-config \
    # libcups dependencies
    libavahi-client-dev \
    libnss-mdns \
    libpng-dev \
    libssl-dev \
    zlib1g-dev \
    # PAPPL additional dependencies
    libjpeg-dev \
    libpam0g-dev \
    libusb-1.0-0-dev \
    # cups-local additional dependencies (D-Bus / systemd)
    libdbus-1-dev \
    libsystemd-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# ---------------------------------------------------------------------------
# Step 1: Build libcups v3.0.0
# ---------------------------------------------------------------------------
RUN echo "=== Building libcups ${LIBCUPS_VERSION} ===" \
    && git clone --recurse-submodules https://github.com/OpenPrinting/libcups.git \
    && cd libcups \
    && git checkout ${LIBCUPS_VERSION} \
    && git submodule update --init --recursive \
    && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig \
    && echo "=== libcups ${LIBCUPS_VERSION} installed ==="

# ---------------------------------------------------------------------------
# Step 2: Build PAPPL v2.x (master branch, libcups3-only)
# ---------------------------------------------------------------------------
# cups-local and cups-sharing require PAPPL >= 2.0 (pkg-config: pappl2).
# PAPPL v2.0 has not been formally released yet; the master branch is
# the libcups3-only development line approaching v2.0.
RUN echo "=== Building PAPPL (${PAPPL_BRANCH}) ===" \
    && git clone https://github.com/michaelrsweet/pappl.git \
    && cd pappl \
    && git checkout ${PAPPL_BRANCH} \
    && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig \
    && echo "=== PAPPL installed ==="

# ---------------------------------------------------------------------------
# Step 3: Build cups-local (alpha, master)
# ---------------------------------------------------------------------------
RUN echo "=== Building cups-local (${CUPS_LOCAL_BRANCH}) ===" \
    && git clone https://github.com/OpenPrinting/cups-local.git \
    && cd cups-local \
    && git checkout ${CUPS_LOCAL_BRANCH} \
    && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig \
    && echo "=== cups-local installed ==="

# ---------------------------------------------------------------------------
# Step 4: Build cups-sharing (alpha, master)
# ---------------------------------------------------------------------------
# cups-sharing is the least mature component of CUPS 3.0. It may not have
# compilable source code yet. We attempt the build but allow it to fail
# gracefully so the rest of the image remains usable.
RUN echo "=== Building cups-sharing (${CUPS_SHARING_BRANCH}) ===" \
    && git clone https://github.com/OpenPrinting/cups-sharing.git \
    && cd cups-sharing \
    && git checkout ${CUPS_SHARING_BRANCH} \
    && ( ./configure --prefix=/usr/local \
         && make -j"$(nproc)" \
         && make install \
         && ldconfig \
         && echo "=== cups-sharing installed ===" \
       ) || echo "=== WARNING: cups-sharing build failed (expected for early alpha) ==="

# ---------------------------------------------------------------------------
# Stage 2: Runtime image (slim)
# ---------------------------------------------------------------------------
FROM ubuntu:24.04 AS runtime

ARG DEBIAN_FRONTEND=noninteractive

LABEL maintainer="cups3-docker"
LABEL description="OpenPrinting CUPS 3.0 (libcups + cups-local + cups-sharing)"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    avahi-daemon \
    libnss-mdns \
    libavahi-client3 \
    libpng16-16t64 \
    libssl3t64 \
    zlib1g \
    libjpeg8 \
    libpam0g \
    libusb-1.0-0 \
    libdbus-1-3 \
    libsystemd0 \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# Copy built artifacts from builder stage
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /usr/local/sbin/ /usr/local/sbin/
COPY --from=builder /usr/local/lib/ /usr/local/lib/
COPY --from=builder /usr/local/include/ /usr/local/include/
COPY --from=builder /usr/local/share/ /usr/local/share/
COPY --from=builder /usr/local/etc/ /usr/local/etc/

# Refresh shared library cache
RUN ldconfig

# Create required directories
RUN mkdir -p /var/spool/cups /var/log/cups /var/run/cups /etc/cups

# Copy entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# IPP port (cups-sharing)
EXPOSE 631

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["cups-local"]
