#!/bin/bash
#
# build-package.sh
# Build linuxmuster-base7 Debian package in Docker container
# thomas@linuxmuster.net
# 20251120
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="linuxmuster-base7-builder"
IMAGE_TAG="latest"
CONTAINER_NAME="lmn-base7-build-$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line options
REBUILD_IMAGE=0
INTERACTIVE=0
CLEAN_BUILD=0

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build linuxmuster-base7 Debian package in Docker container"
    echo ""
    echo "Options:"
    echo "  -r, --rebuild     Rebuild Docker image from scratch"
    echo "  -i, --interactive Enter interactive shell in build container"
    echo "  -c, --clean       Clean build artifacts before building"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                Build package with existing Docker image"
    echo "  $0 --rebuild      Rebuild Docker image and build package"
    echo "  $0 --interactive  Enter container for manual debugging"
    echo "  $0 --clean        Clean old builds and build fresh"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--rebuild)
            REBUILD_IMAGE=1
            shift
            ;;
        -i|--interactive)
            INTERACTIVE=1
            shift
            ;;
        -c|--clean)
            CLEAN_BUILD=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  linuxmuster-base7 Docker Package Builder         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Generate Dockerfile from template
echo -e "${YELLOW}[1/5] Generating Dockerfile from template...${NC}"
"$SCRIPT_DIR/generate-dockerfile.sh"
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to generate Dockerfile${NC}"
    exit 1
fi
echo ""

# Step 2: Build or check Docker image
if [ $REBUILD_IMAGE -eq 1 ] || ! docker image inspect "$IMAGE_NAME:$IMAGE_TAG" &>/dev/null; then
    echo -e "${YELLOW}[2/5] Building Docker image: $IMAGE_NAME:$IMAGE_TAG${NC}"
    echo -e "${BLUE}This may take several minutes on first run...${NC}"
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" "$SCRIPT_DIR"
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to build Docker image${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${YELLOW}[2/5] Using existing Docker image: $IMAGE_NAME:$IMAGE_TAG${NC}"
    echo -e "${BLUE}(Use --rebuild to rebuild image)${NC}"
fi
echo ""

# Step 3: Clean build artifacts if requested
if [ $CLEAN_BUILD -eq 1 ]; then
    echo -e "${YELLOW}[3/5] Cleaning build artifacts...${NC}"
    cd "$PROJECT_ROOT"
    rm -rf debian/linuxmuster-base7/
    rm -rf debian/.debhelper/
    rm -rf debian/files
    rm -rf debian/*.substvars
    rm -rf debian/*.log
    rm -f ../linuxmuster-base7_*.deb
    rm -f ../linuxmuster-base7_*.changes
    rm -f ../linuxmuster-base7_*.buildinfo
    rm -f ../linuxmuster-base7_*.dsc
    rm -f ../linuxmuster-base7_*.tar.*
    echo -e "${GREEN}✓ Build artifacts cleaned${NC}"
else
    echo -e "${YELLOW}[3/5] Skipping clean (use --clean to clean build artifacts)${NC}"
fi
echo ""

# Step 4: Run build or interactive shell
if [ $INTERACTIVE -eq 1 ]; then
    echo -e "${YELLOW}[4/5] Starting interactive shell in build container...${NC}"
    echo -e "${BLUE}Project directory mounted at: /build${NC}"
    echo -e "${BLUE}Run 'dpkg-buildpackage -us -uc' to build package${NC}"
    echo -e "${BLUE}Run 'exit' to leave container${NC}"
    echo ""

    docker run --rm -it \
        --name "$CONTAINER_NAME" \
        -v "$PROJECT_ROOT:/build" \
        -w /build \
        "$IMAGE_NAME:$IMAGE_TAG" \
        /bin/bash

    echo -e "${GREEN}✓ Interactive session ended${NC}"
else
    echo -e "${YELLOW}[4/5] Building Debian package...${NC}"
    echo -e "${BLUE}This may take a few minutes...${NC}"
    echo ""

    docker run --rm \
        --name "$CONTAINER_NAME" \
        -v "$PROJECT_ROOT:/build" \
        -w /build \
        "$IMAGE_NAME:$IMAGE_TAG" \
        dpkg-buildpackage -us -uc -b

    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}✗ Package build failed${NC}"
        echo -e "${YELLOW}Tip: Use --interactive to debug build issues${NC}"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}✓ Package built successfully${NC}"
fi
echo ""

# Step 5: Show results
echo -e "${YELLOW}[5/5] Build results:${NC}"
echo ""

# Find generated .deb files
DEB_FILES=$(find "$(dirname "$PROJECT_ROOT")" -maxdepth 1 -name "linuxmuster-base7_*.deb" -newer "$SCRIPT_DIR/build-package.sh" 2>/dev/null || true)

if [ -n "$DEB_FILES" ]; then
    echo -e "${GREEN}Generated packages:${NC}"
    for deb in $DEB_FILES; do
        SIZE=$(du -h "$deb" | cut -f1)
        echo -e "  ${GREEN}✓${NC} $(basename "$deb") (${SIZE})"
    done
    echo ""
    echo -e "${YELLOW}Installation command:${NC}"
    echo -e "  ${GREEN}sudo dpkg -i $(basename "$DEB_FILES" | head -1)${NC}"
    echo ""
    echo -e "${YELLOW}Package location:${NC}"
    echo -e "  ${BLUE}$(dirname "$PROJECT_ROOT")/${NC}"
else
    if [ $INTERACTIVE -eq 0 ]; then
        echo -e "${YELLOW}No .deb files found (build may have failed)${NC}"
    else
        echo -e "${BLUE}No new packages built in interactive mode${NC}"
    fi
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Build process completed                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
