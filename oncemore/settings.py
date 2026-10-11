"""Settings of oncemore on this computer, not of a project: where the
media cache goes.

The media cache holds what oncemore makes to build fast and to show
things in the editor: encoded titles and menus, rendered slideshows,
joined clips, playback copies. It is in the project folder
(<project>/.oncemore-cache) unless a folder is chosen (Preferences, or
ONCEMORE_CACHE): then each project has its own folder in it, named after
the project folder (and a hash of its path, so two projects of the same
name do not share one).
"""

import hashlib
import json
import os
import re
import sys

CACHE_NAME = ".oncemore-cache"


def config_dir():
    """Where oncemore keeps what is not part of a project (the recent
    projects list, these settings): ONCEMORE_CONFIG, else the platform's
    place for it."""
    env = os.environ.get("ONCEMORE_CONFIG")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/oncemore")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "oncemore")


def _path():
    return os.path.join(config_dir(), "settings.json")


def load():
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data):
    os.makedirs(config_dir(), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _path())


def cache_folder():
    """The chosen media cache folder, or None (each project's own)."""
    return os.environ.get("ONCEMORE_CACHE") or load().get("cache_dir") or None


def set_cache_folder(path):
    """Choose the media cache folder (None: back in each project). It must
    be an absolute path; it is made if it is not there."""
    data = load()
    if not path:
        data.pop("cache_dir", None)
    else:
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            raise ValueError("the media cache folder must be an absolute path")
        os.makedirs(path, exist_ok=True)
        if not os.access(path, os.W_OK):
            raise ValueError(f"cannot write to {path}")
        data["cache_dir"] = path
    save(data)


def cache_dir(base_dir):
    """The media cache of the project in `base_dir`."""
    root = cache_folder()
    if not root:
        return os.path.join(base_dir, CACHE_NAME)
    full = os.path.abspath(base_dir)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(full)).strip("._") or "project"
    return os.path.join(root, f"{name[:40]}-{hashlib.sha256(full.encode('utf-8')).hexdigest()[:10]}")
