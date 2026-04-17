# Release Guide — macOS signed build

This document covers how to produce a **signed + notarized** macOS `.dmg` locally
and publish it to a GitHub Release. It assumes you have an active Apple
Developer Program membership.

---

## One-time setup

### 1. Install Xcode Command Line Tools

```bash
xcode-select --install
```

This gives you `codesign` and `xcrun notarytool`. You do **not** need the Xcode
GUI.

### 2. Create a "Developer ID Application" certificate

In a browser, go to
[developer.apple.com → Certificates](https://developer.apple.com/account/resources/certificates/list)
and create a certificate of type **Developer ID Application** (not "Mac App
Distribution" — that's for the App Store).

- Generate the CSR via **Keychain Access → Certificate Assistant → Request a
  Certificate From a Certificate Authority** (save to disk).
- Upload the CSR to Apple's portal and download the resulting `.cer`.
- Double-click the `.cer` to install it into your **login** keychain.

Verify the cert and its private key are present:

```bash
security find-identity -v -p codesigning
```

You should see a line like:

```
1) ABCD1234... "Developer ID Application: Your Name (TEAMID1234)"
```

The string in quotes is your **signing identity**. The parenthesized
`TEAMID1234` is your **Team ID**.

### 3. Generate an app-specific password for notarization

Apple's notary service can't use your regular Apple ID password.

1. Sign in at [appleid.apple.com](https://appleid.apple.com).
2. **Sign-In and Security → App-Specific Passwords → Generate Password…**
3. Label it something like `search-ads-notary` and save the resulting
   `xxxx-xxxx-xxxx-xxxx` string.

### 4. Export the env vars

Add these to your `~/.zshrc` (or `~/.bashrc`). Replace placeholders with your
real values:

```bash
# Tauri macOS signing
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID1234)"
export APPLE_ID="you@example.com"
export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"   # app-specific password
export APPLE_TEAM_ID="TEAMID1234"
```

Reload your shell (`source ~/.zshrc`) and confirm:

```bash
echo "$APPLE_SIGNING_IDENTITY"
```

### 5. Add an entitlements file for the Python sidecar

PyInstaller-bundled Python will fail to start under the hardened runtime
without a couple of entitlements. Create `src-tauri/Entitlements.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

Reference it in `src-tauri/tauri.conf.json` under `bundle.macOS`:

```json
"macOS": {
  "minimumSystemVersion": "10.15",
  "infoPlist": "Info.plist",
  "entitlements": "Entitlements.plist"
}
```

---

## Per-release workflow

### 1. Bump the version

Update the `version` field in three places so they stay in sync:

- `src-tauri/tauri.conf.json`
- `frontend/package.json`
- `pyproject.toml`

Commit:

```bash
git commit -am "release: vX.Y.Z"
git tag vX.Y.Z
```

### 2. Build the Python sidecar

```bash
source .venv/bin/activate
./scripts/build-sidecar.sh
```

### 3. Deep-sign the sidecar (required)

The PyInstaller `onedir` output under
`src-tauri/resources/search-ads-server/` contains dozens of nested `.so` and
`.dylib` files. Tauri's bundler signs the outer `.app`, but the nested binaries
must each carry a valid signature or notarization will fail.

Run this before `cargo tauri build`:

```bash
find src-tauri/resources/search-ads-server \
  -type f \( -name "*.so" -o -name "*.dylib" -o -perm +111 \) \
  -exec codesign --force --timestamp --options runtime \
    --entitlements src-tauri/Entitlements.plist \
    --sign "$APPLE_SIGNING_IDENTITY" {} \;
```

### 4. Build, sign, and notarize the app

```bash
cargo tauri build
```

With the env vars set, Tauri will:

1. Build the universal binary.
2. Sign the `.app` with your Developer ID cert and hardened runtime.
3. Submit to Apple's notary service (takes ~1–3 min).
4. Staple the notarization ticket to the `.dmg`.

Output paths:

- `src-tauri/target/release/bundle/macos/Search-ADS.app`
- `src-tauri/target/release/bundle/dmg/Search-ADS_X.Y.Z_aarch64.dmg`

### 5. Verify the result

```bash
# Check the signature
codesign --verify --deep --strict --verbose=2 \
  src-tauri/target/release/bundle/macos/Search-ADS.app

# Check Gatekeeper acceptance
spctl --assess --type execute -vv \
  src-tauri/target/release/bundle/macos/Search-ADS.app

# Confirm notarization ticket is stapled to the DMG
stapler validate src-tauri/target/release/bundle/dmg/Search-ADS_*.dmg
```

A clean result should say `accepted` / `source=Notarized Developer ID` /
`The validate action worked!`.

### 6. Create the GitHub Release

```bash
git push origin main --tags

gh release create vX.Y.Z \
  --title "vX.Y.Z" \
  --notes-file CHANGELOG.md \
  src-tauri/target/release/bundle/dmg/Search-ADS_*.dmg
```

---

## Troubleshooting

**`errSecInternalComponent` during codesign.**
Your cert's private key isn't in the login keychain, or the keychain is
locked. Unlock with `security unlock-keychain login.keychain` and re-try.

**Notarization fails with `The signature of the binary is invalid`.**
A nested binary in the sidecar wasn't signed. Re-run the deep-sign command in
step 3, making sure no files were missed (check `codesign -dv` on a
representative `.so`).

**App launches on your Mac but not on a friend's fresh Mac.**
The DMG wasn't stapled. Run `stapler staple <file>.dmg` and re-upload.

**Want to see what Apple's notary service rejected?**

```bash
xcrun notarytool log <submission-id> \
  --apple-id "$APPLE_ID" \
  --team-id "$APPLE_TEAM_ID" \
  --password "$APPLE_PASSWORD"
```

The submission ID is printed at the end of the Tauri build log.
