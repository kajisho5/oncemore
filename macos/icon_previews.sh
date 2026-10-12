#!/bin/bash
# Render the layered icon (macos/AppIcon.icon) as macOS shows it, with the
# renderer of Icon Composer (ictool, inside Xcode 26 or later), for a look
# without a Mac at hand: one PNG an appearance, at 256 x 256.
#   macos/icon_previews.sh <out dir>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$1"
DEV="${DEVELOPER_DIR:-$(xcode-select -p)}"
ICTOOL="$(dirname "$(dirname "$DEV")")/Contents/Applications/Icon Composer.app/Contents/Executables/ictool"
if [ ! -x "$ICTOOL" ]; then
  ICTOOL="$(ls -d /Applications/Xcode*.app/Contents/Applications/Icon\ Composer.app/Contents/Executables/ictool 2>/dev/null | sort -V | tail -1)"
fi
if [ ! -x "$ICTOOL" ]; then
  echo "no ictool (Icon Composer) in this Xcode: no previews" >&2
  exit 0
fi
mkdir -p "$OUT"
for look in Light Dark; do
  "$ICTOOL" "$ROOT/macos/AppIcon.icon" --export-preview macOS "$look" 256 256 1 "$OUT/AppIcon-$look.png"
done
ls -l "$OUT"
