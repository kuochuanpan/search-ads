#!/bin/bash

# OpenClaw Skill Installer for Search-ADS
# Usage: ./install.sh [search-ads-dir]

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Detect Search-ADS directory
SEARCH_ADS_DIR="${1:-$HOME/code/search-ads}"
if [ ! -d "$SEARCH_ADS_DIR" ]; then
    echo "Error: Search-ADS directory not found at $SEARCH_ADS_DIR"
    echo "Usage: ./install.sh [path-to-search-ads]"
    exit 1
fi

# Detect OpenClaw Skills directory
OPENCLAW_SKILLS_DIR="$HOME/.openclaw/workspace/skills"
if [ ! -d "$OPENCLAW_SKILLS_DIR" ]; then
    echo "Warning: OpenClaw workspace not found at standard location."
    echo "Assuming standard path $OPENCLAW_SKILLS_DIR, creating it..."
    mkdir -p "$OPENCLAW_SKILLS_DIR"
fi

TARGET_SKILL_DIR="$OPENCLAW_SKILLS_DIR/search-ads"
mkdir -p "$TARGET_SKILL_DIR/scripts"

echo "Installing Search-ADS Skill to: $TARGET_SKILL_DIR"

# Copy scripts
cp "$SCRIPT_DIR/scripts/sync_insights.py" "$TARGET_SKILL_DIR/scripts/"

# Determine python path
VENV_PYTHON="$SEARCH_ADS_DIR/.venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Virtual environment python not found at $VENV_PYTHON"
    echo "Please set up Search-ADS first (pip install -e .)"
    exit 1
fi

# Generate SKILL.md from template
sed "s|__SEARCH_ADS_PYTHON__|$VENV_PYTHON|g" "$SCRIPT_DIR/SKILL.template.md" | \
sed "s|__SKILL_DIR__|$TARGET_SKILL_DIR|g" > "$TARGET_SKILL_DIR/SKILL.md"

# Enable assistant integration in Search-ADS (WebUI)
ASSISTANT_NAME="${2:-OpenClaw}"
ENV_DIR="$HOME/.search-ads"
ENV_PATH="$ENV_DIR/.env"
mkdir -p "$ENV_DIR"

# Upsert helper (POSIX-ish)
upsert_env() {
  local key="$1"
  local value="$2"
  if [ -f "$ENV_PATH" ] && grep -qE "^${key}=" "$ENV_PATH"; then
    # macOS sed needs -i ''
    sed -i '' -E "s|^${key}=.*$|${key}=\"${value}\"|" "$ENV_PATH"
  else
    echo "${key}=\"${value}\"" >> "$ENV_PATH"
  fi
}

upsert_env "ASSISTANT_ENABLED" "true"
upsert_env "ASSISTANT_NAME" "$ASSISTANT_NAME"

echo "✅ Skill installed successfully!"
echo "OpenClaw can now use 'search-ads' tools."
echo "Assistant integration enabled for WebUI as: $ASSISTANT_NAME"
