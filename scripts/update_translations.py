#!/usr/bin/env python3
"""Regenerate the GUI translation catalogs from the current source code.

For every ``moodle_dl/gui/i18n/moodledl_<lang>.ts`` this:
  1. runs ``lupdate`` to sync source strings from the code into the .ts
     (existing translations preserved, new strings added as unfinished,
     removed strings dropped),
  2. runs ``lrelease`` to recompile the .qm.

Used both manually and by the pre-commit hook. If the Qt tools are not on PATH
it prints a warning and exits 0 (so it never blocks a commit on machines without
the GUI toolchain — the CI check is the real gate).

The .ts files are the source of truth for translations: edit them with Qt
Linguist (or by hand). Strings that are genuinely new stay ``unfinished`` until
translated, and the strict CI check will flag them.

Run:  python scripts/update_translations.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUI_DIR = REPO_ROOT / 'moodle_dl' / 'gui'
I18N_DIR = GUI_DIR / 'i18n'

# Locations are stripped (`-locations none`) so the .ts changes only when the set
# of strings changes, not on every unrelated code edit that shifts line numbers.
LUPDATE_FLAGS = ['-extensions', 'py', '-recursive', '-locations', 'none', '-no-obsolete']


def _find(*names: str):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _run(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f'error: command failed: {" ".join(cmd)}\n{result.stdout}\n{result.stderr}')


def main() -> int:
    ts_files = sorted(I18N_DIR.glob('moodledl_*.ts'))
    if not ts_files:
        print(f'No translation catalogs found in {I18N_DIR}; nothing to do.')
        return 0

    lupdate = _find('pyside6-lupdate', 'lupdate6', 'lupdate')
    lrelease = _find('pyside6-lrelease', 'lrelease6', 'lrelease')
    if not lupdate or not lrelease:
        print('warning: Qt translation tools not found (need lupdate/lrelease, e.g. `pip install PySide6`).')
        print('         Skipping translation regeneration; CI will verify the catalogs.')
        return 0

    for ts_path in ts_files:
        # lupdate merges into the existing .ts: it preserves current translations,
        # adds new source strings as unfinished, and (with -no-obsolete) drops
        # removed ones. The .ts is the source of truth for translations.
        _run([lupdate, *LUPDATE_FLAGS, str(GUI_DIR), '-ts', str(ts_path)])
        _run([lrelease, str(ts_path), '-qm', str(ts_path.with_suffix('.qm'))])
        print(f'updated {ts_path.name} and {ts_path.with_suffix(".qm").name}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
