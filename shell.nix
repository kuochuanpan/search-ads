{ pkgs ? import <nixpkgs> { system = "aarch64-darwin"; } }:

pkgs.mkShell {
  name = "search-ads-dev";

  buildInputs = with pkgs; [
    python312
    python312Packages.pip
    python312Packages.virtualenv
    # --- System Tools ---
    ffmpeg  # faster-whisper音訊處理
    git
    # --- Node.js for frontend ---
    nodejs_20
    # --- Audio Libraries (C/C++ Level) ---
  ];

  shellHook = ''
    # 創建並啟動虛擬環境
    [ ! -d ".venv" ] && virtualenv .venv
    source .venv/bin/activate

    # Install package in development mode if not already installed
    if ! command -v search-ads &> /dev/null; then
      echo "Installing search-ads..."
      pip install -e . -q
    fi

    echo "🔭 Search-ADS Development Environment"
    echo "Run 'search-ads --help' to get started"
  '';
}
