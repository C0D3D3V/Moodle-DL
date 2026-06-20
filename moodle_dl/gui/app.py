import logging
import sys

from PySide6.QtWidgets import QApplication

from moodle_dl.gui.i18n import install_translators
from moodle_dl.gui.main_window import MainWindow
from moodle_dl.version import __version__

_STYLESHEET = """
QPushButton {
    padding: 6px 16px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: palette(midlight);
}
QPushButton:pressed {
    background-color: palette(mid);
}
QProgressBar::chunk {
    background-color: #4caf50;
    border-radius: 3px;
}
QTableView {
    alternate-background-color: palette(alternateBase);
}
QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {
    border: 2px solid palette(highlight);
}
QGroupBox {
    font-weight: bold;
    margin-top: 8px;
    padding-top: 16px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QToolBar {
    spacing: 6px;
    padding: 2px;
}
"""


def register_moodledl_scheme() -> None:
    """Register the moodledl:// URL scheme so WebEngine routes it through acceptNavigationRequest."""
    try:
        from PySide6.QtWebEngineCore import QWebEngineUrlScheme

        scheme = QWebEngineUrlScheme(b"moodledl")
        scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
        scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalAccessAllowed)
        QWebEngineUrlScheme.registerScheme(scheme)
    except ImportError:
        logging.debug('PySide6-WebEngine not available; moodledl:// scheme not registered')


def create_app(opts):
    """Create the QApplication and show the main window."""
    register_moodledl_scheme()
    app = QApplication(sys.argv)
    install_translators(app)
    app.setApplicationName('Moodle-DL')
    app.setApplicationVersion(__version__)
    app.setOrganizationName('Moodle-DL')
    app.setStyleSheet(_STYLESHEET)

    window = MainWindow(opts)
    window.show()

    return app
