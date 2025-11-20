#!/bin/bash
#
# apply-docker-fixes.sh
# Wendet alle notwendigen Fixes für das Docker Build Environment an
# thomas@linuxmuster.net
# 20251120
#

set -e

echo "=== Applying Docker Build Environment Fixes ==="
echo ""

# Restore files if deleted
if [ ! -f "build/Dockerfile.template" ]; then
    echo "Restoring deleted build files..."
    git restore build/
fi

# Fix 1: Dockerfile.template - fakeroot hinzufügen
echo "[1/5] Adding fakeroot to Dockerfile.template..."
sed -i '/lintian \\/a\    fakeroot \\' build/Dockerfile.template

# Fix 2: Dockerfile.template - Korrektes Repository
echo "[2/5] Fixing linuxmuster.net repository URL..."
sed -i 's|https://archive.linuxmuster.net/|https://deb.linuxmuster.net/|g' build/Dockerfile.template
sed -i 's|archive.key|pub.gpg|g' build/Dockerfile.template
sed -i 's|linuxmuster.gpg|linuxmuster.net.gpg|g' build/Dockerfile.template
sed -i 's|linuxmuster.list|lmn73.list|g' build/Dockerfile.template
sed -i 's|RUN echo "deb|RUN mkdir -p /usr/share/keyrings \&\& \\\n    wget -qO- https://deb.linuxmuster.net/pub.gpg | gpg --dearmor > /usr/share/keyrings/linuxmuster.net.gpg \&\& \\\n    echo "deb [arch=amd64|' build/Dockerfile.template

# Fix 3: Dockerfile.template - Dynamische UID
echo "[3/5] Adding dynamic UID support..."
sed -i 's|RUN useradd -m -s /bin/bash builder|ARG USER_ID=1000\nRUN if id -u ${USER_ID} >/dev/null 2>\&1; then \\\n        existing_user=$(getent passwd ${USER_ID} | cut -d: -f1); \\\n        usermod -l builder -d /home/builder -m "$existing_user" || true; \\\n    else \\\n        useradd -m -s /bin/bash -u ${USER_ID} builder; \\\n    fi|' build/Dockerfile.template
sed -i 's|mkdir -p /build|mkdir -p /build /output|' build/Dockerfile.template
sed -i 's|chown builder:builder /build|chown ${USER_ID}:${USER_ID} /build /output|' build/Dockerfile.template

# Fix 4: generate-dockerfile.sh - Filter entfernen
echo "[4/5] Fixing Build-Depends filter..."
sed -i 's|grep -vE .*debhelper.*dh-python.*||g' build/generate-dockerfile.sh

# Fix 5: build-package.sh - Alle Fixes
echo "[5/5] Fixing build-package.sh..."
# USER_ID Parameter
sed -i 's|docker build -t|USER_ID=$(id -u)\n    docker build --build-arg USER_ID="$USER_ID" -t|' build/build-package.sh

# Clean-Logik
sed -i 's|rm -f ../linuxmuster-base7_\*|rm -rf .pybuild/\n    rm -rf src/*.egg-info/|' build/build-package.sh

# tmp-Verzeichnis
sed -i '/^echo ""$/a\# Create temporary output directory for build artifacts\nBUILD_TMP_DIR="$SCRIPT_DIR/tmp"\nrm -rf "$BUILD_TMP_DIR"\nmkdir -p "$BUILD_TMP_DIR"' build/build-package.sh

# .gitignore
if ! grep -q "/build/tmp/" .gitignore; then
    sed -i '/\/build\/Dockerfile/a\/build\/tmp\/' .gitignore
fi

echo ""
echo "✓ All fixes applied successfully!"
echo ""
echo "Run: ./build/build-package.sh --rebuild --clean"
