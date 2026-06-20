# GUI translations

The PySide6 GUI is localized with Qt's translation system. User-facing strings
are wrapped in `self.tr(...)` (inside `QObject` subclasses) or
`QCoreApplication.translate(...)`. At startup `install_translators()` (see
`__init__.py`) loads the catalog for the language selected on the Settings page
(or the system locale).

## Files

- `moodledl_<lang>.ts` — translation **sources** (XML, edited by translators).
- `moodledl_<lang>.qm` — **compiled** catalogs loaded at runtime. Committed so
  the GUI is translated out of the box; regenerate them whenever a `.ts` changes.
- `_translate_de.py` — dev-only helper that fills the German `.ts` from a
  built-in English→German map (handy for bulk re-translation after `lupdate`).

The tools below come from Qt (`lupdate6` / `lrelease6`) or PySide6
(`pyside6-lupdate` / `pyside6-lrelease`) — use whichever is on your `PATH`.

## Update strings after editing the GUI

Re-extract source strings from the code into every catalog:

```bash
lupdate6 -extensions py -recursive moodle_dl/gui -ts moodle_dl/gui/i18n/moodledl_de.ts
```

New strings appear as `type="unfinished"`. Translate them with Qt Linguist:

```bash
linguist6 moodle_dl/gui/i18n/moodledl_de.ts
```

(For German you can instead extend the map in `_translate_de.py` and run
`python moodle_dl/gui/i18n/_translate_de.py`.)

Then compile to `.qm`:

```bash
lrelease6 moodle_dl/gui/i18n/moodledl_de.ts
```

## Add a new language

1. Create the source catalog (e.g. French):
   ```bash
   lupdate6 -extensions py -recursive moodle_dl/gui -ts moodle_dl/gui/i18n/moodledl_fr.ts
   ```
2. Translate it and run `lrelease6` to produce `moodledl_fr.qm`.
3. Add `('fr', 'Français')` to `AVAILABLE_LANGUAGES` in `__init__.py`.
