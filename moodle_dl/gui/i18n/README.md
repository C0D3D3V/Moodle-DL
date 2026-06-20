# GUI translations

The PySide6 GUI is localized with Qt's translation system. User-facing strings
are wrapped in `self.tr(...)` (inside `QObject` subclasses) or
`QCoreApplication.translate(...)`. At startup `install_translators()` (see
`__init__.py`) loads the catalog for the language selected on the Settings page
(or the system locale).

## Files

- `moodledl_<lang>.ts` — translation **sources** (XML); the source of truth for
  translations, edited with Qt Linguist (or by hand).
- `moodledl_<lang>.qm` — **compiled** catalogs loaded at runtime. Committed so
  the GUI is translated out of the box; regenerate them whenever a `.ts` changes.

The tools below come from Qt (`lupdate6` / `lrelease6`) or PySide6
(`pyside6-lupdate` / `pyside6-lrelease`) — use whichever is on your `PATH`.

## Update strings after editing the GUI

One command re-extracts strings (preserving existing translations) and recompiles
every `.qm`:

```bash
python scripts/update_translations.py
```

This also runs automatically as a **pre-commit hook** whenever you change GUI
code, so the catalogs stay in sync (requires the Qt tools, e.g.
`pip install PySide6`; if they are absent the hook warns and skips).

Brand-new strings are added as `type="unfinished"` and must be translated by a
human — the strict CI check (`scripts/check_translations.py`) fails until every
string is translated. Translate them with Qt Linguist (then recompile the `.qm`):

```bash
linguist6 moodle_dl/gui/i18n/moodledl_de.ts   # then: python scripts/update_translations.py
```

Note: catalogs are generated with `-locations none`, so the `.ts` changes only
when the set of strings changes — not on every unrelated code edit.

### Manual equivalent

```bash
lupdate6 -extensions py -recursive -locations none -no-obsolete moodle_dl/gui -ts moodle_dl/gui/i18n/moodledl_de.ts
# translate moodledl_de.ts with Qt Linguist, then:
lrelease6 moodle_dl/gui/i18n/moodledl_de.ts
```

## Add a new language

1. Create the source catalog (e.g. French):
   ```bash
   lupdate6 -extensions py -recursive -locations none -no-obsolete moodle_dl/gui -ts moodle_dl/gui/i18n/moodledl_fr.ts
   ```
2. Translate it with Qt Linguist.
3. Run `python scripts/update_translations.py` to compile `moodledl_fr.qm`.
4. Add `('fr', 'Français')` to `AVAILABLE_LANGUAGES` in `__init__.py`.

From then on the pre-commit hook and the CI check cover the new language
automatically (every `moodledl_*.ts` is picked up by glob).
