#!/usr/bin/env python3
"""Bump the patch version in app.py (e.g. 0.6.0 → 0.6.1).

Usage:
    python bump_version.py          # bump patch
    python bump_version.py minor    # bump minor (0.6.1 → 0.7.0)
    python bump_version.py major    # bump major (0.7.0 → 1.0.0)

Called automatically by .githooks/pre-commit if configured:
    git config core.hooksPath .githooks
"""
import re
import sys
from pathlib import Path

APP_PY = Path(__file__).resolve().parent / 'app.py'
VERSION_RE = re.compile(r"^(VERSION\s*=\s*')(\d+)\.(\d+)\.(\d+)(')", re.MULTILINE)


def bump(level='patch'):
    text = APP_PY.read_text(encoding='utf-8')
    m = VERSION_RE.search(text)
    if not m:
        print('ERROR: VERSION line not found in app.py', file=sys.stderr)
        sys.exit(1)

    major, minor, patch = int(m.group(2)), int(m.group(3)), int(m.group(4))

    if level == 'major':
        major, minor, patch = major + 1, 0, 0
    elif level == 'minor':
        major, minor, patch = major, minor + 1, 0
    else:
        patch += 1

    new_version = f'{major}.{minor}.{patch}'
    new_line = f"{m.group(1)}{new_version}{m.group(5)}"
    text = text[:m.start()] + new_line + text[m.end():]
    APP_PY.write_text(text, encoding='utf-8')
    print(f'Version bumped to {new_version}')
    return new_version


if __name__ == '__main__':
    level = sys.argv[1] if len(sys.argv) > 1 else 'patch'
    if level not in ('patch', 'minor', 'major'):
        print(f'Usage: {sys.argv[0]} [patch|minor|major]', file=sys.stderr)
        sys.exit(1)
    bump(level)
