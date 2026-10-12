#!/usr/bin/env python3
"""Update oncemore's copy of vtskit: `tools/vendor.py vtskit ...` under the
name vtskit's own README gives.

    python tools/vendor_vtskit.py --pypi 0.1.0
    python tools/vendor_vtskit.py ../vtskit
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vendor  # noqa: E402

if __name__ == "__main__":
    sys.exit(vendor.main([sys.argv[0], "vtskit", *sys.argv[1:]]))
