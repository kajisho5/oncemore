#!/bin/bash
# Launch the built app on a sample project and check that the real UI loads.
#   macos/smoke_test.sh dist/Oncemore.app
set -euo pipefail
APP="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# away from the checkout: `python -m oncemore` must load the app's own package
cd "$TMP"
PY="$APP/Contents/Resources/python/bin/python3"
export PYTHONPATH="$APP/Contents/Resources/app"
# only macOS's own programs: the app must work without Homebrew
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

echo "==> bundled engine"
"$PY" -s -m oncemore --version
"$PY" -s -m oncemore doctor || true
"$PY" -s -m oncemore --json doctor > "$TMP/doctor.json" || true
"$PY" - "$TMP/doctor.json" "$APP" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
d = d.get("result", d)
paths = {t["name"]: t["path"] for t in d["tools"]}
import oncemore
assert oncemore.__file__.startswith(sys.argv[2] + "/"), oncemore.__file__
for name in ("ffmpeg", "ffprobe"):
    assert paths[name] == sys.argv[2] + "/Contents/Resources/ffmpeg/" + name, paths
assert d["ready"], d
print("doctor: ready, with the app's own ffmpeg and ffprobe")
EOF
"$PY" -s -m oncemore init "$TMP/Sample Project" >/dev/null

echo "==> a DVD and a Blu-ray with the app's ffmpeg"
"$PY" -s -m oncemore iso "$TMP/Sample Project" -o "$TMP/dvd.iso" >/dev/null
"$PY" -s -m oncemore iso "$TMP/Sample Project" --format bluray -o "$TMP/bd.iso" >/dev/null
ls -l "$TMP/dvd.iso" "$TMP/bd.iso"

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
# the menu bar is the page's (posted to the app): File … Help, in that order
menus = r.get("menus", [])
assert menus[1:] == ["File", "Edit", "Object", "Menu", "Timeline", "View", "Window", "Help"], menus
print("smoke test passed: the app loaded the project UI and its menu bar")
EOF
