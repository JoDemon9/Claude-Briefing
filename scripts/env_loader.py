#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared .env loader.

generate-briefing.py and send-briefing.py each carried their own copy of this
parsing loop, and the two disagreed: one read the file as utf-8 and left
quotes in the value, the other read utf-8-sig and stripped them. Every script
now loads the same way.

Values already present in the real environment win, so CI secrets are never
shadowed by a stale local .env.
"""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')


def parse_env(path=ENV_PATH):
    """{key: value} from a .env file. Empty dict when it is absent."""
    values = {}
    if not os.path.exists(path):
        return values
    try:
        # utf-8-sig: the file is edited on Windows and may carry a BOM.
        with open(path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip().lstrip('﻿')
                if key:
                    values[key] = value.strip().strip('\'"')
    except Exception as e:
        print(f"Warning: could not read {path}: {e}")
    return values


def load_env(path=ENV_PATH):
    """Load .env into os.environ without overwriting what is already set."""
    values = parse_env(path)
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values
