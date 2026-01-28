#!/bin/bash
#
# Build the Search-ADS server as a PyInstaller sidecar for Tauri
#

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "==> Building Search-ADS server sidecar..."

# Determine target triple
if command -v rustc &> /dev/null; then
    TARGET_TRIPLE=$(rustc -Vv | grep host | cut -f2 -d' ')
else
    # Fallback for macOS
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        TARGET_TRIPLE="aarch64-apple-darwin"
    else
        TARGET_TRIPLE="x86_64-apple-darwin"
    fi
fi

echo "    Target triple: $TARGET_TRIPLE"

# Ensure PyInstaller is installed
if ! pip show pyinstaller &> /dev/null; then
    echo "==> Installing PyInstaller..."
    pip install pyinstaller
fi

# Build with PyInstaller
echo "==> Running PyInstaller..."
pyinstaller search-ads-server.spec --noconfirm --clean

# Define paths
DIST_DIR="dist/search-ads-server"
RESOURCES_DIR="src-tauri/resources/search-ads-server"
BINARIES_DIR="src-tauri/binaries"
WRAPPER_SCRIPT="$BINARIES_DIR/search-ads-server-$TARGET_TRIPLE"

# Ensure directories exist
mkdir -p "$BINARIES_DIR"
mkdir -p "$(dirname "$RESOURCES_DIR")"

# Check if dist is a directory (onedir mode)
if [ -d "$DIST_DIR" ]; then
    echo "==> Detected onedir build."
    
    # Clean old resources
    rm -rf "$RESOURCES_DIR"

    # Copy onedir distribution to resources
    echo "==> Copying application bundle to $RESOURCES_DIR..."
    cp -R "$DIST_DIR" "$RESOURCES_DIR"

    # Create wrapper script
    echo "==> Creating wrapper script at $WRAPPER_SCRIPT..."
    cat > "$WRAPPER_SCRIPT" << 'EOF'
#!/bin/bash
# Wrapper to launch the PyInstaller onedir application from Resources

# Resolve resource path relative to this script
# Use simple relative path logic assuming standard bundle structure
# Tauri bundle structure:
# Contents/MacOS/search-ads-server-target-triple (this script)
# Contents/Resources/resources/search-ads-server/search-ads-server (executable)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Try standard macOS bundle path
EXEC_PATH="$SCRIPT_DIR/../Resources/resources/search-ads-server/search-ads-server"

# If not found (e.g. dev mode), try relative to src-tauri
if [ ! -f "$EXEC_PATH" ]; then
    # In dev mode: src-tauri/binaries/wrapper -> src-tauri/resources/search-ads-server/server
    EXEC_PATH="$SCRIPT_DIR/../resources/search-ads-server/search-ads-server"
fi

if [ ! -f "$EXEC_PATH" ]; then
    echo "Error: Could not find search-ads-server executable at $EXEC_PATH" >&2
    echo "Script dir: $SCRIPT_DIR" >&2
    exit 1
fi

# Execute the actual binary, passing all arguments
exec "$EXEC_PATH" "$@"
EOF

    chmod +x "$WRAPPER_SCRIPT"
    echo "==> Wrapper created."

else
    # Fallback for onefile mode (if spec wasn't updated)
    echo "==> Detected onefile build (fallback)."
    if [ -f "dist/search-ads-server" ]; then
        cp "dist/search-ads-server" "$WRAPPER_SCRIPT"
        chmod +x "$WRAPPER_SCRIPT"
    elif [ -f "dist/search-ads-server.exe" ]; then
        cp "dist/search-ads-server.exe" "$WRAPPER_SCRIPT.exe"
    else
        echo "ERROR: Binary not found in dist/"
        exit 1
    fi
fi

echo "==> Build complete!"

