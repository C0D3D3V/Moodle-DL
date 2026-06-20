import logging

from PySide6.QtCore import QModelIndex, Qt, QTimer
from PySide6.QtGui import QAction, QCursor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.pages.download_models import (
    Phase,
    PreviewTableModel,
    SelectCheckBoxDelegate,
    SkipButtonDelegate,
    TaskTableModel,
)
from moodle_dl.gui.style_utils import set_status_text
from moodle_dl.gui.workers import DownloadWorker, FetchWorker, NotifyWorker
from moodle_dl.types import TaskState
from moodle_dl.utils import format_bytes


class DownloadPage(QWidget):
    def __init__(self, config: ConfigHelper, opts) -> None:
        super().__init__()
        self.config = config
        self.opts = opts
        self._phase = Phase.IDLE
        self._fetch_worker = None
        self._download_worker = None
        self._notify_worker = None
        self._download_service = None
        self._fetched_courses = None
        self._fetched_database = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_status)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Controls
        controls = QHBoxLayout()
        self.scan_btn = QPushButton('Scan Moodle')
        self.scan_btn.clicked.connect(self._on_scan)
        controls.addWidget(self.scan_btn)

        self.start_btn = QPushButton('Start Download')
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start_download)
        controls.addWidget(self.start_btn)

        self.cancel_btn = QPushButton('Cancel All')
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_all)
        controls.addWidget(self.cancel_btn)

        self.skip_selected_btn = QPushButton('Skip Selected')
        self.skip_selected_btn.setEnabled(False)
        self.skip_selected_btn.clicked.connect(self._on_skip_selected)
        controls.addWidget(self.skip_selected_btn)

        self.always_skip_selected_btn = QPushButton('Always Skip Selected')
        self.always_skip_selected_btn.setEnabled(False)
        self.always_skip_selected_btn.clicked.connect(self._on_always_skip_selected)
        controls.addWidget(self.always_skip_selected_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # Overall progress
        self.progress_group = QGroupBox('Overall Progress')
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.stats_label = QLabel('Ready. Navigate here to scan for changes.')
        progress_layout.addWidget(self.stats_label)

        self.progress_group.setLayout(progress_layout)
        layout.addWidget(self.progress_group)

        # Shared table view
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Models
        self._preview_model = PreviewTableModel()
        self._task_model = TaskTableModel()

        # Start with preview model
        self.table_view.setModel(self._preview_model)

        layout.addWidget(self.table_view)

        # Context menu on table
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_table_context_menu)

        # Enable/disable skip buttons when selection changes
        self._preview_model.dataChanged.connect(self._update_skip_buttons_enabled)
        self._preview_model.modelReset.connect(self._update_skip_buttons_enabled)

        # Delegates (created once, re-applied as needed)
        self._skip_delegate = SkipButtonDelegate(self.table_view)
        self._skip_delegate.clicked.connect(self._on_skip_clicked)

        self._select_delegate = SelectCheckBoxDelegate(self.table_view)
        self._select_delegate.toggled.connect(lambda idx, checked: self._update_skip_buttons_enabled())

    # -------------------------------------------------------------------
    # Phase management
    # -------------------------------------------------------------------

    def invalidate(self) -> None:
        """Mark cached results as stale so the next on_show() triggers a rescan."""
        if self._phase == Phase.PREVIEW:
            self._reset_to_idle()

    def on_show(self) -> None:
        """Called when this page becomes visible."""
        if self._phase == Phase.IDLE:
            self._on_scan()

    def _on_scan(self) -> None:
        """Start scanning Moodle for changes."""
        self._phase = Phase.SCANNING
        self.scan_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.skip_selected_btn.setEnabled(False)
        self.always_skip_selected_btn.setEnabled(False)
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.stats_label, 'Scanning Moodle for changes\u2026', 'info')
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)  # indeterminate

        # Switch to empty preview model during scan
        self.table_view.setModel(self._preview_model)
        self._preview_model.set_data([], [])
        self._apply_preview_delegates()

        # Reload config in case it changed
        try:
            self.config.load()
        except ConfigHelper.NoConfigError:
            QMessageBox.critical(self, 'Error', 'No configuration found. Please log in first.')
            self._reset_to_idle()
            return

        self._fetch_worker = FetchWorker(self.config, self.opts)
        self._fetch_worker.fetch_finished.connect(self._on_fetch_finished)
        self._fetch_worker.error_occurred.connect(self._on_fetch_error)
        self._fetch_worker.start()

    def _on_fetch_finished(self, courses, database) -> None:
        """Scan complete — populate preview table."""
        self._fetched_courses = courses
        self._fetched_database = database
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.unsetCursor()

        # Load always-skip keys from config
        always_skip_keys = set(self.config.get_property_or('always_skip_files', []))

        self._preview_model.set_data(courses, always_skip_keys)
        self.table_view.setModel(self._preview_model)
        self._apply_preview_delegates()

        total_files = self._preview_model.rowCount()
        if total_files == 0:
            set_status_text(self.stats_label, 'No new or changed files found.', 'success')
            self._phase = Phase.PREVIEW
            self.scan_btn.setEnabled(True)
            self.start_btn.setEnabled(False)
        else:
            set_status_text(
                self.stats_label,
                f'Found {total_files} file(s) to download. Review and click Start Download.',
                'info',
            )
            self._phase = Phase.PREVIEW
            self.scan_btn.setEnabled(True)
            self.start_btn.setEnabled(True)

    def _on_fetch_error(self, error_msg) -> None:
        """Scan failed."""
        self.progress_bar.setRange(0, 100)
        QMessageBox.critical(self, 'Scan Error', error_msg)
        set_status_text(self.stats_label, f'Error: {error_msg}', 'error')
        self._reset_to_idle()

    def _on_start_download(self) -> None:
        """User clicked Start Download — begin downloading remaining files."""
        remaining_courses = self._preview_model.get_remaining_courses()
        if not remaining_courses or all(len(c.files) == 0 for c in remaining_courses):
            QMessageBox.information(self, 'Nothing to Download', 'All files have been skipped.')
            return

        self._phase = Phase.DOWNLOADING
        self.scan_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.start_btn.setText('Downloading\u2026')
        self.cancel_btn.setEnabled(True)
        self.skip_selected_btn.setEnabled(False)
        self.always_skip_selected_btn.setEnabled(False)
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.stats_label, 'Starting download\u2026', 'info')

        # Switch to task model
        self.table_view.setModel(self._task_model)
        self._apply_download_delegates()

        self._download_worker = DownloadWorker(self.config, self.opts, remaining_courses, self._fetched_database)
        self._download_worker.download_started.connect(self._on_download_started)
        self._download_worker.download_finished.connect(self._on_download_finished)
        self._download_worker.error_occurred.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_started(self, download_service) -> None:
        self._download_service = download_service
        self._task_model.set_tasks(download_service.all_tasks)

        total = download_service.status.files_to_download
        set_status_text(self.stats_label, f'Downloading {total} files\u2026', 'info')
        self._poll_timer.start()

    def _on_download_finished(self, failed: list) -> None:
        self._poll_timer.stop()
        self._poll_status()  # Final update

        if self._download_service:
            status = self._download_service.status
            msg = f'Download complete. {status.files_downloaded} succeeded, {status.files_failed} failed.'
            level = 'success' if status.files_failed == 0 else 'warning'
            set_status_text(self.stats_label, msg, level)
            self.progress_bar.setValue(100)

        if failed:
            details = '\n'.join(failed[:20])
            if len(failed) > 20:
                details += f'\n... and {len(failed) - 20} more'
            QMessageBox.warning(
                self, 'Some Downloads Failed', f'{len(failed)} file(s) failed to download:\n\n{details}'
            )

        self._download_service = None

        # Trigger post-download notifications
        database = self._fetched_database
        if database is not None:
            self._notify_worker = NotifyWorker(self.config, database)
            self._notify_worker.notify_finished.connect(self._on_notify_done)
            self._notify_worker.error_occurred.connect(self._on_notify_done)
            self._notify_worker.start()
        else:
            self._reset_to_idle()

    def _on_notify_done(self, *_args) -> None:
        """Called after post-download notifications complete (or fail)."""
        self._reset_to_idle()

    def _on_download_error(self, error_msg: str) -> None:
        self._poll_timer.stop()
        set_status_text(self.stats_label, f'Error: {error_msg}', 'error')
        QMessageBox.critical(self, 'Download Error', error_msg)
        self._download_service = None
        self._reset_to_idle()

    def _poll_status(self) -> None:
        """Update UI from download status."""
        if self._download_service is None:
            return

        status = self._download_service.status

        if status.bytes_to_download > 0:
            pct = int(status.bytes_downloaded * 100 / status.bytes_to_download)
            pct = max(0, min(100, pct))
            self.progress_bar.setValue(pct)

        done = status.files_downloaded + status.files_failed
        self.stats_label.setText(
            f'{format_bytes(status.bytes_downloaded)} / {format_bytes(status.bytes_to_download)} | '
            f'Done: {done} / {status.files_to_download} | '
            f'Failed: {status.files_failed}'
        )

        self._task_model.refresh()

    # -------------------------------------------------------------------
    # Skip / Always-skip handlers
    # -------------------------------------------------------------------

    def _on_skip_clicked(self, index: QModelIndex) -> None:
        """Handle click on a Skip button delegate (download phase only)."""
        if self._phase == Phase.DOWNLOADING:
            task = self._task_model.get_task(index.row())
            if task and task.status.state == TaskState.STARTED and not task.status.skip_requested:
                task.status.skip_requested = True
                logging.info('Skip requested for task %d: %s', task.task_id, task.file.content_filename)
                self._task_model.refresh()

    def _skip_entries(self, rows) -> None:
        """Remove given rows from preview (one-time skip)."""
        self._preview_model.remove_rows(rows)
        self._update_preview_status()

    def _always_skip_entries(self, rows) -> None:
        """Mark rows as always-skipped (greyed-out + strikethrough), persist to config."""
        rows = {r for r in rows if not self._preview_model.is_always_skipped(r)}
        if not rows:
            return
        always_skip = set(self.config.get_property_or('always_skip_files', []))
        for row in rows:
            entry = self._preview_model.get_entry(row)
            if entry:
                always_skip.add(PreviewTableModel.file_key(entry[0], entry[1]))
        self.config.set_property('always_skip_files', sorted(always_skip))
        self._preview_model.mark_always_skipped(rows)
        self._update_preview_status()

    def _remove_always_skip_entries(self, rows) -> None:
        """Restore rows from always-skipped state, update config."""
        rows = {r for r in rows if self._preview_model.is_always_skipped(r)}
        if not rows:
            return
        always_skip = set(self.config.get_property_or('always_skip_files', []))
        for row in rows:
            entry = self._preview_model.get_entry(row)
            if entry:
                always_skip.discard(PreviewTableModel.file_key(entry[0], entry[1]))
        self.config.set_property('always_skip_files', sorted(always_skip))
        self._preview_model.unmark_always_skipped(rows)
        self._update_preview_status()

    def _on_skip_selected(self) -> None:
        self._skip_entries(self._preview_model.selected_rows())

    def _on_always_skip_selected(self) -> None:
        self._always_skip_entries(self._preview_model.selected_rows())

    def _on_table_context_menu(self, pos) -> None:
        if self._phase != Phase.PREVIEW:
            return
        selected = self._preview_model.selected_rows()
        index = self.table_view.indexAt(pos)
        if not selected and index.isValid():
            selected = {index.row()}
        if not selected:
            return

        any_always = any(self._preview_model.is_always_skipped(r) for r in selected)
        any_normal = any(not self._preview_model.is_always_skipped(r) for r in selected)
        menu = QMenu(self.table_view)

        if any_normal:
            normal_rows = {r for r in selected if not self._preview_model.is_always_skipped(r)}
            n = len(normal_rows)
            skip_action = QAction(f'Skip ({n})' if n > 1 else 'Skip', menu)
            skip_action.triggered.connect(lambda checked=False, rows=normal_rows: self._skip_entries(rows))
            menu.addAction(skip_action)

            always_action = QAction(f'Always Skip ({n})' if n > 1 else 'Always Skip', menu)
            always_action.triggered.connect(lambda checked=False, rows=normal_rows: self._always_skip_entries(rows))
            menu.addAction(always_action)

        if any_always:
            skipped_rows = {r for r in selected if self._preview_model.is_always_skipped(r)}
            n = len(skipped_rows)
            restore_action = QAction(f'Remove Always Skip ({n})' if n > 1 else 'Remove Always Skip', menu)
            restore_action.triggered.connect(
                lambda checked=False, rows=skipped_rows: self._remove_always_skip_entries(rows)
            )
            menu.addAction(restore_action)

        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def _update_skip_buttons_enabled(self) -> None:
        has_sel = self._phase == Phase.PREVIEW and self._preview_model.has_selection()
        self.skip_selected_btn.setEnabled(has_sel)
        self.always_skip_selected_btn.setEnabled(has_sel)

    def _update_preview_status(self) -> None:
        """Update status label and start button after skip operations."""
        remaining = self._preview_model.get_remaining_courses()
        total_files = sum(len(c.files) for c in remaining) if remaining else 0
        if total_files == 0:
            self.start_btn.setEnabled(False)
            set_status_text(self.stats_label, 'All files skipped. Click Scan to re-check.', 'info')
        else:
            self.start_btn.setEnabled(True)
            set_status_text(
                self.stats_label,
                f'{total_files} file(s) remaining. Review and click Start Download.',
                'info',
            )

    # -------------------------------------------------------------------
    # Cancel
    # -------------------------------------------------------------------

    def _on_cancel_all(self) -> None:
        """Cancel all downloads after user confirmation."""
        reply = QMessageBox.question(
            self,
            'Cancel All Downloads',
            'Are you sure you want to cancel all running downloads?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._download_worker is not None:
            self._download_worker.request_cancel()
            self.cancel_btn.setEnabled(False)
            set_status_text(self.stats_label, 'Cancelling\u2026', 'warning')

    def cancel_all(self) -> None:
        """Called when the window is closing."""
        if self._fetch_worker is not None and self._fetch_worker.isRunning():
            self._fetch_worker.quit()
            self._fetch_worker.wait(3000)
        if self._download_worker is not None and self._download_worker.isRunning():
            self._download_worker.request_cancel()
            self._download_worker.quit()
            self._download_worker.wait(3000)
        if self._notify_worker is not None and self._notify_worker.isRunning():
            self._notify_worker.quit()
            self._notify_worker.wait(3000)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _apply_preview_delegates(self) -> None:
        """Set delegates for preview mode columns."""
        self.table_view.setItemDelegateForColumn(PreviewTableModel.COL_SELECT, self._select_delegate)
        self.table_view.setItemDelegateForColumn(TaskTableModel.COL_SKIP, None)

    def _apply_download_delegates(self) -> None:
        """Set delegates for download mode columns."""
        self.table_view.setItemDelegateForColumn(TaskTableModel.COL_SKIP, self._skip_delegate)
        self.table_view.setItemDelegateForColumn(PreviewTableModel.COL_SELECT, None)

    def _reset_to_idle(self) -> None:
        """Reset all UI state to idle."""
        self._phase = Phase.IDLE
        self.scan_btn.setEnabled(True)
        self.start_btn.setEnabled(False)
        self.start_btn.setText('Start Download')
        self.cancel_btn.setEnabled(False)
        self.skip_selected_btn.setEnabled(False)
        self.always_skip_selected_btn.setEnabled(False)
        self.unsetCursor()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self._fetched_courses = None
        self._fetched_database = None

        # Switch back to preview model
        self.table_view.setModel(self._preview_model)
        self._apply_preview_delegates()
