#!/bin/bash
# SessionStart hook for Claude Code cloud sessions: install the external
# programs oncemore drives, so `python -m unittest` (incl. end-to-end tests)
# can run. oncemore itself is stdlib-only, so there is nothing to pip install.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PKGS="ffmpeg genisoimage xorriso libdvdnav4 fonts-noto-cjk"

missing=${ONCEMORE_HOOK_FORCE_INSTALL:-0}
for bin in ffmpeg ffprobe genisoimage xorriso; do
  command -v "$bin" >/dev/null 2>&1 || missing=1
done
ldconfig -p 2>/dev/null | grep -q libdvdnav || missing=1
[ -e /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc ] || missing=1

if [ "$missing" = 1 ]; then
  SUDO=""
  [ "$(id -u)" = 0 ] || SUDO="sudo"
  export DEBIAN_FRONTEND=noninteractive
  $SUDO apt-get update -qq
  $SUDO apt-get install -y -qq --no-install-recommends $PKGS >/dev/null
fi

echo "export PYTHONPATH=\"${CLAUDE_PROJECT_DIR:-$(pwd)}\${PYTHONPATH:+:\$PYTHONPATH}\"" >> "${CLAUDE_ENV_FILE:-/dev/null}"
