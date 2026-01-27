{ pkgs ? import <nixpkgs> { system = "aarch64-darwin"; } }:

pkgs.mkShell {
  name = "python3.10";
  
  buildInputs = with pkgs; [
    python310  # Python 3.10，穩定且相容
    python310Packages.pip
    python310Packages.virtualenv
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
