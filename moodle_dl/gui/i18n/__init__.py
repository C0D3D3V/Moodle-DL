"""GUI internationalization (i18n) support.

User-facing strings in the GUI are wrapped in ``self.tr(...)`` (inside ``QObject``
subclasses) or :func:`PySide6.QtCore.QCoreApplication.translate` (module level).
At startup :func:`install_translators` loads the compiled ``.qm`` catalog for the
selected language and installs it on the :class:`QApplication`.

Translation catalogs live next to this module as ``moodledl_<lang>.qm`` and are
generated from the matching ``.ts`` files (see ``moodle_dl/gui/i18n/README.md``).
"""

import logging
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator

_I18N_DIR = Path(__file__).parent
_CATALOG = 'moodledl'
_SETTINGS_ORG = 'Moodle-DL'
_SETTINGS_APP = 'Moodle-DL'
_SETTINGS_KEY = 'gui/language'

# Languages the GUI can be displayed in. The first element of each tuple is the
# code stored in settings (``'system'`` follows the OS locale); the second is the
# label shown in the language picker (kept untranslated — endonyms).
AVAILABLE_LANGUAGES = [
    ('system', 'System default'),
    ('en', 'English'),
    ('de', 'Deutsch'),
]

# QTranslator instances must outlive this function call, otherwise Qt drops them.
_translators = []


def _settings() -> QSettings:
    return QSettings(_SETTINGS_ORG, _SETTINGS_APP)


def get_language() -> str:
    """Return the stored UI language code (``'system'`` if unset)."""
    return _settings().value(_SETTINGS_KEY, 'system')


def set_language(code: str) -> None:
    """Persist the UI language *code*. Takes effect on next start."""
    _settings().setValue(_SETTINGS_KEY, code)


def _resolve_locale(code: str) -> QLocale:
    return QLocale.system() if code == 'system' else QLocale(code)


def install_translators(app) -> None:
    """Load and install the Qt and application translation catalogs on *app*.

    Must be called after the :class:`QApplication` exists but before any widgets
    are created, so that ``tr()`` calls during UI setup are translated.
    """
    locale = _resolve_locale(get_language())

    # Qt's own catalog translates standard dialog buttons (OK/Cancel/Yes/No, ...).
    qt_translator = QTranslator(app)
    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(locale, 'qtbase', '_', qt_path):
        app.installTranslator(qt_translator)
        _translators.append(qt_translator)

    # Application catalog: moodledl_<lang>.qm next to this module.
    app_translator = QTranslator(app)
    if app_translator.load(locale, _CATALOG, '_', str(_I18N_DIR)):
        app.installTranslator(app_translator)
        _translators.append(app_translator)
    else:
        logging.debug('No GUI translation catalog found for locale %s', locale.name())
