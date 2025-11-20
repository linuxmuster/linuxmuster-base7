#!/bin/bash
#
# generate-dockerfile.sh
# Generate Dockerfile from template with Build-Depends from debian/control
# thomas@linuxmuster.net
# 20251120
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/Dockerfile.template"
OUTPUT_FILE="$SCRIPT_DIR/Dockerfile"
CONTROL_FILE="$SCRIPT_DIR/../debian/control"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== linuxmuster-base7 Dockerfile Generator ===${NC}"
echo ""

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

# Check if control file exists
if [ ! -f "$CONTROL_FILE" ]; then
    echo -e "${RED}Error: debian/control file not found: $CONTROL_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Reading Build-Depends from debian/control...${NC}"

# Extract Build-Depends from debian/control
# This handles multi-line Build-Depends and removes version constraints
BUILD_DEPENDS=$(awk '
    /^Build-Depends:/ {
        # Start reading Build-Depends
        in_build_depends = 1
        # Get everything after "Build-Depends:"
        sub(/^Build-Depends:/, "")
        line = $0
        next
    }
    in_build_depends {
        # If line starts with space, it continues Build-Depends
        if (/^ /) {
            line = line " " $0
        } else {
            # Build-Depends section ended
            in_build_depends = 0
        }
    }
    END {
        # Remove version constraints (>= X.Y), commas, and extra spaces
        gsub(/\([^)]*\)/, "", line)  # Remove (>= version)
        gsub(/,/, " ", line)          # Replace commas with spaces
        gsub(/[ \t]+/, " ", line)     # Normalize whitespace
        gsub(/^[ \t]+|[ \t]+$/, "", line)  # Trim
        print line
    }
' "$CONTROL_FILE")

if [ -z "$BUILD_DEPENDS" ]; then
    echo -e "${RED}Error: Could not extract Build-Depends from debian/control${NC}"
    exit 1
fi

echo -e "${GREEN}Build-Depends found:${NC}"
echo "$BUILD_DEPENDS" | tr ' ' '\n' | sed 's/^/  - /'
echo ""

# Filter out packages that might not be needed in Docker
# (debhelper, dh-python are already installed in base image)
FILTERED_DEPENDS=$(echo "$BUILD_DEPENDS" | tr ' ' '\n' | grep -v '^$' | grep -vE '^(debhelper|dh-python)$' | tr '\n' ' ')

echo -e "${YELLOW}Generating Dockerfile...${NC}"

# Create temporary file with Build-Depends installation section
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << 'INSTALL_EOF'
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
INSTALL_EOF

# Add each package on a new line
for pkg in $FILTERED_DEPENDS; do
    echo "    $pkg \\" >> "$TEMP_FILE"
done

# Add cleanup commands (remove last backslash from last package)
sed -i '$ s| \\$| \&\& \\|' "$TEMP_FILE"
cat >> "$TEMP_FILE" << 'CLEANUP_EOF'
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
CLEANUP_EOF

# Replace placeholder in template with generated install section
awk '
    /# BUILD_DEPENDS_PLACEHOLDER/ {
        while ((getline line < "'"$TEMP_FILE"'") > 0) {
            print line
        }
        next
    }
    { print }
' "$TEMPLATE_FILE" > "$OUTPUT_FILE"

# Clean up temp file
rm -f "$TEMP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dockerfile generated successfully: $OUTPUT_FILE${NC}"
    echo ""
    echo -e "${YELLOW}To build the Docker image, run:${NC}"
    echo -e "  ${GREEN}cd build && docker build -t linuxmuster-base7-builder .${NC}"
    echo ""
    echo -e "${YELLOW}Or use the build script:${NC}"
    echo -e "  ${GREEN}./build/build-package.sh${NC}"
else
    echo -e "${RED}✗ Error generating Dockerfile${NC}"
    exit 1
fi
