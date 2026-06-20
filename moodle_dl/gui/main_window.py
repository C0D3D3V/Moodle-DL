import logging

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QToolBar,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.pages.config_page import ConfigPage
from moodle_dl.gui.pages.download_page import DownloadPage
from moodle_dl.gui.pages.login_page import LoginPage
from moodle_dl.gui.pages.notifications_page import NotificationsPage
from moodle_dl.gui.pages.settings_page import SettingsPage
from moodle_dl.version import __version__


class MainWindow(QMainWindow):
    PAGE_LOGIN = 0
    PAGE_CONFIG = 1
    PAGE_DOWNLOAD = 2
    PAGE_SETTINGS = 3
    PAGE_NOTIFICATIONS = 4

    def __init__(self, opts) -> None:
        super().__init__()
        self.opts = opts
        self.config = ConfigHelper(opts)
        self._logged_in = False

        self.setWindowTitle(f'Moodle-DL v{__version__}')
        self.setMinimumSize(800, 600)

        # Restore window geometry
        self._settings = QSettings('Moodle-DL', 'Moodle-DL')
        geometry = self._settings.value('window/geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)

        self._setup_ui()
        self._setup_shortcuts()
        self._try_auto_login()

    def _setup_ui(self) -> None:
        """Set up the main UI: pages, toolbar, status bar, and signals."""
        # Central stacked widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Pages
        self.login_page = LoginPage(self.config, self.opts)
        self.config_page = ConfigPage(self.config, self.opts)
        self.download_page = DownloadPage(self.config, self.opts)
        self.settings_page = SettingsPage(self.config, self.opts)
        self.notifications_page = NotificationsPage(self.config, self.opts)

        self.stack.addWidget(self.login_page)  # index 0
        self.stack.addWidget(self.config_page)  # index 1
        self.stack.addWidget(self.download_page)  # index 2
        self.stack.addWidget(self.settings_page)  # index 3
        self.stack.addWidget(self.notifications_page)  # index 4

        # Toolbar navigation (text-only)
        self.toolbar = QToolBar('Navigation')
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.act_login = QAction('Login', self)
        self.act_login.triggered.connect(lambda: self._navigate(self.PAGE_LOGIN))
        self.toolbar.addAction(self.act_login)

        self.act_config = QAction('Courses', self)
        self.act_config.setEnabled(False)
        self.act_config.triggered.connect(lambda: self._navigate(self.PAGE_CONFIG))
        self.toolbar.addAction(self.act_config)

        self.act_download = QAction('Download', self)
        self.act_download.setEnabled(False)
        self.act_download.triggered.connect(lambda: self._navigate(self.PAGE_DOWNLOAD))
        self.toolbar.addAction(self.act_download)

        self.act_settings = QAction('Settings', self)
        self.act_settings.setEnabled(False)
        self.act_settings.triggered.connect(lambda: self._navigate(self.PAGE_SETTINGS))
        self.toolbar.addAction(self.act_settings)

        self.act_notifications = QAction('Notifications', self)
        self.act_notifications.setEnabled(False)
        self.act_notifications.triggered.connect(lambda: self._navigate(self.PAGE_NOTIFICATIONS))
        self.toolbar.addAction(self.act_notifications)

        self._nav_actions = [
            self.act_login,
            self.act_config,
            self.act_download,
            self.act_settings,
            self.act_notifications,
        ]

        # Separator + tools
        self.toolbar.addSeparator()

        self.act_manage_db = QAction('Missing Files', self)
        self.act_manage_db.setEnabled(False)
        self.act_manage_db.setToolTip(
            'Find files tracked in the database but missing from disk. Remove entries to re-download them.'
        )
        self.act_manage_db.triggered.connect(self._on_manage_db)
        self.toolbar.addAction(self.act_manage_db)

        self.act_old_files = QAction('Outdated Copies', self)
        self.act_old_files.setEnabled(False)
        self.act_old_files.setToolTip(
            'Find old file versions that have been replaced by newer ones. Delete them to free disk space.'
        )
        self.act_old_files.triggered.connect(self._on_old_files)
        self.toolbar.addAction(self.act_old_files)

        self.toolbar.addSeparator()

        self.act_logout = QAction('Logout', self)
        self.act_logout.setEnabled(False)
        self.act_logout.setToolTip('Log out and return to the login page.')
        self.act_logout.triggered.connect(self._on_logout)
        self.toolbar.addAction(self.act_logout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Please log in to your Moodle account.')

        # Wire signals
        self.login_page.login_successful.connect(self._on_login_success)
        self.login_page.login_failed.connect(self._on_login_failed)
        self.config_page.config_saved.connect(self.download_page.invalidate)
        self.settings_page.config_saved.connect(self.download_page.invalidate)

    def _setup_shortcuts(self) -> None:
        """Set up Alt+1..5 navigation shortcuts."""
        for i, page_index in enumerate(
            [
                self.PAGE_LOGIN,
                self.PAGE_CONFIG,
                self.PAGE_DOWNLOAD,
                self.PAGE_SETTINGS,
                self.PAGE_NOTIFICATIONS,
            ]
        ):
            shortcut = QShortcut(QKeySequence(f'Alt+{i + 1}'), self)
            shortcut.activated.connect(lambda idx=page_index: self._navigate(idx))

    def _try_auto_login(self) -> None:
        """If a valid config already exists, skip login."""
        try:
            self.config.load()
            token = self.config.get_token()
            if token:
                self._enable_navigation()
                self._navigate(self.PAGE_DOWNLOAD)
                self.status_bar.showMessage('Loaded existing configuration.')
                return
        except (ConfigHelper.NoConfigError, ValueError):
            pass

    def _on_login_success(self) -> None:
        """Handle successful login from any login method."""
        logging.info('Login successful')
        # Reload config after login saved tokens
        try:
            self.config.load()
        except ConfigHelper.NoConfigError:
            pass
        self._enable_navigation()
        self._navigate(self.PAGE_CONFIG)
        self.status_bar.showMessage('Login successful. Configure your courses.')

    def _on_login_failed(self, error_msg: str) -> None:
        """Handle login failure."""
        logging.error('Login failed: %s', error_msg)
        QMessageBox.critical(self, 'Login Failed', error_msg)
        self.status_bar.showMessage('Login failed.')

    def _enable_navigation(self) -> None:
        """Enable all navigation actions after successful login."""
        self._logged_in = True
        self.act_config.setEnabled(True)
        self.act_download.setEnabled(True)
        self.act_settings.setEnabled(True)
        self.act_notifications.setEnabled(True)
        self.act_manage_db.setEnabled(True)
        self.act_old_files.setEnabled(True)
        self.act_logout.setEnabled(True)

    def _navigate(self, page_index: int) -> None:
        """Navigate to a page and update the active indicator."""
        self.stack.setCurrentIndex(page_index)

        # Update active action font (bold + underline for active, normal for rest)
        for i, action in enumerate(self._nav_actions):
            font = QFont()
            if i == page_index:
                font.setBold(True)
                font.setUnderline(True)
            action.setFont(font)

        if page_index == self.PAGE_CONFIG:
            self.config_page.on_show()
        elif page_index == self.PAGE_DOWNLOAD:
            self.download_page.on_show()
        elif page_index == self.PAGE_SETTINGS:
            self.settings_page.on_show()
        elif page_index == self.PAGE_NOTIFICATIONS:
            self.notifications_page.on_show()

    def _on_logout(self) -> None:
        """Log out: clear tokens, disable navigation, return to login page."""
        reply = QMessageBox.question(
            self,
            'Logout',
            'Are you sure you want to log out? Any running downloads will be cancelled.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.download_page.cancel_all()
        self.config.remove_property('token')
        self.config.remove_property('privatetoken')
        self._logged_in = False
        self.act_config.setEnabled(False)
        self.act_download.setEnabled(False)
        self.act_settings.setEnabled(False)
        self.act_notifications.setEnabled(False)
        self.act_manage_db.setEnabled(False)
        self.act_old_files.setEnabled(False)
        self.act_logout.setEnabled(False)
        self._navigate(self.PAGE_LOGIN)
        self.status_bar.showMessage('Logged out. Please log in again.')

    def _on_manage_db(self) -> None:
        """Open the database management dialog."""
        from moodle_dl.gui.dialogs.database_dialog import DatabaseManagementDialog

        dialog = DatabaseManagementDialog(self.config, self.opts, self)
        dialog.exec()

    def _on_old_files(self) -> None:
        """Open the old files dialog."""
        from moodle_dl.gui.dialogs.old_files_dialog import OldFilesDialog

        dialog = OldFilesDialog(self.config, self.opts, self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        """Save geometry, stop downloads, and clean up WebEngine on close."""
        self._settings.setValue('window/geometry', self.saveGeometry())
        # Stop any running downloads
        self.download_page.cancel_all()
        # Clean up SSO WebEngine resources to avoid profile/page teardown warning
        self.login_page.cleanup()
        super().closeEvent(event)
