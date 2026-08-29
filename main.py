#!/usr/bin/env python3
"""Convenience wrapper: `python main.py` behaves like `python detective.py`."""

import sys
from detective import main

if __name__ == "__main__":
    sys.exit(main())
