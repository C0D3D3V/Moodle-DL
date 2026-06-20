#!/usr/bin/env python3
"""CI gate: GUI translation catalogs are complete and in sync with the code.

Fails (exit 1) if any of the following is true for the PySide6 GUI:

1. Stale extraction  — the code contains tr() source strings that are not present
   in a committed ``moodle_dl/gui/i18n/moodledl_<lang>.ts`` (or the .ts lists
   strings no longer in the code).
2. Untranslated      — a committed .ts has an empty or ``type="unfinished"``
   translation.
3. Stale .qm         — the committed ``moodledl_<lang>.qm`` does not contain every
   translation from its .ts (i.e. lrelease was not re-run after editing the .ts).

Run locally:  python scripts/check_translations.py

Requires ``pyside6-lupdate`` (or ``lupdate6``/``lupdate``) on PATH and the
``PySide6`` Python package (for verifying the compiled .qm).
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

# Translation states that mean "this entry no longer applies"; ignored everywhere.
_DEAD_STATES = {'obsolete', 'vanished'}


def _find_lupdate() -> str:
    for name in ('pyside6-lupdate', 'lupdate6', 'lupdate'):
        path = shutil.which(name)
        if path:
            return path
    sys.exit('error: no lupdate tool found (install PySide6 or Qt: pyside6-lupdate / lupdate6).')


def _live_messages(ts_path: Path):
    """Yield (context, source, translation_element) for every non-dead message."""
    root = ET.parse(ts_path).getroot()
    for ctx in root.findall('context'):
        name = ctx.findtext('name')
        for msg in ctx.findall('message'):
            trans = msg.find('translation')
            state = trans.get('type') if trans is not None else None
            if state in _DEAD_STATES:
                continue
            yield name, msg.findtext('source'), trans


def _source_keys(ts_path: Path) -> set:
    return {(ctx, src) for ctx, src, _ in _live_messages(ts_path)}


def extract_current_keys(lupdate: str) -> set:
    """Run lupdate against the code into a throwaway .ts and return its source keys."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / 'current.ts'
        result = subprocess.run(
            [lupdate, '-extensions', 'py', '-recursive', str(GUI_DIR), '-ts', str(fresh)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not fresh.exists():
            sys.exit(f'error: lupdate failed:\n{result.stdout}\n{result.stderr}')
        return _source_keys(fresh)


def check_extraction(ts_path: Path, current_keys: set) -> list:
    committed = _source_keys(ts_path)
    problems = []
    for ctx, src in sorted(current_keys - committed):
        problems.append(f'  + missing from .ts (run lupdate): [{ctx}] {src!r}')
    for ctx, src in sorted(committed - current_keys):
        problems.append(f'  - stale in .ts, no longer in code (run lupdate): [{ctx}] {src!r}')
    return problems


def check_translated(ts_path: Path) -> list:
    problems = []
    for ctx, src, trans in _live_messages(ts_path):
        unfinished = trans is None or trans.get('type') == 'unfinished' or not (trans.text or '').strip()
        if unfinished:
            problems.append(f'  [{ctx}] {src!r}')
    return problems


def check_qm_in_sync(ts_path: Path, qm_path: Path) -> list:
    from PySide6.QtCore import QTranslator  # imported lazily so step 1/2 work without a GUI build

    if not qm_path.exists():
        return [f'  {qm_path.name} is missing — run lrelease on {ts_path.name}']

    translator = QTranslator()
    if not translator.load(str(qm_path)):
        return [f'  {qm_path.name} could not be loaded — regenerate it with lrelease']

    problems = []
    for ctx, src, trans in _live_messages(ts_path):
        expected = (trans.text or '') if trans is not None else ''
        if not expected:
            continue  # untranslated entries are reported by check_translated()
        if translator.translate(ctx, src) != expected:
            problems.append(f'  [{ctx}] {src!r} not current in {qm_path.name}')
    return problems


def main() -> int:
    ts_files = sorted(I18N_DIR.glob('moodledl_*.ts'))
    if not ts_files:
        sys.exit(f'error: no translation catalogs found in {I18N_DIR}')

    lupdate = _find_lupdate()
    current_keys = extract_current_keys(lupdate)
    failed = False

    for ts_path in ts_files:
        lang = ts_path.stem.split('_', 1)[1]
        qm_path = ts_path.with_suffix('.qm')
        sections = {
            'source strings not extracted / stale': check_extraction(ts_path, current_keys),
            'untranslated strings (strict mode requires all to be translated)': check_translated(ts_path),
            'compiled .qm out of sync with .ts': check_qm_in_sync(ts_path, qm_path),
        }
        lang_failed = any(sections.values())
        if lang_failed:
            failed = True
            print(f'\n✗ {lang}: translation problems in {ts_path.name}')
            for title, problems in sections.items():
                if problems:
                    print(f'  {title}:')
                    for line in problems:
                        print(f'  {line}')
        else:
            print(f'✓ {lang}: {ts_path.name} complete and in sync')

    if failed:
        print('\nTo fix:')
        print('  1. lupdate6 -extensions py -recursive moodle_dl/gui -ts moodle_dl/gui/i18n/moodledl_<lang>.ts')
        print('  2. Translate the new strings with Qt Linguist (or edit the .ts directly)')
        print('  3. lrelease6 moodle_dl/gui/i18n/moodledl_<lang>.ts')
        print('  See moodle_dl/gui/i18n/README.md for details.')
        return 1

    print('\nAll GUI translation catalogs are complete and in sync.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
