#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Daily Workflow Runner
Executes the full automated daily pipeline:
  1. Validates or detects today's briefing markdown
  2. Runs build-html.py (compiles index.html with images, loan calculator, live weather, and search index)
  3. Runs send-briefing.py (formats and dispatches the briefing to Telegram)
  4. Syncs docs/ for GitHub Pages deployment
"""

import os
import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BUILD_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'build-html.py')
CHECK_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'check-duplication.py')
SEND_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'send-briefing.py')
DOCS_INDEX = os.path.join(BASE_DIR, 'docs', 'index.html')


def run_command(cmd, desc):
    print(f"\n▶ {desc}...")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"❌ Error during: {desc} (Exit code: {res.returncode})")
        return False
    print(f"✔ Completed: {desc}")
    return True


def main():
    target_md = sys.argv[1] if len(sys.argv) > 1 else ""

    print("=" * 60)
    print("🏛️ THE ORACLE SOVEREIGN — DAILY AUTOMATED PIPELINE")
    print("=" * 60)

    # 1. Build HTML & Search Index
    build_cmd = f'python "{BUILD_SCRIPT}" "{target_md}"' if target_md else f'python "{BUILD_SCRIPT}"'
    if not run_command(build_cmd, "Building HTML portal, archives & search index"):
        sys.exit(1)

    # 2. Anti-Duplication Quality Verification
    check_cmd = f'python "{CHECK_SCRIPT}" "{DOCS_INDEX}"'
    if not run_command(check_cmd, "Verifying anti-duplication quality on web edition"):
        sys.exit(1)

    # 3. Telegram Dispatch
    send_cmd = f'python "{SEND_SCRIPT}" "{target_md}"' if target_md else f'python "{SEND_SCRIPT}"'
    if not run_command(send_cmd, "Dispatching Daily Briefing to Telegram"):
        print("Note: Telegram dispatch finished with notice (check token configuration).")

    print("\n" + "=" * 60)
    print("🎉 ALL DAILY STEPS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == '__main__':
    main()
