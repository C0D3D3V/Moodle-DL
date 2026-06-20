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

When you add or change `tr()` strings, sync them into the `.ts` (the human-owned
source of truth) and recompile the `.qm`:

```bash
python scripts/update_translations.py
```

This runs `lupdate` (preserving existing translations, adding new strings as
`type="unfinished"`) and recompiles every `.qm`. New strings then need a human
translation — with Qt Linguist:

```bash
linguist6 moodle_dl/gui/i18n/moodledl_de.ts   # then: python scripts/update_translations.py
```

The strict CI check (`scripts/check_translations.py`) fails until every string
is translated.

Note: catalogs use `-locations none`, so the `.ts` changes only when the set of
strings changes — not on every unrelated code edit.

### The pre-commit hook does NOT edit the .ts

The `compile-translations` pre-commit hook (`scripts/compile_translations.py`)
only recompiles the `.qm` from the committed `.ts` and prints a **big warning**
(and fails) if the code has strings the `.ts` is missing. It never rewrites a
`.ts` — adding new strings to it is the deliberate `update_translations.py` step
above. (Requires the Qt tools; if absent the hook warns and skips.)

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
