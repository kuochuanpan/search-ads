# Tauri Implementation Plan for Search-ADS

This document outlines the implementation of wrapping Search-ADS (frontend + backend + CLI) into a native macOS application using Tauri v2.

## Status: IMPLEMENTED

The Tauri wrapper has been successfully implemented. The macOS `.app` bundle is ready for use.

## What Was Done

### 1. Project Structure

```
search-ads/
├── src-tauri/                    # Tauri Rust project
│   ├── Cargo.toml                # Rust dependencies
│   ├── tauri.conf.json           # Tauri configuration
│   ├── build.rs                  # Build script
│   ├── capabilities/
│   │   └── default.json          # Permission configuration
│   ├── binaries/
│   │   └── search-ads-server-aarch64-apple-darwin  # PyInstaller sidecar (71MB)
│   ├── icons/                    # App icons (auto-generated)
│   └── src/
│       ├── main.rs               # Entry point
│       └── lib.rs                # Sidecar lifecycle management
├── scripts/
│   └── build-sidecar.sh          # Build script for Python sidecar
├── search-ads-server.spec        # PyInstaller spec file
├── src/
│   └── server_entry.py           # Sidecar entry point with graceful shutdown
└── frontend/
    └── src/
        ├── lib/api.ts            # Updated with Tauri detection
        └── tauri.d.ts            # TypeScript declarations
```

### 2. Key Components

| Component | Description |
|-----------|-------------|
| **Sidecar** | Python FastAPI server packaged with PyInstaller (71MB binary) |
| **Lifecycle** | Auto-start on app launch, graceful shutdown on exit |
| **Frontend** | Detects Tauri environment, connects directly to `127.0.0.1:9527` |
| **IPC** | Shutdown command sent via stdin to Python process |

### 3. How It Works

1. When the app launches, Tauri spawns the Python sidecar binary
2. The sidecar starts FastAPI server on `127.0.0.1:9527`
3. The webview loads the React frontend
4. Frontend detects Tauri and connects directly to the API (no proxy)
5. On app close, Tauri sends "SHUTDOWN" via stdin for graceful exit

## Usage

### Development

```bash
# First time: build the sidecar
./scripts/build-sidecar.sh

# Run in dev mode (hot reload for frontend)
cargo tauri dev
```

### Production Build

```bash
# Build sidecar (if Python code changed)
./scripts/build-sidecar.sh

# Build macOS app
cargo tauri build
```

### Output Locations

- **App bundle**: `src-tauri/target/release/bundle/macos/Search-ADS.app`
- **DMG installer**: `src-tauri/target/release/bundle/dmg/Search-ADS_*.dmg`

## Updating the App

### After Frontend Changes
```bash
cargo tauri build
# No need to rebuild sidecar
```

### After Python Backend Changes
```bash
./scripts/build-sidecar.sh  # Rebuild sidecar first
cargo tauri build
```

### After Adding Python Dependencies
1. Update `pyproject.toml` or `requirements.txt`
2. Update `search-ads-server.spec` hidden imports if needed
3. Run `./scripts/build-sidecar.sh`
4. Run `cargo tauri build`

## Backward Compatibility

The app continues to work in both modes:

| Mode | Frontend URL | Backend |
|------|--------------|---------|
| **Browser** (`npm run dev`) | `localhost:5173` | Vite proxy → `127.0.0.1:9527` |
| **Tauri** (`cargo tauri dev/build`) | Webview | Direct → `127.0.0.1:9527` |

The frontend automatically detects the environment and uses the appropriate API base URL.

## Notes

### Bundle Size
- Sidecar binary: ~71MB (includes Python runtime + all dependencies)
- Total app size: ~180MB

### First Launch
- PyInstaller one-file executables extract on first run
- Expect 2-3 second delay on first launch

### Known Issues
1. **DMG bundling**: May fail due to missing dependencies. The `.app` bundle works regardless.
2. **TypeScript warning**: Pre-existing type issue in `LibraryPage.tsx` (not Tauri-related)

### Code Signing (for Distribution)
To distribute the app, you'll need:
1. Apple Developer account
2. Set environment variables:
   ```bash
   export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name"
   export APPLE_ID="your@email.com"
   export APPLE_PASSWORD="app-specific-password"
   export APPLE_TEAM_ID="XXXXXXXXXX"
   ```
3. Run `cargo tauri build`

## File Changes Summary

| File | Change |
|------|--------|
| `src-tauri/*` | NEW - Tauri project |
| `scripts/build-sidecar.sh` | NEW - Sidecar build script |
| `search-ads-server.spec` | NEW - PyInstaller config |
| `src/server_entry.py` | NEW - Sidecar entry point |
| `frontend/src/lib/api.ts` | Modified - Tauri detection |
| `frontend/src/tauri.d.ts` | NEW - TypeScript declarations |
| `frontend/package.json` | Modified - Added Tauri scripts |
