from __future__ import annotations

import logging
import secrets

from PySide6.QtCore import QBuffer, Qt, QUrl, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.style_utils import set_status_text
from moodle_dl.gui.workers import LoginWorker, SSOTokenWorker
from moodle_dl.moodle.moodle_service import MoodleService
from moodle_dl.types import MoodleURL

# Custom QWebEnginePage that intercepts moodledl:// navigations.
# This replaces the broken QWebEngineUrlSchemeHandler approach — Qt's URL
# parser strips token data from custom-scheme URLs, but
# acceptNavigationRequest() receives the QUrl before scheme-specific parsing.
try:
    from PySide6.QtWebEngineCore import QWebEnginePage as _QWebEnginePage
    from PySide6.QtWebEngineCore import (
        QWebEngineUrlRequestJob,
        QWebEngineUrlSchemeHandler,
    )

    def _extract_sso_url(url) -> str | None:
        """Try multiple QUrl methods to extract a string containing 'token='."""
        # Method 1: toString()
        s = url.toString()
        if s and 'token=' in s:
            return s

        # Method 2: toEncoded() — raw bytes may survive when QUrl is "invalid"
        try:
            raw = url.toEncoded()
            if raw:
                s = bytes(raw).decode('utf-8', errors='replace')
                if 'token=' in s:
                    return s
        except Exception:
            pass

        # Method 3: path() — with Syntax.Path, data may land here as //token=...
        path = url.path()
        if path and 'token=' in path:
            return path

        # Method 4: authority()/host() — Qt may misparse token=... as authority
        for accessor in (url.authority, url.host, url.userInfo, url.fragment, url.query):
            try:
                val = accessor()
                if val and 'token=' in val:
                    return val
            except Exception:
                pass

        # Log diagnostics for debugging
        logging.warning(
            'SSO URL extraction failed. isValid=%s path=%r authority=%r host=%r query=%r encoded=%r',
            url.isValid(),
            url.path(),
            url.authority(),
            url.host(),
            url.query(),
            bytes(url.toEncoded()).decode('utf-8', errors='ignore') if url.toEncoded() else '',
        )
        return None

    class _SSOInterceptPage(_QWebEnginePage):
        """QWebEnginePage that intercepts moodledl:// navigations."""

        token_received = Signal(str)

        def acceptNavigationRequest(self, url, nav_type, is_main_frame):
            url_string = url.toString()
            logging.debug(
                'Navigation request: type=%s scheme=%s url=%s',
                nav_type,
                url.scheme(),
                url_string[:120] if url_string else '<empty>',
            )
            if url.scheme() == 'moodledl':
                extracted = _extract_sso_url(url)
                if extracted:
                    logging.info('SSO callback intercepted (nav): %s...', extracted[:80])
                    self.token_received.emit(extracted)
                    return False  # Block navigation, token captured
                # Extraction failed — let navigation proceed to scheme handler
                logging.info('SSO nav intercept: URL empty, deferring to scheme handler')
                return True
            return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    class _SSOSchemeHandler(QWebEngineUrlSchemeHandler):
        """Fallback handler for moodledl:// scheme."""

        token_received = Signal(str)

        def requestStarted(self, request) -> None:
            url = request.requestUrl()
            extracted = _extract_sso_url(url)
            if extracted:
                logging.info('SSO scheme handler got request: %s...', extracted[:80])
                self.token_received.emit(extracted)
                request.fail(QWebEngineUrlRequestJob.Error.RequestDenied)
                return
            # QUrl extraction failed — serve HTML that reports URL via JavaScript
            logging.info('SSO scheme handler: QUrl empty, serving JS title probe')
            html = (
                b'<html><head><script>'
                b'document.title = window.location.href;'
                b'</script></head>'
                b'<body>Completing SSO login...</body></html>'
            )
            buf = QBuffer(request)
            buf.setData(html)
            buf.open(QBuffer.OpenModeFlag.ReadOnly)
            request.reply(b'text/html', buf)

except ImportError:
    _SSOInterceptPage = None
    _SSOSchemeHandler = None


class LoginPage(QWidget):
    login_successful = Signal()
    login_failed = Signal(str)

    def __init__(self, config: ConfigHelper, opts) -> None:
        super().__init__()
        self.config = config
        self.opts = opts
        self._worker = None
        self._sso_worker = None
        self._sso_profile = None
        self._sso_page = None
        self._sso_scheme_handler = None
        self._sso_token_received = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Normal Login Tab ---
        normal_tab = QWidget()
        normal_layout = QVBoxLayout(normal_tab)

        form_group = QGroupBox('Moodle Login')
        form_layout = QFormLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('https://moodle.example.com')
        self.url_input.returnPressed.connect(self._on_login_clicked)
        form_layout.addRow('Moodle URL:', self.url_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('your.username')
        self.username_input.returnPressed.connect(self._on_login_clicked)
        form_layout.addRow('Username:', self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText('your password')
        self.password_input.returnPressed.connect(self._on_login_clicked)
        form_layout.addRow('Password:', self.password_input)

        form_group.setLayout(form_layout)
        normal_layout.addWidget(form_group)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton('Login')
        self.login_btn.clicked.connect(self._on_login_clicked)
        btn_layout.addStretch()
        btn_layout.addWidget(self.login_btn)
        normal_layout.addLayout(btn_layout)

        self.normal_status = QLabel('')
        normal_layout.addWidget(self.normal_status)
        normal_layout.addStretch()

        self.tabs.addTab(normal_tab, 'Normal Login')

        # --- SSO Login Tab ---
        sso_tab = QWidget()
        sso_layout = QVBoxLayout(sso_tab)

        sso_url_layout = QFormLayout()
        self.sso_url_input = QLineEdit()
        self.sso_url_input.setPlaceholderText('https://moodle.example.com')
        sso_url_layout.addRow('Moodle URL:', self.sso_url_input)
        sso_layout.addLayout(sso_url_layout)

        self.sso_open_btn = QPushButton('Open SSO Login in Browser')
        self.sso_open_btn.clicked.connect(self._on_sso_open_clicked)
        sso_layout.addWidget(self.sso_open_btn)

        self.sso_status = QLabel(
            'Enter your Moodle URL and click the button to start SSO login.\n'
            'The login page will open below (requires PySide6-WebEngine).'
        )
        sso_layout.addWidget(self.sso_status)

        self._sso_webview = None
        self._sso_webview_container = QVBoxLayout()
        sso_layout.addLayout(self._sso_webview_container, 1)

        sso_layout.addStretch()

        self.tabs.addTab(sso_tab, 'SSO Login')

        # --- Token Login Tab ---
        token_tab = QWidget()
        token_layout = QVBoxLayout(token_tab)

        token_group = QGroupBox('Token Login')
        token_form = QFormLayout()

        self.token_url_input = QLineEdit()
        self.token_url_input.setPlaceholderText('https://moodle.example.com')
        self.token_url_input.returnPressed.connect(self._on_token_login_clicked)
        token_form.addRow('Moodle URL:', self.token_url_input)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText('Paste your Moodle token here')
        self.token_input.returnPressed.connect(self._on_token_login_clicked)
        token_form.addRow('Token:', self.token_input)

        self.private_token_input = QLineEdit()
        self.private_token_input.setPlaceholderText('Optional')
        self.private_token_input.returnPressed.connect(self._on_token_login_clicked)
        token_form.addRow('Private Token:', self.private_token_input)

        token_group.setLayout(token_form)
        token_layout.addWidget(token_group)

        token_btn_layout = QHBoxLayout()
        self.token_login_btn = QPushButton('Save Token')
        self.token_login_btn.clicked.connect(self._on_token_login_clicked)
        token_btn_layout.addStretch()
        token_btn_layout.addWidget(self.token_login_btn)
        token_layout.addLayout(token_btn_layout)

        self.token_status = QLabel('')
        token_layout.addWidget(self.token_status)
        token_layout.addStretch()

        self.tabs.addTab(token_tab, 'Token Login')

        # Pre-fill URL from existing config
        self._prefill_url()

    def _prefill_url(self) -> None:
        """Pre-fill Moodle URL fields from existing config."""
        try:
            self.config.load()
            moodle_url = self.config.get_moodle_URL()
            url_str = moodle_url.url_base
            self.url_input.setText(url_str)
            self.sso_url_input.setText(url_str)
            self.token_url_input.setText(url_str)
        except (ConfigHelper.NoConfigError, ValueError):
            pass

    def _parse_moodle_url(self, url_text: str) -> MoodleURL:
        """Parse a URL string into a MoodleURL object."""
        url_text = url_text.strip()
        if not url_text:
            raise ValueError('Please enter a Moodle URL.')
        if not url_text.startswith('http://') and not url_text.startswith('https://'):
            url_text = 'https://' + url_text

        use_http = url_text.startswith('http://')
        domain, path = MoodleService.split_moodle_url(url_text)
        if not domain:
            raise ValueError('Invalid Moodle URL.')
        return MoodleURL(use_http=use_http, domain=domain, path=path)

    # --- Normal Login ---

    def _on_login_clicked(self) -> None:
        """Handle normal login button click."""
        try:
            moodle_url = self._parse_moodle_url(self.url_input.text())
        except ValueError as e:
            self.login_failed.emit(str(e))
            return

        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.login_failed.emit('Please enter both username and password.')
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText('Logging in\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.normal_status, 'Logging in\u2026', 'info')

        self._worker = LoginWorker(self.config, self.opts, moodle_url, username, password)
        self._worker.login_successful.connect(self._on_worker_login_success)
        self._worker.login_failed.connect(self._on_worker_login_failed)
        self._worker.start()

    def _on_worker_login_success(self) -> None:
        """Handle successful normal login."""
        self.login_btn.setEnabled(True)
        self.login_btn.setText('Login')
        self.unsetCursor()
        set_status_text(self.normal_status, 'Login successful!', 'success')
        self.login_successful.emit()

    def _on_worker_login_failed(self, error_msg: str) -> None:
        """Handle failed normal login."""
        self.login_btn.setEnabled(True)
        self.login_btn.setText('Login')
        self.unsetCursor()
        set_status_text(self.normal_status, f'Login failed: {error_msg}', 'error')
        self.login_failed.emit(error_msg)

    # --- Token Login ---

    def _on_token_login_clicked(self) -> None:
        """Handle token-based login."""
        try:
            moodle_url = self._parse_moodle_url(self.token_url_input.text())
        except ValueError as e:
            set_status_text(self.token_status, str(e), 'error')
            return

        token = self.token_input.text().strip()
        if not token:
            set_status_text(self.token_status, 'Please enter a token.', 'error')
            return

        private_token = self.private_token_input.text().strip() or None

        self.token_login_btn.setEnabled(False)
        self.token_login_btn.setText('Saving\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))

        try:
            self.config.set_moodle_URL(moodle_url)
            self.config.set_tokens(token, private_token)
            set_status_text(self.token_status, 'Token saved successfully!', 'success')
            self.login_successful.emit()
        except Exception as e:
            set_status_text(self.token_status, f'Failed to save token: {e}', 'error')
        finally:
            self.token_login_btn.setEnabled(True)
            self.token_login_btn.setText('Save Token')
            self.unsetCursor()

    # --- SSO ---

    def _on_sso_load_finished(self, ok: bool) -> None:
        """Handle page load completion. Avoids overwriting status after token receipt."""
        logging.debug('SSO loadFinished: ok=%s, token_received=%s', ok, self._sso_token_received)
        if self._sso_token_received:
            return  # Don't overwrite "Token received, verifying..." status
        if ok:
            # If this is our scheme handler page, try JS extraction
            if self._sso_page is not None:
                self._sso_page.runJavaScript(
                    "window.location.href",
                    self._on_js_location_result,
                )
            set_status_text(self.sso_status, 'Enter your credentials below.', 'info')
        else:
            set_status_text(
                self.sso_status,
                'Page load error. The SSO login page may still appear after redirects.',
                'warning',
            )

    def _on_sso_open_clicked(self) -> None:
        """Open the SSO login page in an embedded browser."""
        try:
            moodle_url = self._parse_moodle_url(self.sso_url_input.text())
        except ValueError as e:
            self.login_failed.emit(str(e))
            return

        self._sso_moodle_url = moodle_url
        self._sso_token_received = False
        passport = secrets.token_hex(16)
        sso_url = (
            f'{moodle_url.url_base}admin/tool/mobile/launch.php'
            f'?service=moodle_mobile_app&passport={passport}&urlscheme=moodledl'
        )
        logging.debug('SSO launch URL: %s', sso_url)

        self.sso_open_btn.setEnabled(False)
        self.sso_open_btn.setText('Opening\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))

        try:
            from PySide6.QtWebEngineCore import QWebEngineProfile
            from PySide6.QtWebEngineWidgets import QWebEngineView

            if _SSOInterceptPage is None:
                raise ImportError('_SSOInterceptPage not available')

            # Clear old webview if any
            if self._sso_webview is not None:
                self._sso_webview_container.removeWidget(self._sso_webview)
                self._sso_webview.deleteLater()
                self._sso_webview = None

            self._sso_profile = QWebEngineProfile('moodledl_sso', self)

            self._sso_scheme_handler = _SSOSchemeHandler(self._sso_profile)
            self._sso_scheme_handler.token_received.connect(self._on_sso_token_received)
            self._sso_profile.installUrlSchemeHandler(b"moodledl", self._sso_scheme_handler)

            self._sso_page = _SSOInterceptPage(self._sso_profile, self)
            self._sso_page.token_received.connect(self._on_sso_token_received)

            self._sso_webview = QWebEngineView()
            self._sso_webview.setPage(self._sso_page)
            self._sso_webview.setMinimumHeight(400)
            self._sso_webview_container.addWidget(self._sso_webview)

            set_status_text(self.sso_status, 'Loading SSO login page\u2026', 'info')
            # Connect loadFinished AFTER setUrl to skip the about:blank signal
            self._sso_webview.setUrl(QUrl(sso_url))
            self._sso_page.loadFinished.connect(self._on_sso_load_finished)
            self._sso_page.titleChanged.connect(self._on_sso_title_changed)

        except ImportError:
            set_status_text(
                self.sso_status,
                'PySide6-WebEngine is not installed. Cannot open embedded browser.',
                'error',
            )
            logging.warning('PySide6-WebEngine not available for SSO')
        finally:
            self.sso_open_btn.setEnabled(True)
            self.sso_open_btn.setText('Open SSO Login in Browser')
            self.unsetCursor()

    def _on_sso_title_changed(self, title: str) -> None:
        """Check page title for SSO token data."""
        if title and 'token=' in title:
            logging.info('SSO token captured via titleChanged: %s...', title[:80])
            self._on_sso_token_received(title)

    def _on_js_location_result(self, href) -> None:
        """Handle JavaScript location.href result for SSO token extraction."""
        if self._sso_token_received or not href:
            return
        href = str(href)
        if 'token=' in href:
            logging.info('SSO token captured via runJavaScript: %s...', href[:80])
            self._on_sso_token_received(href)

    def _on_sso_token_received(self, callback_url: str) -> None:
        """Process a received SSO callback URL."""
        if self._sso_token_received:
            return
        if not callback_url or 'token=' not in callback_url:
            logging.warning(
                'SSO token signal received but no token= in URL: %r', callback_url[:120] if callback_url else ''
            )
            return
        self._sso_token_received = True
        set_status_text(self.sso_status, 'Token received, verifying\u2026', 'info')
        self._sso_worker = SSOTokenWorker(self.config, self.opts, self._sso_moodle_url, callback_url)
        self._sso_worker.login_successful.connect(self._on_sso_login_success)
        self._sso_worker.login_failed.connect(self._on_sso_login_failed)
        self._sso_worker.start()

    def cleanup(self) -> None:
        """Public cleanup method — call before the application exits."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        if self._sso_worker is not None and self._sso_worker.isRunning():
            self._sso_worker.quit()
            self._sso_worker.wait(2000)
        self._cleanup_sso_webview()

    def _cleanup_sso_webview(self) -> None:
        """Remove and clean up the SSO web view, page, handler, and profile.

        Destruction order matters: the page must be deleted before the profile,
        otherwise Qt emits "Release of profile requested but WebEnginePage
        still not deleted."
        """
        from PySide6.QtWidgets import QApplication

        if self._sso_page is not None:
            try:
                self._sso_page.loadFinished.disconnect()
                self._sso_page.titleChanged.disconnect()
                self._sso_page.token_received.disconnect()
            except RuntimeError:
                pass

        if self._sso_scheme_handler is not None:
            try:
                self._sso_scheme_handler.token_received.disconnect()
            except RuntimeError:
                pass

        if self._sso_webview is not None:
            self._sso_webview_container.removeWidget(self._sso_webview)
            self._sso_webview.setPage(None)
            self._sso_webview.deleteLater()
            self._sso_webview = None

        if self._sso_page is not None:
            self._sso_page.deleteLater()
            self._sso_page = None

        if self._sso_scheme_handler is not None and self._sso_profile is not None:
            self._sso_profile.removeUrlSchemeHandler(self._sso_scheme_handler)

        if self._sso_scheme_handler is not None:
            self._sso_scheme_handler.deleteLater()
            self._sso_scheme_handler = None

        if self._sso_profile is not None:
            self._sso_profile.deleteLater()
            self._sso_profile = None

        QApplication.processEvents()

    def _on_sso_login_success(self) -> None:
        """Handle successful SSO login."""
        set_status_text(self.sso_status, 'SSO login successful!', 'success')
        self._cleanup_sso_webview()
        self.login_successful.emit()

    def _on_sso_login_failed(self, error_msg: str) -> None:
        """Handle failed SSO login."""
        set_status_text(self.sso_status, f'SSO login failed: {error_msg}', 'error')
        self._cleanup_sso_webview()
        self.login_failed.emit(error_msg)
