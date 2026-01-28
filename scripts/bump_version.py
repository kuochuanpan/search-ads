
import re
import sys
from pathlib import Path
import json

def bump_version(new_version: str):
    """Update version in all project files."""
    root = Path(__file__).parent.parent
    
    files = {
        "pyproject.toml": {
            "path": root / "pyproject.toml",
            "regex": r'version = "[^"]+"',
            "replace": f'version = "{new_version}"'
        },
        "cargo": {
            "path": root / "src-tauri" / "Cargo.toml",
            "regex": r'version = "[^"]+"',
            "replace": f'version = "{new_version}"'
        },
        "settings": {
            "path": root / "src" / "core" / "config.py",
            "regex": r'version: str = Field\(default="[^"]+"',
            "replace": f'version: str = Field(default="{new_version}"'
        }
    }
    
    # Text-based replacements
    for name, config in files.items():
        path = config["path"]
        if not path.exists():
            print(f"Warning: {path} not found")
            continue
            
        content = path.read_text()
        new_content = re.sub(config["regex"], config["replace"], content, count=1)
        
        if content != new_content:
            path.write_text(new_content)
            print(f"Updated {name}")
        else:
            print(f"No changes for {name} (or verify regex)")

    # JSON replacements (safer than regex for JSON)
    json_files = {
        "package.json": root / "frontend" / "package.json",
        "tauri.conf.json": root / "src-tauri" / "tauri.conf.json"
    }

    for name, path in json_files.items():
        if not path.exists():
            print(f"Warning: {path} not found")
            continue
            
        try:
            content = json.loads(path.read_text())
            if content.get("version") != new_version:
                content["version"] = new_version
                # Write back with indentation
                path.write_text(json.dumps(content, indent=2) + "\n")
                print(f"Updated {name}")
            else:
                print(f"No changes for {name}")
        except Exception as e:
            print(f"Error updating {name}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <new_version>")
        sys.exit(1)
    
    bump_version(sys.argv[1])
