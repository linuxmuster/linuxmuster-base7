# Dockerfile template for linuxmuster-base7 package build
# This file is processed by generate-dockerfile.sh to inject Build-Depends
# Base: Ubuntu 24.04 (Noble Numbat)

FROM ubuntu:24.04

LABEL maintainer="thomas@linuxmuster.net"
LABEL description="Build environment for linuxmuster-base7 Debian package"
LABEL version="1.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Berlin

# Update package lists and install base build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    devscripts \
    equivs \
    lintian \
    git \
    ca-certificates \
    wget \
    gnupg \
    lsb-release && \
    rm -rf /var/lib/apt/lists/*

# Add linuxmuster.net repository
RUN echo "deb [signed-by=/usr/share/keyrings/linuxmuster.gpg] https://archive.linuxmuster.net/ lmn73 main" > /etc/apt/sources.list.d/linuxmuster.list && \
    wget -qO- https://archive.linuxmuster.net/archive.key | gpg --dearmor > /usr/share/keyrings/linuxmuster.gpg

# Update package lists with linuxmuster repository
RUN apt-get update

# Install Build-Depends (injected by generate-dockerfile.sh)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-all \
    python3-setuptools \
    linuxmuster-common \
    python3-bcrypt \
    python3-bs4 \
    python3-lxml \
    python3-ipy \
    python3-apt \
    python3-netifaces \
    python3-dialog \
    python3-ldap3 \
    python3-netaddr \
    python3-paramiko \
    python3-requests \
    python3-urllib3 &&
 \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clean up apt cache to reduce image size
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create build user (non-root for security)
RUN useradd -m -s /bin/bash builder && \
    mkdir -p /build && \
    chown builder:builder /build

# Set working directory
WORKDIR /build

# Switch to build user
USER builder

# Default command shows build instructions
CMD ["bash", "-c", "echo 'linuxmuster-base7 Docker build environment ready.' && \
     echo 'Usage: docker run -v $(pwd):/build <image-name> dpkg-buildpackage -us -uc' && \
     bash"]
