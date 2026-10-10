import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args, cwd=None, env=None, timeout=900):
    """Run `python -m oncemore ...`; return (returncode, stdout, stderr)."""
    full_env = dict(os.environ)
    full_env["PYTHONPATH"] = ROOT + os.pathsep + full_env.get("PYTHONPATH", "")
    if env:
        full_env.update(env)
    p = subprocess.run([sys.executable, "-m", "oncemore"] + list(args), cwd=cwd or ROOT,
                       env=full_env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def json_lines(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def have(*names):
    return all(shutil.which(n) for n in names)
