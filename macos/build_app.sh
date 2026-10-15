#!/bin/bash
# Build dist/Oncemore.app (and dist/Oncemore-<version>-<arch>.zip) on macOS.
#
#   macos/build_app.sh                 # ad-hoc signed, for local use / CI artifacts
#   CODESIGN_IDENTITY="Developer ID Application: Name (TEAMID)" macos/build_app.sh
#
# The app bundles a standalone CPython (python-build-standalone, pinned
# release, checksum-verified) and the oncemore package, so users only need
# Homebrew's ffmpeg-full. Needs: Xcode 26 or later (swiftc, codesign,
# iconutil, sips, and actool for the layered icon) and `gh` (to fetch the
# Python build).
#
# Environment:
#   ARCH=arm64|x86_64     target architecture (default: this machine)
#   PY_TAG, PY_MINOR      python-build-standalone release and Python version
#   CODESIGN_IDENTITY     signing identity (default "-" = ad-hoc)
#   NO_LAYERED_ICON=1     leave out the macOS 26 layered icon (no Xcode 26)
#   NOTARIZE=1            notarize + staple (needs APPLE_ID, APPLE_TEAM_ID,
#                         APPLE_APP_PASSWORD and a Developer ID identity)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/dist}"
ARCH="${ARCH:-$(uname -m)}"
PY_TAG="${PY_TAG:-20260924}"
PY_MINOR="${PY_MINOR:-3.12}"
IDENTITY="${CODESIGN_IDENTITY:--}"
case "$ARCH" in
  arm64) PBS_ARCH=aarch64 ;;
  x86_64) PBS_ARCH=x86_64 ;;
  *) echo "unsupported ARCH $ARCH" >&2; exit 2 ;;
esac

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/oncemore/__init__.py")"
BUILD="$(git -C "$ROOT" rev-list --count HEAD 2>/dev/null || echo 1)"
APP="$OUT/Oncemore.app"
echo "==> oncemore $VERSION ($BUILD) for $ARCH"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/app"

echo "==> compiling the app shell"
swiftc -O -target "$ARCH-apple-macos12.0" \
  -o "$APP/Contents/MacOS/Oncemore" "$ROOT/macos/Oncemore/main.swift" \
  -framework Cocoa -framework WebKit

sed -e "s/@VERSION@/$VERSION/g" -e "s/@BUILD@/$BUILD/g" "$ROOT/macos/Info.plist" \
  > "$APP/Contents/Info.plist"
plutil -lint "$APP/Contents/Info.plist"

echo "==> icon"
ICONSET="$OUT/AppIcon.iconset"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  sips -z $s $s "$ROOT/macos/AppIcon.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s * 2))
  sips -z $d $d "$ROOT/macos/AppIcon.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"
rm -rf "$ICONSET"

# macOS 26 and later: the layered icon (macos/AppIcon.icon, made by
# docs/images/logo/make_logo.py), compiled into Assets.car and named by
# CFBundleIconName; the system masks it and adds its light. Earlier macOS
# keep AppIcon.icns. Needs Xcode 26 or later (actool reading .icon);
# NO_LAYERED_ICON=1 builds without it.
if [ -z "${NO_LAYERED_ICON:-}" ]; then
  echo "==> layered icon (Xcode at ${DEVELOPER_DIR:-$(xcode-select -p)})"
  ICONTMP="$OUT/AppIcon.actool"
  rm -rf "$ICONTMP"; mkdir -p "$ICONTMP"
  xcrun actool "$ROOT/macos/AppIcon.icon" --compile "$ICONTMP" \
    --output-format human-readable-text --notices --warnings --errors \
    --output-partial-info-plist "$ICONTMP/partial.plist" \
    --app-icon AppIcon --include-all-app-icons --enable-on-demand-resources NO \
    --development-region en --target-device mac --minimum-deployment-target 12.0 \
    --platform macosx
  # (only the asset catalog: actool's own AppIcon.icns is smaller than ours)
  cp "$ICONTMP/Assets.car" "$APP/Contents/Resources/Assets.car"
  xcrun assetutil --info "$APP/Contents/Resources/Assets.car" | grep -q 'AppIcon' \
    || { echo "Assets.car has no AppIcon" >&2; exit 1; }
  rm -rf "$ICONTMP"
else
  /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$APP/Contents/Info.plist"
fi

if [ -z "${NO_PYTHON:-}" ]; then
  echo "==> Python $PY_MINOR (python-build-standalone $PY_TAG)"
  CACHE="${PY_CACHE:-$OUT/.cache}"
  mkdir -p "$CACHE"
  PATTERN="cpython-$PY_MINOR.*+$PY_TAG-$PBS_ARCH-apple-darwin-install_only.tar.gz"
  if ! ls "$CACHE"/$PATTERN >/dev/null 2>&1; then
    gh release download "$PY_TAG" -R astral-sh/python-build-standalone -D "$CACHE" \
      -p "$PATTERN" --clobber
    gh release download "$PY_TAG" -R astral-sh/python-build-standalone -D "$CACHE" \
      -p "SHA256SUMS" --clobber || true
  fi
  TARBALL="$(ls "$CACHE"/$PATTERN | head -1)"
  if [ -f "$CACHE/SHA256SUMS" ]; then
    (cd "$CACHE" && grep " $(basename "$TARBALL")\$" SHA256SUMS | shasum -a 256 -c -)
  else
    echo "warning: no SHA256SUMS in release $PY_TAG; checksum not verified" >&2
  fi
  tar -xzf "$TARBALL" -C "$APP/Contents/Resources"
  PYLIB="$APP/Contents/Resources/python/lib/python$PY_MINOR"
  # trim what a DVD tool never uses (~40 MB)
  rm -rf "$PYLIB"/test "$PYLIB"/idlelib "$PYLIB"/tkinter "$PYLIB"/turtledemo \
         "$PYLIB"/ensurepip "$PYLIB"/lib2to3 "$PYLIB"/pydoc_data \
         "$PYLIB"/lib-dynload/_tkinter.* \
         "$APP/Contents/Resources/python/lib"/{tcl,tk,itcl,thread,libtcl,libtk}* \
         "$APP/Contents/Resources/python/share"
  find "$APP/Contents/Resources/python" -name '__pycache__' -prune -exec rm -rf {} +
  "$APP/Contents/Resources/python/bin/python3" -c "import sys, ssl, zlib, json; print(sys.version)"
fi

echo "==> oncemore package"
cp -R "$ROOT/oncemore" "$APP/Contents/Resources/app/"
find "$APP/Contents/Resources/app" -name '__pycache__' -prune -exec rm -rf {} +
cp "$ROOT/LICENSE" "$APP/Contents/Resources/LICENSE.txt"

echo "==> signing ($IDENTITY)"
SIGN_OPTS=(--force --sign "$IDENTITY" --timestamp=none)
if [ "$IDENTITY" != "-" ]; then
  SIGN_OPTS=(--force --sign "$IDENTITY" --timestamp --options runtime
             --entitlements "$ROOT/macos/entitlements.plist")
fi
# nested Mach-O files first (inside-out), then the bundle
while IFS= read -r -d '' f; do
  if file -b "$f" | grep -q 'Mach-O'; then
    codesign "${SIGN_OPTS[@]}" "$f"
  fi
done < <(find "$APP/Contents/Resources" -type f \( -perm -u+x -o -name '*.so' -o -name '*.dylib' \) -print0)
codesign "${SIGN_OPTS[@]}" "$APP"
codesign --verify --strict --verbose=2 "$APP"

ZIP="$OUT/Oncemore-$VERSION-$ARCH.zip"
rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"

if [ -n "${NOTARIZE:-}" ]; then
  echo "==> notarizing"
  xcrun notarytool submit "$ZIP" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_APP_PASSWORD" --wait
  # the ticket is fetched from Apple's servers, which sometimes drop the
  # connection right after the submission is accepted: try a few times
  for try in 1 2 3 4 5; do
    if xcrun stapler staple "$APP"; then break; fi
    if [ "$try" = 5 ]; then echo "stapling failed $try times" >&2; exit 1; fi
    echo "stapling failed (try $try); trying again in $((try * 20)) s"
    sleep $((try * 20))
  done
  xcrun stapler validate "$APP"
  rm -f "$ZIP"
  ditto -c -k --keepParent "$APP" "$ZIP"
fi

du -sh "$APP" "$ZIP"
echo "==> $APP"
