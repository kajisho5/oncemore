"""Progress reporting: human-readable lines on stderr, or JSON Lines on stdout.

JSON mode emits one object per line. Every object has an "event" key:

  {"event": "log", "level": "info|warn", "message": "..."}
  {"event": "step", "step": "encode", "item": "t1", "message": "..."}
  {"event": "progress", "step": "encode", "item": "t1", "fraction": 0.42}
  {"event": "result", "ok": true, ...}          (always the last line)
  {"event": "error", "ok": false, "message": ..., "hint": ..., ...}
"""

import json
import sys
import time


class Reporter:
    def __init__(self, json_mode=False, verbose=False, out=None, err=None):
        self.json_mode = json_mode
        self.verbose = verbose
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self._last_progress = {}

    def _emit(self, obj):
        self.out.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.out.flush()

    def info(self, message):
        if self.json_mode:
            self._emit({"event": "log", "level": "info", "message": message})
        else:
            print(message, file=self.err, flush=True)

    def debug(self, message):
        if not self.verbose:
            return
        if self.json_mode:
            self._emit({"event": "log", "level": "debug", "message": message})
        else:
            print("  " + message, file=self.err, flush=True)

    def warn(self, message):
        if self.json_mode:
            self._emit({"event": "log", "level": "warn", "message": message})
        else:
            print(f"warning: {message}", file=self.err, flush=True)

    def step(self, step, message, item=None):
        if self.json_mode:
            d = {"event": "step", "step": step, "message": message}
            if item is not None:
                d["item"] = item
            self._emit(d)
        else:
            print(f"==> {message}", file=self.err, flush=True)

    def progress(self, step, fraction, item=None):
        fraction = max(0.0, min(1.0, fraction))
        key = (step, item)
        now = time.monotonic()
        last = self._last_progress.get(key)
        # throttle: at most ~4 updates/s, always report completion
        if last and fraction < 1.0 and now - last[0] < 0.25:
            return
        if last and abs(last[1] - fraction) < 1e-9:
            return
        self._last_progress[key] = (now, fraction)
        if self.json_mode:
            d = {"event": "progress", "step": step, "fraction": round(fraction, 4)}
            if item is not None:
                d["item"] = item
            self._emit(d)
        elif self.err.isatty():
            label = f"{step} {item}" if item else step
            end = "\n" if fraction >= 1.0 else ""
            print(f"\r    {label}: {fraction * 100:5.1f}%", end=end, file=self.err, flush=True)

    def result(self, data, human=None):
        """Final output. `human` is the text printed in non-JSON mode."""
        if self.json_mode:
            d = {"event": "result", "ok": True}
            d.update(data)
            self._emit(d)
        elif human is not None:
            print(human, file=self.out, flush=True)

    def error(self, message, hint=None, **extra):
        if self.json_mode:
            d = {"event": "error", "ok": False, "message": message}
            if hint:
                d["hint"] = hint
            d.update(extra)
            self._emit(d)
        else:
            print(f"error: {message}", file=self.err, flush=True)
            for k, v in extra.items():
                if k == "issues":
                    for issue in v:
                        print(f"  - {issue['path']}: {issue['message']}" if issue.get("path")
                              else f"  - {issue['message']}", file=self.err)
                elif k == "output" and v:
                    print("---- tool output (tail) ----", file=self.err)
                    print(v, file=self.err)
                    print("----------------------------", file=self.err)
                elif k == "log" and v:
                    print(f"full log: {v}", file=self.err)
            if hint:
                print(hint, file=self.err, flush=True)
