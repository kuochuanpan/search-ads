---
name: release-macos
description: "Cut a signed + notarized macOS DMG release for search-ads, bump versions, commit, tag, and publish to GitHub Releases. Use when: the user asks to cut a release, publish a new version, build a signed DMG, or ship to GitHub. NOT for: dev-time local builds (use development skill) or unsigned experimental builds."
version: 1.0.0
---

# Search-ADS Release Workflow (macOS)

End-to-end runbook for shipping a signed + notarized macOS release of Search-ADS to GitHub Releases. Every step here has been validated against an actual release; gotchas we hit are documented inline so the next run doesn't repeat them.

## Prerequisites (verify before starting)

```bash
# 1. Signing env vars must be set (from ~/.zshrc)
echo "APPLE_SIGNING_IDENTITY=$APPLE_SIGNING_IDENTITY"
echo "APPLE_ID=$APPLE_ID"
echo "APPLE_TEAM_ID=$APPLE_TEAM_ID"
echo "APPLE_PASSWORD=$([ -n "$APPLE_PASSWORD" ] && echo SET || echo NOT SET)"

# Expected values:
#   APPLE_SIGNING_IDENTITY="Developer ID Application: Kuo-Chuan Pan (K867NAPA93)"
#   APPLE_ID="kuochuan.pan@gmail.com"
#   APPLE_TEAM_ID="K867NAPA93"
#   APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx" (app-specific password)

# 2. Developer ID cert must be in login keychain
security find-identity -v -p codesigning | grep "Developer ID Application"
# Must print: "Developer ID Application: Kuo-Chuan Pan (K867NAPA93)"

# 3. Python venv must be activated (pyinstaller needed for sidecar)
source .venv/bin/activate
command -v pyinstaller  # must resolve
```

If any check fails, see `docs/release.md` for one-time setup (cert creation, env var export).

## Inputs needed

Before starting, confirm with the user:
- **New version** (e.g. `1.0.1-beta`, `1.1.0`, `1.0.0`)
- **Tag name convention** — existing releases use `X.Y.Z-beta` or `vX.Y.Z`
- **Release title convention** — existing pattern is `macOS-X.Y.Z-beta`
- **Prerelease flag** — `true` for beta, `false` for stable

## Step 1 — Bump the version in every manifest

Five files need the version updated. **All must match**, or Tauri bundling will fail or produce mismatched artifacts.

| File | Field |
|---|---|
| `frontend/package.json` | `"version": "X.Y.Z"` |
| `pyproject.toml` | `version = "X.Y.Z"` |
| `src-tauri/Cargo.toml` | `version = "X.Y.Z"` |
| `src-tauri/tauri.conf.json` | `"version": "X.Y.Z"` |
| `src/core/config.py` | `version: str = Field(default="X.Y.Z", alias="VERSION")` |

Also update the README:

| File | Location |
|---|---|
| `README.md` | `![Version](https://img.shields.io/badge/version-X.Y.Z-blue)` (line ~3) |
| `README.md` | `**Version: X.Y.Z**` (line ~17) |

Note: `src-tauri/Cargo.lock` will auto-update when cargo runs — don't hand-edit.

## Step 2 — Commit the version bump

```bash
git add \
  frontend/package.json \
  pyproject.toml \
  src-tauri/Cargo.toml \
  src-tauri/tauri.conf.json \
  src/core/config.py \
  README.md

# Review before committing — NEVER use `git add -A`, it may catch secrets
git diff --staged

# Scan for accidentally-staged secrets
git diff --staged | grep -iE '(password|secret|token|api_key)\s*[=:]\s*["'"'"'][a-zA-Z0-9_\-]{16,}'
# Expected: no output

git commit -m "$(cat <<'EOF'
release: vX.Y.Z

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Step 3 — Build the Python sidecar

The sidecar is the PyInstaller-packaged FastAPI backend that ships inside the `.app`. It must be rebuilt any time Python code in `src/` changes.

```bash
source .venv/bin/activate  # pyinstaller is in .venv, not global
./scripts/build-sidecar.sh
```

Produces `src-tauri/resources/search-ads-server/` (onedir bundle with ~120 nested binaries) and the wrapper at `src-tauri/binaries/search-ads-server-aarch64-apple-darwin`.

## Step 4 — Deep-sign the sidecar

**Critical step** — Tauri only signs the outer `.app` bundle. Every `.so` / `.dylib` / mach-o inside `src-tauri/resources/search-ads-server/` must carry its own valid signature or Apple's notary service will reject the submission with `The signature of the binary is invalid`.

```bash
SIGNING_IDENTITY="Developer ID Application: Kuo-Chuan Pan (K867NAPA93)"

find src-tauri/resources/search-ads-server \
  -type f \( -name "*.so" -o -name "*.dylib" -o -name "search-ads-server" \) \
  -exec codesign --force --timestamp --options runtime \
    --entitlements src-tauri/Entitlements.plist \
    --sign "$SIGNING_IDENTITY" {} \;
```

Expect ~120 "replacing existing signature" lines.

## Step 5 — Check for stale DMG volumes (gotcha)

`bundle_dmg.sh` inside Tauri fails silently if a previous DMG's temp volume is still mounted. Always detach any stale `/Volumes/dmg.*` before building.

```bash
ls /Volumes/ | grep -i dmg   # look for dmg.XXXXXX

# If present:
hdiutil detach /Volumes/dmg.XXXXXX -force
```

## Step 6 — Build, sign, notarize the app

Run in the **foreground shell** (do NOT use Claude Code's `run_in_background` for this — the task dies silently during notarization). Notarization takes 5–15 min on first call, 1–3 min on repeat.

```bash
APPLE_SIGNING_IDENTITY="Developer ID Application: Kuo-Chuan Pan (K867NAPA93)" \
  cargo tauri build 2>&1 | tee /tmp/tauri-build.log
```

This step does, in order:
1. Frontend build (vite)
2. Rust compile (~50 s)
3. Sign `.app` bundle
4. Submit to Apple notary, wait for ticket
5. Staple ticket to `.app`
6. Build DMG
7. Sign DMG

Success output ends with:
```
Finished 2 bundles at:
    .../bundle/macos/Search-ADS.app
    .../bundle/dmg/Search-ADS_X.Y.Z_aarch64.dmg
```

## Step 7 — Notarize + staple the DMG (Tauri doesn't do this)

Tauri signs the DMG but **does not** submit it to the notary. Do this manually:

```bash
DMG=src-tauri/target/release/bundle/dmg/Search-ADS_X.Y.Z_aarch64.dmg

xcrun notarytool submit "$DMG" \
  --apple-id "$APPLE_ID" \
  --team-id "K867NAPA93" \
  --password "$APPLE_PASSWORD" \
  --wait

# Expect: status: Accepted (2–5 min)

xcrun stapler staple "$DMG"
```

## Step 8 — Verify

```bash
APP=src-tauri/target/release/bundle/macos/Search-ADS.app
DMG=src-tauri/target/release/bundle/dmg/Search-ADS_X.Y.Z_aarch64.dmg

codesign --verify --deep --strict --verbose=2 "$APP"
# Expect: "valid on disk" and "satisfies its Designated Requirement"

spctl --assess --type execute -vv "$APP"
# Expect: "accepted", "source=Notarized Developer ID"

xcrun stapler validate "$APP"
xcrun stapler validate "$DMG"
# Both: "The validate action worked!"
```

If any check fails, **do not proceed** — see Troubleshooting below.

## Step 9 — Tag, push, release

```bash
VERSION="X.Y.Z-beta"
TITLE="macOS-$VERSION"

git tag "$VERSION"
git push origin main "$VERSION"

gh release create "$VERSION" \
  --title "$TITLE" \
  --prerelease \
  --notes-file <(cat <<'EOF'
## <version> — <one-line summary>

<what's new>

### Install

1. Download the DMG below.
2. Open it and drag **Search-ADS** to **Applications**.
3. Launch. The app is signed + notarized — no warnings.
EOF
) \
  "src-tauri/target/release/bundle/dmg/Search-ADS_${VERSION}_aarch64.dmg"
```

Drop `--prerelease` for stable releases.

Confirm the release:
```bash
gh release view "$VERSION"
```

## Gotchas learned the hard way

| Symptom | Cause | Fix |
|---|---|---|
| `cd: frontend: No such file or directory` in tauri build | Tauri runs `beforeBuildCommand` from `src-tauri/`, not project root | `cd ../frontend && ...` in `tauri.conf.json` |
| `pip: command not found` in `build-sidecar.sh` | uv venvs don't include pip | Script uses `command -v pyinstaller` + `uv pip install` fallback |
| `bundle_dmg.sh` fails silently | Stale `/Volumes/dmg.*` from prior build | `hdiutil detach -force` before rebuild |
| `The signature of the binary is invalid` from Apple notary | Sidecar nested `.so` files not signed | Step 4 deep-sign |
| Notarization submission stuck forever in Claude bg task | `run_in_background` shell dies during the Apple wait | Run foreground with `| tee` |
| `codesign` picks wrong identity | Multiple certs in keychain with similar names | Export exact `APPLE_SIGNING_IDENTITY` string |
| User's app opens with "unidentified developer" | Cert is "Apple Development" (free team) | Need "Developer ID Application" (paid team K867NAPA93) |

## Troubleshooting notarization rejections

If `notarytool submit` returns `Invalid` instead of `Accepted`, inspect the log:

```bash
xcrun notarytool log <submission-id> \
  --apple-id "$APPLE_ID" \
  --team-id "K867NAPA93" \
  --password "$APPLE_PASSWORD"
```

The log lists each file that failed and why. Common causes:
- Missing hardened runtime — ensure `--options runtime` is in every `codesign` call
- Missing entitlements — ensure `--entitlements src-tauri/Entitlements.plist` is passed
- Nested unsigned binary — re-run Step 4 and verify no files were missed with `codesign -dv` on a sampled `.so`

## Related files

- `docs/release.md` — one-time setup (cert creation, keychain install, env var export)
- `src-tauri/Entitlements.plist` — hardened runtime exceptions for PyInstaller/CPython
- `src-tauri/tauri.conf.json` — Tauri bundle config (entitlements reference, macOS settings)
- `scripts/build-sidecar.sh` — PyInstaller wrapper (uv-compatible)
