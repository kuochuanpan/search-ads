#!/bin/bash

# Exit on error
set -e

REPO_URL="https://github.com/kuochuanpan/search-ads.git"
INSTALL_DIR="$HOME/search-ads"

# Function to check command existence
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 could not be found. Please install it first."
        exit 1
    fi
}

echo "Checking dependencies..."
check_command git
check_command npm

# Detect package installer: prefer uv, fall back to pipx
if command -v uv &> /dev/null; then
    PKG_INSTALLER="uv"
    echo "Using uv as package installer."
elif command -v pipx &> /dev/null; then
    PKG_INSTALLER="pipx"
    echo "Using pipx as package installer."
else
    echo "Error: Neither uv nor pipx found. Please install one of them first."
    echo "  uv:   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  pipx: python3 -m pip install --user pipx"
    exit 1
fi

echo "Installing Search-ADS..."

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists."
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "Updating existing installation..."
        cd "$INSTALL_DIR"
        git pull
    fi
else
    echo "Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
chmod +x launch.sh

echo "Installing backend (CLI)..."
if [ "$PKG_INSTALLER" = "uv" ]; then
    uv tool install . --force
else
    pipx install . --force
fi

echo "Installing frontend dependencies..."
cd frontend
npm install

echo "------------------------------------------------"
echo "Initializing configuration..."
# Initialize configuration (creates ~/.search-ads/.env)
search-ads init

echo "------------------------------------------------"
echo "IMPORTANT: Please configure your API keys!"
echo "Edit the file at: ~/.search-ads/.env"
echo "  - ADS_API_KEY (Required): Get from https://ui.adsabs.harvard.edu/user/settings/token"
echo "  - OPENAI_API_KEY (Optional)"
echo "  - ANTHROPIC_API_KEY (Optional)"
echo ""
echo "Also set these optional variables in .env:"
echo "  - MY_AUTHOR_NAMES=\"Author, A.; Author, B.\""
echo "  - OPENAI_MODEL=\"gpt-4o-mini\""
echo "  - ANTHROPIC_MODEL=\"claude-3-haiku-20240307\""
echo "------------------------------------------------"

echo "Installation complete!"
echo "To launch the application:"
echo "  cd $INSTALL_DIR"
echo "  ./launch.sh"
echo "------------------------------------------------"
