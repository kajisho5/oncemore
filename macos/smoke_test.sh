#!/bin/bash
# Launch the built app on a sample project and check that the real UI loads.
#   macos/smoke_test.sh dist/Oncemore.app
set -euo pipefail
APP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
PY="$APP/Contents/Resources/python/bin/python3"
export PYTHONPATH="$APP/Contents/Resources/app"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "==> bundled engine"
"$PY" -s -m oncemore --version
"$PY" -s -m oncemore doctor || true
"$PY" -s -m oncemore init "$TMP/Sample Project" >/dev/null

echo "==> launching the app"
unset PYTHONPATH   # the app sets its own
ONCEMORE_PROJECT="$TMP/Sample Project" ONCEMORE_SMOKE_RESULT="$TMP/result.json" \
  "$APP/Contents/MacOS/Oncemore" > "$TMP/app.log" 2>&1 &
PID=$!
for _ in $(seq 1 120); do
  [ -s "$TMP/result.json" ] && break
  sleep 1
done
kill "$PID" 2>/dev/null || true
if [ ! -s "$TMP/result.json" ]; then
  echo "no result from the app"; cat "$TMP/app.log"; exit 1
fi
cat "$TMP/result.json"; echo
python3 - "$TMP/result.json" <<'EOF'
import json, sys
r = json.load(open(sys.argv[1]))
assert r.get("disc") == "SAMPLE_DISC", r
assert r.get("navItems", 0) >= 5, r
assert r.get("stage") is True, r
print("smoke test passed: the app loaded the project UI")
EOF
