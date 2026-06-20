#!/usr/bin/env python3
"""Pre-commit hook: recompile the GUI .qm catalogs and warn about missing strings.

This intentionally does NOT modify any ``.ts`` file — those are the human-owned
source of truth. It only:

  1. recompiles every ``moodledl_<lang>.qm`` from its committed ``.ts`` (so the
     runtime catalog always matches the source), and
  2. checks whether the code contains ``tr()`` source strings that are missing
     from the ``.ts``; if so it prints a big warning and exits non-zero so the
     developer notices (pre-commit hides hook output on success).

Adding the new strings to the ``.ts`` is a deliberate manual step:
``python scripts/update_translations.py`` (then translate them). Completeness is
enforced separately by ``scripts/check_translations.py`` in CI.

If the Qt tools are not on PATH this warns and exits 0 (never blocks a commit on
a machine without the GUI toolchain — CI is the real gate).
"""

import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUI_DIR = REPO_ROOT / 'moodle_dl' / 'gui'
I18N_DIR = GUI_DIR / 'i18n'

LUPDATE_FLAGS = ['-extensions', 'py', '-recursive', '-locations', 'none', '-no-obsolete']
_DEAD_STATES = {'obsolete', 'vanished'}


def _find(*names: str):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _source_keys(ts_path: Path) -> set:
    """Return the set of (context, source) message keys present in a .ts file."""
    keys = set()
    for ctx in ET.parse(ts_path).getroot().findall('context'):
        name = ctx.findtext('name')
        for msg in ctx.findall('message'):
            trans = msg.find('translation')
            if trans is not None and trans.get('type') in _DEAD_STATES:
                continue
            keys.add((name, msg.findtext('source')))
    return keys


def _current_keys(lupdate: str) -> set:
    """Extract the source strings currently present in the code (without touching any committed .ts)."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / 'current.ts'
        result = subprocess.run(
            [lupdate, *LUPDATE_FLAGS, str(GUI_DIR), '-ts', str(fresh)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not fresh.exists():
            print(f'warning: lupdate failed, skipping drift check:\n{result.stderr}', file=sys.stderr)
            return set()
        return _source_keys(fresh)


def _print_warning(missing_by_lang: dict) -> None:
    bar = '=' * 70
    print('\n' + bar)
    print('  ⚠  GUI TRANSLATION SOURCES (.ts) ARE MISSING NEW STRINGS')
    print(bar)
    print('  The .qm files were recompiled, but the code contains user-facing')
    print('  string(s) that are NOT in the translation source (.ts). They will')
    print('  appear untranslated (English) until added and translated.\n')
    for lang, missing in sorted(missing_by_lang.items()):
        print(f'  {lang}: {len(missing)} missing string(s):')
        for ctx, src in sorted(missing):
            print(f'      [{ctx}] {src!r}')
    print('\n  To fix:')
    print('    1. python scripts/update_translations.py   # syncs the .ts (adds them as unfinished)')
    print('    2. translate the new strings with Qt Linguist')
    print('    3. re-stage the updated .ts and .qm, then commit')
    print(bar + '\n')


def main() -> int:
    ts_files = sorted(I18N_DIR.glob('moodledl_*.ts'))
    if not ts_files:
        print(f'No translation catalogs found in {I18N_DIR}; nothing to do.')
        return 0

    lupdate = _find('pyside6-lupdate', 'lupdate6', 'lupdate')
    lrelease = _find('pyside6-lrelease', 'lrelease6', 'lrelease')
    if not lupdate or not lrelease:
        print('warning: Qt translation tools not found (need lupdate/lrelease, e.g. `pip install PySide6`).')
        print('         Skipping .qm compilation; CI will verify the catalogs.')
        return 0

    # 1. Recompile .qm from each committed .ts (never modifies the .ts).
    for ts_path in ts_files:
        qm_path = ts_path.with_suffix('.qm')
        result = subprocess.run([lrelease, str(ts_path), '-qm', str(qm_path)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f'error: lrelease failed for {ts_path.name}:\n{result.stdout}\n{result.stderr}', file=sys.stderr)
            return 1
        print(f'compiled {qm_path.name}')

    # 2. Warn (loudly) if the code has strings the .ts files do not contain.
    current = _current_keys(lupdate)
    missing_by_lang = {}
    for ts_path in ts_files:
        lang = ts_path.stem.split('_', 1)[1]
        missing = current - _source_keys(ts_path)
        if missing:
            missing_by_lang[lang] = missing

    if missing_by_lang:
        _print_warning(missing_by_lang)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
