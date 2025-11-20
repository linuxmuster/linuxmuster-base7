# Docker Build Environment Fixes

Diese Datei dokumentiert alle notwendigen Fixes für das Docker Build Environment.

## 1. Dockerfile.template

### Zeile 22: fakeroot hinzufügen
```dockerfile
    fakeroot \
```

### Zeilen 30-33: Korrektes linuxmuster.net Repository
```dockerfile
# Add linuxmuster.net repository
RUN mkdir -p /usr/share/keyrings && \
    wget -qO- https://deb.linuxmuster.net/pub.gpg | gpg --dearmor > /usr/share/keyrings/linuxmuster.net.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/linuxmuster.net.gpg] https://deb.linuxmuster.net/ lmn73 main" > /etc/apt/sources.list.d/lmn73.list
```

### Zeilen 45-57: Dynamische UID und /output-Verzeichnis
```dockerfile
# Create build user (non-root for security)
# Use host user's UID for permission compatibility
ARG USER_ID=1000
RUN if id -u ${USER_ID} >/dev/null 2>&1; then \
        # UID already exists, modify existing user
        existing_user=$(getent passwd ${USER_ID} | cut -d: -f1); \
        usermod -l builder -d /home/builder -m "$existing_user" || true; \
    else \
        # UID doesn't exist, create new user
        useradd -m -s /bin/bash -u ${USER_ID} builder; \
    fi && \
    mkdir -p /build /output && \
    chown ${USER_ID}:${USER_ID} /build /output
```

## 2. generate-dockerfile.sh

### Zeilen 78-79: Filter entfernen
```bash
# Filter out empty entries only
FILTERED_DEPENDS=$(echo "$BUILD_DEPENDS" | tr ' ' '\n' | grep -v '^$' | tr '\n' ' ')
```

## 3. build-package.sh

### Zeilen 99-115: USER_ID Parameter
```bash
# Step 2: Build or check Docker image
if [ $REBUILD_IMAGE -eq 1 ] || ! docker image inspect "$IMAGE_NAME:$IMAGE_TAG" &>/dev/null; then
    echo -e "${YELLOW}[2/5] Building Docker image: $IMAGE_NAME:$IMAGE_TAG${NC}"
    echo -e "${BLUE}This may take several minutes on first run...${NC}"
    # Pass current user's UID to Docker build for permission compatibility
    USER_ID=$(id -u)
    docker build --build-arg USER_ID="$USER_ID" -t "$IMAGE_NAME:$IMAGE_TAG" "$SCRIPT_DIR"
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
```

### Zeilen 115-136: Clean-Logik verbessern
```bash
# Step 3: Clean build artifacts if requested
if [ $CLEAN_BUILD -eq 1 ]; then
    echo -e "${YELLOW}[3/5] Cleaning build artifacts...${NC}"
    cd "$PROJECT_ROOT"
    rm -rf debian/linuxmuster-base7/
    rm -rf debian/.debhelper/
    rm -rf debian/files
    rm -rf debian/*.substvars
    rm -rf debian/*.log
    rm -rf .pybuild/
    rm -rf src/*.egg-info/
    echo -e "${GREEN}✓ Build artifacts cleaned${NC}"
else
    echo -e "${YELLOW}[3/5] Skipping clean (use --clean to clean build artifacts)${NC}"
fi
echo ""

# Create temporary output directory for build artifacts
BUILD_TMP_DIR="$SCRIPT_DIR/tmp"
rm -rf "$BUILD_TMP_DIR"
mkdir -p "$BUILD_TMP_DIR"
```

### Zeilen 154-180: Docker Build mit Parent Mount und tmp
```bash
else
    echo -e "${YELLOW}[4/5] Building Debian package...${NC}"
    echo -e "${BLUE}This may take a few minutes...${NC}"
    echo ""

    # Clean up any existing build artifacts in container as root
    docker run --rm \
        --name "$CONTAINER_NAME-cleanup" \
        -v "$PROJECT_ROOT:/build" \
        -w /build \
        --user root \
        "$IMAGE_NAME:$IMAGE_TAG" \
        bash -c "rm -rf .pybuild debian/linuxmuster-base7 debian/.debhelper debian/files debian/*.substvars debian/*.log || true"

    # Mount project directory's parent and tmp directory
    # dpkg-buildpackage writes to .. so we need to mount the parent
    PROJECT_PARENT="$(dirname "$PROJECT_ROOT")"
    PROJECT_NAME="$(basename "$PROJECT_ROOT")"

    docker run --rm \
        --name "$CONTAINER_NAME" \
        -v "$PROJECT_PARENT:/workspace" \
        -v "$BUILD_TMP_DIR:/output" \
        -w "/workspace/$PROJECT_NAME" \
        "$IMAGE_NAME:$IMAGE_TAG" \
        bash -c "dpkg-buildpackage -us -uc -b; mv /workspace/linuxmuster-base7_*.deb /workspace/linuxmuster-base7_*.changes /workspace/linuxmuster-base7_*.buildinfo /output/ 2>/dev/null || true"
```

### Zeilen 183-214: Move files from tmp to output
```bash
    echo ""
    echo -e "${GREEN}✓ Package built successfully${NC}"

    # Move package files from tmp to output directory
    echo ""
    echo -e "${YELLOW}[4.5/5] Moving package files to output directory...${NC}"

    # Create output directory if it doesn't exist (relative to PROJECT_ROOT)
    cd "$PROJECT_ROOT"
    mkdir -p "$OUTPUT_DIR"

    # Move files from tmp to output directory
    PACKAGE_FILES=$(find "$BUILD_TMP_DIR" -maxdepth 1 -type f \( \
        -name "linuxmuster-base7_*.deb" -o \
        -name "linuxmuster-base7_*.changes" -o \
        -name "linuxmuster-base7_*.buildinfo" \
        \) 2>/dev/null || true)

    if [ -n "$PACKAGE_FILES" ]; then
        FILE_COUNT=0
        for file in $PACKAGE_FILES; do
            mv "$file" "$OUTPUT_DIR/"
            FILE_COUNT=$((FILE_COUNT + 1))
        done
        echo -e "${GREEN}✓ Moved $FILE_COUNT file(s) to $OUTPUT_DIR${NC}"

        # Clean up tmp directory
        rm -rf "$BUILD_TMP_DIR"
    else
        echo -e "${YELLOW}⚠ No package files found in tmp directory${NC}"
    fi
fi
echo ""
```

## 4. .gitignore

Zeile 11 hinzufügen:
```
/build/tmp/
```
