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
    # --- Audio Libraries (C/C++ Level) ---
  ];

  shellHook = ''
    # 創建並啟動虛擬環境
    [ ! -d ".venv" ] && virtualenv .venv
    source .venv/bin/activate

    echo "🎀 Python 3 Virtual Enviroment 🎀"
  '';
}
