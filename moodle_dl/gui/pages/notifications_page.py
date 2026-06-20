from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.style_utils import set_status_text
from moodle_dl.gui.workers import (
    TestDiscordWorker,
    TestMailWorker,
    TestNtfyWorker,
    TestTelegramWorker,
    TestXmppWorker,
)


class NotificationsPage(QWidget):
    def __init__(self, config: ConfigHelper, opts) -> None:
        super().__init__()
        self.config = config
        self.opts = opts
        self._telegram_worker = None
        self._discord_worker = None
        self._mail_worker = None
        self._ntfy_worker = None
        self._xmpp_worker = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Telegram Tab ---
        telegram_tab = QWidget()
        tg_layout = QVBoxLayout(telegram_tab)

        tg_group = QGroupBox('Telegram Configuration')
        tg_form = QFormLayout()

        self.tg_token_input = QLineEdit()
        self.tg_token_input.setPlaceholderText('123456:ABC-DEF...')
        self.tg_token_input.setToolTip('Bot token from @BotFather.')
        tg_form.addRow('Bot Token:', self.tg_token_input)

        self.tg_chat_id_input = QLineEdit()
        self.tg_chat_id_input.setPlaceholderText('e.g. 123456789')
        self.tg_chat_id_input.setToolTip('Your Telegram chat ID. Send /start to @userinfobot to find it.')
        tg_form.addRow('Chat ID:', self.tg_chat_id_input)

        self.tg_send_errors = QCheckBox('Send Error Reports')
        self.tg_send_errors.setToolTip('Also send error notifications via Telegram.')
        tg_form.addRow(self.tg_send_errors)

        tg_group.setLayout(tg_form)
        tg_layout.addWidget(tg_group)

        tg_btn_row = QHBoxLayout()
        self.tg_test_btn = QPushButton('Test')
        self.tg_test_btn.clicked.connect(self._on_test_telegram)
        tg_btn_row.addWidget(self.tg_test_btn)

        self.tg_save_btn = QPushButton('Save')
        self.tg_save_btn.clicked.connect(self._on_save_telegram)
        tg_btn_row.addWidget(self.tg_save_btn)

        self.tg_disable_btn = QPushButton('Disable')
        self.tg_disable_btn.clicked.connect(self._on_disable_telegram)
        tg_btn_row.addWidget(self.tg_disable_btn)

        tg_btn_row.addStretch()
        tg_layout.addLayout(tg_btn_row)

        self.tg_status = QLabel('')
        tg_layout.addWidget(self.tg_status)
        tg_layout.addStretch()

        self.tabs.addTab(telegram_tab, 'Telegram')

        # --- Discord Tab ---
        discord_tab = QWidget()
        dc_layout = QVBoxLayout(discord_tab)

        dc_group = QGroupBox('Discord Configuration')
        dc_form_layout = QVBoxLayout()

        dc_label = QLabel('Webhook URLs (one per line):')
        dc_form_layout.addWidget(dc_label)

        self.dc_webhooks_input = QTextEdit()
        self.dc_webhooks_input.setPlaceholderText('https://discord.com/api/webhooks/...')
        self.dc_webhooks_input.setToolTip('Enter one Discord webhook URL per line.')
        self.dc_webhooks_input.setMaximumHeight(120)
        dc_form_layout.addWidget(self.dc_webhooks_input)

        dc_group.setLayout(dc_form_layout)
        dc_layout.addWidget(dc_group)

        dc_btn_row = QHBoxLayout()
        self.dc_test_btn = QPushButton('Test')
        self.dc_test_btn.clicked.connect(self._on_test_discord)
        dc_btn_row.addWidget(self.dc_test_btn)

        self.dc_save_btn = QPushButton('Save')
        self.dc_save_btn.clicked.connect(self._on_save_discord)
        dc_btn_row.addWidget(self.dc_save_btn)

        self.dc_disable_btn = QPushButton('Disable')
        self.dc_disable_btn.clicked.connect(self._on_disable_discord)
        dc_btn_row.addWidget(self.dc_disable_btn)

        dc_btn_row.addStretch()
        dc_layout.addLayout(dc_btn_row)

        self.dc_status = QLabel('')
        dc_layout.addWidget(self.dc_status)
        dc_layout.addStretch()

        self.tabs.addTab(discord_tab, 'Discord')

        # --- Email (SMTP) Tab ---
        mail_tab = QWidget()
        mail_layout = QVBoxLayout(mail_tab)

        mail_group = QGroupBox('Email (SMTP) Configuration')
        mail_form = QFormLayout()

        self.mail_sender_input = QLineEdit()
        self.mail_sender_input.setPlaceholderText('noreply@example.com')
        self.mail_sender_input.setToolTip('Email address to send from.')
        mail_form.addRow('Sender:', self.mail_sender_input)

        self.mail_host_input = QLineEdit()
        self.mail_host_input.setPlaceholderText('smtp.gmail.com')
        self.mail_host_input.setToolTip('SMTP server hostname.')
        mail_form.addRow('SMTP Host:', self.mail_host_input)

        self.mail_port_spin = QSpinBox()
        self.mail_port_spin.setRange(1, 65535)
        self.mail_port_spin.setValue(587)
        self.mail_port_spin.setToolTip('SMTP server port (typically 587 for STARTTLS).')
        mail_form.addRow('SMTP Port:', self.mail_port_spin)

        self.mail_username_input = QLineEdit()
        self.mail_username_input.setPlaceholderText('user@example.com')
        self.mail_username_input.setToolTip('SMTP authentication username.')
        mail_form.addRow('Username:', self.mail_username_input)

        self.mail_password_input = QLineEdit()
        self.mail_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mail_password_input.setToolTip('SMTP authentication password.')
        mail_form.addRow('Password:', self.mail_password_input)

        self.mail_target_input = QLineEdit()
        self.mail_target_input.setPlaceholderText('recipient@example.com')
        self.mail_target_input.setToolTip('Recipient email address.')
        mail_form.addRow('Target:', self.mail_target_input)

        self.mail_send_errors = QCheckBox('Send Error Reports')
        self.mail_send_errors.setToolTip('Also send error notifications via email.')
        mail_form.addRow(self.mail_send_errors)

        mail_group.setLayout(mail_form)
        mail_layout.addWidget(mail_group)

        mail_btn_row = QHBoxLayout()
        self.mail_test_btn = QPushButton('Test')
        self.mail_test_btn.clicked.connect(self._on_test_mail)
        mail_btn_row.addWidget(self.mail_test_btn)

        self.mail_save_btn = QPushButton('Save')
        self.mail_save_btn.clicked.connect(self._on_save_mail)
        mail_btn_row.addWidget(self.mail_save_btn)

        self.mail_disable_btn = QPushButton('Disable')
        self.mail_disable_btn.clicked.connect(self._on_disable_mail)
        mail_btn_row.addWidget(self.mail_disable_btn)

        mail_btn_row.addStretch()
        mail_layout.addLayout(mail_btn_row)

        self.mail_status = QLabel('')
        mail_layout.addWidget(self.mail_status)
        mail_layout.addStretch()

        self.tabs.addTab(mail_tab, 'Email')

        # --- ntfy Tab ---
        ntfy_tab = QWidget()
        ntfy_layout = QVBoxLayout(ntfy_tab)

        ntfy_group = QGroupBox('ntfy Configuration')
        ntfy_form = QFormLayout()

        self.ntfy_topic_input = QLineEdit()
        self.ntfy_topic_input.setPlaceholderText('moodle_updates')
        self.ntfy_topic_input.setToolTip('The ntfy topic to publish to.')
        ntfy_form.addRow('Topic:', self.ntfy_topic_input)

        self.ntfy_server_input = QLineEdit()
        self.ntfy_server_input.setPlaceholderText('https://ntfy.sh/')
        self.ntfy_server_input.setToolTip('Custom ntfy server URL. Leave empty to use the default (https://ntfy.sh/).')
        ntfy_form.addRow('Server URL:', self.ntfy_server_input)

        ntfy_group.setLayout(ntfy_form)
        ntfy_layout.addWidget(ntfy_group)

        ntfy_btn_row = QHBoxLayout()
        self.ntfy_test_btn = QPushButton('Test')
        self.ntfy_test_btn.clicked.connect(self._on_test_ntfy)
        ntfy_btn_row.addWidget(self.ntfy_test_btn)

        self.ntfy_save_btn = QPushButton('Save')
        self.ntfy_save_btn.clicked.connect(self._on_save_ntfy)
        ntfy_btn_row.addWidget(self.ntfy_save_btn)

        self.ntfy_disable_btn = QPushButton('Disable')
        self.ntfy_disable_btn.clicked.connect(self._on_disable_ntfy)
        ntfy_btn_row.addWidget(self.ntfy_disable_btn)

        ntfy_btn_row.addStretch()
        ntfy_layout.addLayout(ntfy_btn_row)

        self.ntfy_status = QLabel('')
        ntfy_layout.addWidget(self.ntfy_status)
        ntfy_layout.addStretch()

        self.tabs.addTab(ntfy_tab, 'ntfy')

        # --- XMPP Tab ---
        xmpp_tab = QWidget()
        xmpp_layout = QVBoxLayout(xmpp_tab)

        xmpp_group = QGroupBox('XMPP Configuration')
        xmpp_form = QFormLayout()

        self.xmpp_jid_input = QLineEdit()
        self.xmpp_jid_input.setPlaceholderText('bot@jabber.org')
        self.xmpp_jid_input.setToolTip('Sender JID (Jabber ID).')
        xmpp_form.addRow('Sender JID:', self.xmpp_jid_input)

        self.xmpp_password_input = QLineEdit()
        self.xmpp_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.xmpp_password_input.setToolTip('XMPP account password.')
        xmpp_form.addRow('Password:', self.xmpp_password_input)

        self.xmpp_target_input = QLineEdit()
        self.xmpp_target_input.setPlaceholderText('user@jabber.org')
        self.xmpp_target_input.setToolTip('Target JID to receive notifications.')
        xmpp_form.addRow('Target JID:', self.xmpp_target_input)

        self.xmpp_send_errors = QCheckBox('Send Error Reports')
        self.xmpp_send_errors.setToolTip('Also send error notifications via XMPP.')
        xmpp_form.addRow(self.xmpp_send_errors)

        xmpp_group.setLayout(xmpp_form)
        xmpp_layout.addWidget(xmpp_group)

        xmpp_btn_row = QHBoxLayout()
        self.xmpp_test_btn = QPushButton('Test')
        self.xmpp_test_btn.clicked.connect(self._on_test_xmpp)
        xmpp_btn_row.addWidget(self.xmpp_test_btn)

        self.xmpp_save_btn = QPushButton('Save')
        self.xmpp_save_btn.clicked.connect(self._on_save_xmpp)
        xmpp_btn_row.addWidget(self.xmpp_save_btn)

        self.xmpp_disable_btn = QPushButton('Disable')
        self.xmpp_disable_btn.clicked.connect(self._on_disable_xmpp)
        xmpp_btn_row.addWidget(self.xmpp_disable_btn)

        xmpp_btn_row.addStretch()
        xmpp_layout.addLayout(xmpp_btn_row)

        self.xmpp_status = QLabel('')
        xmpp_layout.addWidget(self.xmpp_status)
        xmpp_layout.addStretch()

        self.tabs.addTab(xmpp_tab, 'XMPP')

        layout.addStretch()

    def on_show(self) -> None:
        """Load current notification configuration."""
        # Telegram
        tg_token = self.config.get_property_or('telegram_token', '')
        tg_chat_id = self.config.get_property_or('telegram_chatid', '')
        tg_send_errors = self.config.get_property_or('telegram_send_error_reports', False)
        self.tg_token_input.setText(tg_token or '')
        self.tg_chat_id_input.setText(tg_chat_id or '')
        self.tg_send_errors.setChecked(bool(tg_send_errors))

        # Discord
        dc_webhooks = self.config.get_property_or('discord_webhook_urls', [])
        if isinstance(dc_webhooks, list):
            self.dc_webhooks_input.setPlainText('\n'.join(dc_webhooks))
        else:
            self.dc_webhooks_input.setPlainText('')

        # Email
        mail_cfg = self.config.get_property_or('mail', {})
        if isinstance(mail_cfg, dict):
            self.mail_sender_input.setText(mail_cfg.get('sender', ''))
            self.mail_host_input.setText(mail_cfg.get('server_host', ''))
            self.mail_port_spin.setValue(mail_cfg.get('server_port', 587))
            self.mail_username_input.setText(mail_cfg.get('username', ''))
            self.mail_password_input.setText(mail_cfg.get('password', ''))
            self.mail_target_input.setText(mail_cfg.get('target', ''))
            self.mail_send_errors.setChecked(mail_cfg.get('send_error_msg', False))

        # ntfy
        ntfy_cfg = self.config.get_property_or('ntfy', {})
        if isinstance(ntfy_cfg, dict):
            self.ntfy_topic_input.setText(ntfy_cfg.get('topic', ''))
            self.ntfy_server_input.setText(ntfy_cfg.get('server', ''))

        # XMPP
        xmpp_cfg = self.config.get_property_or('xmpp', {})
        if isinstance(xmpp_cfg, dict):
            self.xmpp_jid_input.setText(xmpp_cfg.get('sender', ''))
            self.xmpp_password_input.setText(xmpp_cfg.get('password', ''))
            self.xmpp_target_input.setText(xmpp_cfg.get('target', ''))
            self.xmpp_send_errors.setChecked(xmpp_cfg.get('send_error_msg', False))

    # --- Telegram ---

    def _on_test_telegram(self) -> None:
        """Send a test message via Telegram."""
        token = self.tg_token_input.text().strip()
        chat_id = self.tg_chat_id_input.text().strip()
        if not token or not chat_id:
            set_status_text(self.tg_status, 'Please enter both Bot Token and Chat ID.', 'error')
            return

        self.tg_test_btn.setEnabled(False)
        self.tg_test_btn.setText('Sending\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.tg_status, 'Sending test message\u2026', 'info')

        self._telegram_worker = TestTelegramWorker(token, chat_id)
        self._telegram_worker.test_successful.connect(self._on_telegram_test_success)
        self._telegram_worker.test_failed.connect(self._on_telegram_test_failed)
        self._telegram_worker.start()

    def _on_telegram_test_success(self) -> None:
        """Handle successful Telegram test."""
        self.tg_test_btn.setEnabled(True)
        self.tg_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.tg_status, 'Test message sent successfully!', 'success')

    def _on_telegram_test_failed(self, error_msg: str) -> None:
        """Handle failed Telegram test."""
        self.tg_test_btn.setEnabled(True)
        self.tg_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.tg_status, f'Test failed: {error_msg}', 'error')

    def _on_save_telegram(self) -> None:
        """Save Telegram configuration."""
        token = self.tg_token_input.text().strip()
        chat_id = self.tg_chat_id_input.text().strip()
        if not token or not chat_id:
            set_status_text(self.tg_status, 'Please enter both Bot Token and Chat ID.', 'error')
            return

        self.config.set_property('telegram_token', token)
        self.config.set_property('telegram_chatid', chat_id)
        self.config.set_property('telegram_send_error_reports', self.tg_send_errors.isChecked())
        set_status_text(self.tg_status, 'Telegram configuration saved.', 'success')

    def _on_disable_telegram(self) -> None:
        """Disable Telegram notifications."""
        self.config.set_property('telegram_token', '')
        self.config.set_property('telegram_chatid', '')
        self.config.set_property('telegram_send_error_reports', False)
        self.tg_token_input.clear()
        self.tg_chat_id_input.clear()
        self.tg_send_errors.setChecked(False)
        set_status_text(self.tg_status, 'Telegram notifications disabled.', 'info')

    # --- Discord ---

    def _get_discord_webhooks(self) -> list:
        """Parse webhook URLs from the text area."""
        text = self.dc_webhooks_input.toPlainText().strip()
        if not text:
            return []
        return [url.strip() for url in text.splitlines() if url.strip()]

    def _on_test_discord(self) -> None:
        """Send a test message via Discord."""
        webhooks = self._get_discord_webhooks()
        if not webhooks:
            set_status_text(self.dc_status, 'Please enter at least one webhook URL.', 'error')
            return

        self.dc_test_btn.setEnabled(False)
        self.dc_test_btn.setText('Sending\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.dc_status, 'Sending test message\u2026', 'info')

        self._discord_worker = TestDiscordWorker(webhooks)
        self._discord_worker.test_successful.connect(self._on_discord_test_success)
        self._discord_worker.test_failed.connect(self._on_discord_test_failed)
        self._discord_worker.start()

    def _on_discord_test_success(self) -> None:
        """Handle successful Discord test."""
        self.dc_test_btn.setEnabled(True)
        self.dc_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.dc_status, 'Test message sent successfully!', 'success')

    def _on_discord_test_failed(self, error_msg: str) -> None:
        """Handle failed Discord test."""
        self.dc_test_btn.setEnabled(True)
        self.dc_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.dc_status, f'Test failed: {error_msg}', 'error')

    def _on_save_discord(self) -> None:
        """Save Discord configuration."""
        webhooks = self._get_discord_webhooks()
        if not webhooks:
            set_status_text(self.dc_status, 'Please enter at least one webhook URL.', 'error')
            return

        self.config.set_property('discord_webhook_urls', webhooks)
        set_status_text(self.dc_status, 'Discord configuration saved.', 'success')

    def _on_disable_discord(self) -> None:
        """Disable Discord notifications."""
        self.config.set_property('discord_webhook_urls', [])
        self.dc_webhooks_input.clear()
        set_status_text(self.dc_status, 'Discord notifications disabled.', 'info')

    # --- Email (SMTP) ---

    def _on_test_mail(self) -> None:
        """Send a test email."""
        sender = self.mail_sender_input.text().strip()
        host = self.mail_host_input.text().strip()
        port = self.mail_port_spin.value()
        username = self.mail_username_input.text().strip()
        password = self.mail_password_input.text()
        target = self.mail_target_input.text().strip()

        if not all([sender, host, username, password, target]):
            set_status_text(self.mail_status, 'Please fill in all required fields.', 'error')
            return

        self.mail_test_btn.setEnabled(False)
        self.mail_test_btn.setText('Sending\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.mail_status, 'Sending test email\u2026', 'info')

        self._mail_worker = TestMailWorker(sender, host, port, username, password, target)
        self._mail_worker.test_successful.connect(self._on_mail_test_success)
        self._mail_worker.test_failed.connect(self._on_mail_test_failed)
        self._mail_worker.start()

    def _on_mail_test_success(self) -> None:
        self.mail_test_btn.setEnabled(True)
        self.mail_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.mail_status, 'Test email sent successfully!', 'success')

    def _on_mail_test_failed(self, error_msg: str) -> None:
        self.mail_test_btn.setEnabled(True)
        self.mail_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.mail_status, f'Test failed: {error_msg}', 'error')

    def _on_save_mail(self) -> None:
        """Save email configuration."""
        sender = self.mail_sender_input.text().strip()
        host = self.mail_host_input.text().strip()
        target = self.mail_target_input.text().strip()
        if not all([sender, host, target]):
            set_status_text(self.mail_status, 'Please fill in sender, host, and target.', 'error')
            return

        self.config.set_property(
            'mail',
            {
                'sender': sender,
                'server_host': host,
                'server_port': self.mail_port_spin.value(),
                'username': self.mail_username_input.text().strip(),
                'password': self.mail_password_input.text(),
                'target': target,
                'send_error_msg': self.mail_send_errors.isChecked(),
            },
        )
        set_status_text(self.mail_status, 'Email configuration saved.', 'success')

    def _on_disable_mail(self) -> None:
        """Disable email notifications."""
        self.config.set_property('mail', {})
        self.mail_sender_input.clear()
        self.mail_host_input.clear()
        self.mail_port_spin.setValue(587)
        self.mail_username_input.clear()
        self.mail_password_input.clear()
        self.mail_target_input.clear()
        self.mail_send_errors.setChecked(False)
        set_status_text(self.mail_status, 'Email notifications disabled.', 'info')

    # --- ntfy ---

    def _on_test_ntfy(self) -> None:
        """Send a test ntfy notification."""
        topic = self.ntfy_topic_input.text().strip()
        if not topic:
            set_status_text(self.ntfy_status, 'Please enter a topic.', 'error')
            return

        self.ntfy_test_btn.setEnabled(False)
        self.ntfy_test_btn.setText('Sending\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.ntfy_status, 'Sending test notification\u2026', 'info')

        server = self.ntfy_server_input.text().strip()
        self._ntfy_worker = TestNtfyWorker(topic, server)
        self._ntfy_worker.test_successful.connect(self._on_ntfy_test_success)
        self._ntfy_worker.test_failed.connect(self._on_ntfy_test_failed)
        self._ntfy_worker.start()

    def _on_ntfy_test_success(self) -> None:
        self.ntfy_test_btn.setEnabled(True)
        self.ntfy_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.ntfy_status, 'Test notification sent successfully!', 'success')

    def _on_ntfy_test_failed(self, error_msg: str) -> None:
        self.ntfy_test_btn.setEnabled(True)
        self.ntfy_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.ntfy_status, f'Test failed: {error_msg}', 'error')

    def _on_save_ntfy(self) -> None:
        """Save ntfy configuration."""
        topic = self.ntfy_topic_input.text().strip()
        if not topic:
            set_status_text(self.ntfy_status, 'Please enter a topic.', 'error')
            return

        self.config.set_property(
            'ntfy',
            {
                'topic': topic,
                'server': self.ntfy_server_input.text().strip(),
            },
        )
        set_status_text(self.ntfy_status, 'ntfy configuration saved.', 'success')

    def _on_disable_ntfy(self) -> None:
        """Disable ntfy notifications."""
        self.config.set_property('ntfy', {})
        self.ntfy_topic_input.clear()
        self.ntfy_server_input.clear()
        set_status_text(self.ntfy_status, 'ntfy notifications disabled.', 'info')

    # --- XMPP ---

    def _on_test_xmpp(self) -> None:
        """Send a test XMPP message."""
        jid = self.xmpp_jid_input.text().strip()
        password = self.xmpp_password_input.text()
        target = self.xmpp_target_input.text().strip()

        if not all([jid, password, target]):
            set_status_text(self.xmpp_status, 'Please fill in all required fields.', 'error')
            return

        self.xmpp_test_btn.setEnabled(False)
        self.xmpp_test_btn.setText('Sending\u2026')
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.xmpp_status, 'Sending test message\u2026', 'info')

        self._xmpp_worker = TestXmppWorker(jid, password, target)
        self._xmpp_worker.test_successful.connect(self._on_xmpp_test_success)
        self._xmpp_worker.test_failed.connect(self._on_xmpp_test_failed)
        self._xmpp_worker.start()

    def _on_xmpp_test_success(self) -> None:
        self.xmpp_test_btn.setEnabled(True)
        self.xmpp_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.xmpp_status, 'Test message sent successfully!', 'success')

    def _on_xmpp_test_failed(self, error_msg: str) -> None:
        self.xmpp_test_btn.setEnabled(True)
        self.xmpp_test_btn.setText('Test')
        self.unsetCursor()
        set_status_text(self.xmpp_status, f'Test failed: {error_msg}', 'error')

    def _on_save_xmpp(self) -> None:
        """Save XMPP configuration."""
        jid = self.xmpp_jid_input.text().strip()
        target = self.xmpp_target_input.text().strip()
        if not all([jid, target]):
            set_status_text(self.xmpp_status, 'Please fill in sender JID and target JID.', 'error')
            return

        self.config.set_property(
            'xmpp',
            {
                'sender': jid,
                'password': self.xmpp_password_input.text(),
                'target': target,
                'send_error_msg': self.xmpp_send_errors.isChecked(),
            },
        )
        set_status_text(self.xmpp_status, 'XMPP configuration saved.', 'success')

    def _on_disable_xmpp(self) -> None:
        """Disable XMPP notifications."""
        self.config.set_property('xmpp', {})
        self.xmpp_jid_input.clear()
        self.xmpp_password_input.clear()
        self.xmpp_target_input.clear()
        self.xmpp_send_errors.setChecked(False)
        set_status_text(self.xmpp_status, 'XMPP notifications disabled.', 'info')
