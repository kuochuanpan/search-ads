#!/bin/bash

# OpenClaw Skill Installer for Search-ADS
# Usage:
#   ./install.sh [path-to-search-ads] [assistant-display-name]
# Examples:
#   ./install.sh                       # uses ~/code/search-ads and assistant name "OpenClaw"
#   ./install.sh ~/code/search-ads Maho

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Detect Search-ADS directory
SEARCH_ADS_DIR="${1:-$HOME/code/search-ads}"
if [ ! -d "$SEARCH_ADS_DIR" ]; then
    echo "Error: Search-ADS directory not found at $SEARCH_ADS_DIR"
    echo "Usage: ./install.sh [path-to-search-ads] [assistant-display-name]"
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

# Escape backslashes and double quotes for use in KEY="value" lines
escape_env_value() {
  local raw="$1"
  raw=${raw//\\/\\\\}
  raw=${raw//\"/\\\"}
  # strip newlines (defensive)
  raw=${raw//$'\n'/}
  raw=${raw//$'\r'/}
  printf '%s' "$raw"
}

# Upsert helper (portable: no GNU/BSD sed differences)
upsert_env() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(escape_env_value "$value")"

  # If the env file does not exist yet, create it with this single entry.
  if [ ! -f "$ENV_PATH" ]; then
    printf '%s="%s"\n' "$key" "$escaped" > "$ENV_PATH"
    return
  fi

  local tmp_file
  tmp_file="$(mktemp "${ENV_PATH}.XXXXXX")"
  local replaced="false"

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "${key}="*)
        if [ "$replaced" = "false" ]; then
          printf '%s="%s"\n' "$key" "$escaped" >> "$tmp_file"
          replaced="true"
        fi
        ;;
      *)
        printf '%s\n' "$line" >> "$tmp_file"
        ;;
    esac
  done < "$ENV_PATH"

  if [ "$replaced" = "false" ]; then
    printf '%s="%s"\n' "$key" "$escaped" >> "$tmp_file"
  fi

  mv "$tmp_file" "$ENV_PATH"
}

upsert_env "ASSISTANT_ENABLED" "true"
upsert_env "ASSISTANT_NAME" "$ASSISTANT_NAME"

echo "✅ Skill installed successfully!"
echo "OpenClaw can now use 'search-ads' tools."
echo "Assistant integration enabled for WebUI as: $ASSISTANT_NAME"
echo
# Note: Search-ADS settings are loaded at backend startup.
echo "Note: if Search-ADS WebUI/backend is already running, restart it so ASSISTANT_ENABLED/ASSISTANT_NAME take effect."
