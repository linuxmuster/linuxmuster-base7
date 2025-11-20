# Docker Build Environment for linuxmuster-base7

This directory contains a Docker-based build environment for creating linuxmuster-base7 Debian packages in a clean, reproducible Ubuntu 24.04 environment.

## Quick Start

```bash
# Build the package
./build/build-package.sh

# Rebuild Docker image and build package
./build/build-package.sh --rebuild

# Interactive mode for debugging
./build/build-package.sh --interactive

# Clean build
./build/build-package.sh --clean
```

## Files Overview

- **`Dockerfile.template`**: Template for Docker image with placeholders
- **`generate-dockerfile.sh`**: Generates actual Dockerfile from template by reading Build-Depends from `debian/control`
- **`build-package.sh`**: Main build script with options for rebuild, interactive mode, and clean builds
- **`.dockerignore`**: Excludes unnecessary files from Docker build context

## How It Works

### 1. Dockerfile Generation

The `generate-dockerfile.sh` script:
- Reads Build-Depends from `debian/control`
- Parses package names and removes version constraints
- Injects packages into Dockerfile template
- Generates final `Dockerfile`

### 2. Docker Image

The Docker image is based on Ubuntu 24.04 and includes:
- Base build tools (debhelper, devscripts, equivs, lintian)
- linuxmuster.net repository configured
- All Build-Depends from debian/control
- Non-root `builder` user for security

### 3. Package Build

The build process:
1. Generates Dockerfile from template
2. Builds Docker image (or uses cached image)
3. Mounts project directory into container
4. Runs `dpkg-buildpackage -us -uc -b`
5. Outputs .deb package to parent directory

## Build Options

### Standard Build
```bash
./build/build-package.sh
```
- Uses cached Docker image if available
- Builds package with default options
- Outputs .deb to parent directory

### Rebuild Docker Image
```bash
./build/build-package.sh --rebuild
```
- Forces rebuild of Docker image
- Useful after updating Build-Depends in debian/control
- Ensures all dependencies are up-to-date

### Interactive Mode
```bash
./build/build-package.sh --interactive
```
- Starts interactive bash shell in build container
- Project mounted at `/build`
- Useful for debugging build issues
- Run `dpkg-buildpackage -us -uc` manually

### Clean Build
```bash
./build/build-package.sh --clean
```
- Removes all build artifacts before building
- Ensures a completely fresh build
- Cleans debian/linuxmuster-base7/, *.deb, etc.

## Requirements

- Docker installed and running
- User must have Docker permissions (`docker` group)
- Sufficient disk space (~1GB for image + build artifacts)

## Troubleshooting

### Build Fails

1. **Check Build-Depends**:
   ```bash
   ./build/generate-dockerfile.sh
   ```
   Verify all packages are available in Ubuntu 24.04 + linuxmuster.net repo

2. **Rebuild Image**:
   ```bash
   ./build/build-package.sh --rebuild
   ```
   Forces fresh image build with latest dependencies

3. **Interactive Debug**:
   ```bash
   ./build/build-package.sh --interactive
   # Inside container:
   dpkg-buildpackage -us -uc
   ```
   Build manually to see detailed error messages

### Docker Permission Denied

Add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Disk Space Issues

Clean up Docker:
```bash
docker system prune -a
```

## Output Location

Built packages are placed in the parent directory of the project:
```
/home/thomas/lmndev/base73/
├── linuxmuster-base7_7.3.29_all.deb
├── linuxmuster-base7_7.3.29.buildinfo
└── linuxmuster-base7_7.3.29_amd64.changes
```

## Manual Docker Commands

If you prefer manual control:

```bash
# Generate Dockerfile
cd build
./generate-dockerfile.sh

# Build image
docker build -t linuxmuster-base7-builder .

# Run build
docker run --rm \
  -v $(pwd)/..:/build \
  -w /build \
  linuxmuster-base7-builder \
  dpkg-buildpackage -us -uc -b
```

## Notes

- Docker image is tagged as `linuxmuster-base7-builder:latest`
- Build artifacts are created by non-root `builder` user (UID 1000)
- Container is automatically removed after build (`--rm` flag)
- linuxmuster.net repository GPG key is added during image build
- Ubuntu 24.04 (Noble) is used as base for compatibility

## Maintenance

### Update Dependencies

When Build-Depends change in `debian/control`:
```bash
./build/build-package.sh --rebuild
```

### Clean Docker Images

Remove old build images:
```bash
docker rmi linuxmuster-base7-builder:latest
docker system prune -a
```

### Verify Image Contents

Inspect what's in the Docker image:
```bash
docker run --rm -it linuxmuster-base7-builder:latest bash
```
