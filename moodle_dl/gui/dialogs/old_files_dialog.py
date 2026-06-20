import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.style_utils import set_status_text
from moodle_dl.gui.workers import FetchOldFilesWorker


class OldFilesDialog(QDialog):
    """Dialog to browse and delete old (superseded) file copies still on disk."""

    def __init__(self, config: ConfigHelper, opts, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.opts = opts
        self._worker = None

        self.setWindowTitle(self.tr('Outdated Copies'))
        self.setMinimumSize(700, 500)

        self._setup_ui()
        self._load_files()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        hint = QLabel(
            self.tr(
                'These are older versions of files that have been replaced by newer ones but are still on disk. '
                'Select entries to delete them and free up disk space.'
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.status_label = QLabel('')
        layout.addWidget(self.status_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([self.tr('Name'), self.tr('Section'), self.tr('Path')])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree, 1)

        btn_row = QHBoxLayout()

        self.refresh_btn = QPushButton(self.tr('Refresh'))
        self.refresh_btn.clicked.connect(self._load_files)
        btn_row.addWidget(self.refresh_btn)

        self.delete_btn = QPushButton(self.tr('Delete Selected'))
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete_selected)
        btn_row.addWidget(self.delete_btn)

        btn_row.addStretch()

        close_btn = QPushButton(self.tr('Close'))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

        self.tree.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_files(self) -> None:
        """Fetch old files from the database."""
        self.tree.clear()
        self.delete_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.status_label, self.tr('Loading old files\u2026'), 'info')

        self._worker = FetchOldFilesWorker(self.config, self.opts)
        self._worker.files_fetched.connect(self._on_files_fetched)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_files_fetched(self, courses: list) -> None:
        self.refresh_btn.setEnabled(True)
        self.unsetCursor()
        self.tree.clear()

        total = 0
        for course in courses:
            course_item = QTreeWidgetItem([course.fullname, '', ''])
            course_item.setFlags(course_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            for f in course.files:
                file_item = QTreeWidgetItem(
                    [
                        f.content_filename,
                        f.section_name or '',
                        f.saved_to or '',
                    ]
                )
                file_item.setData(0, Qt.ItemDataRole.UserRole, f)
                course_item.addChild(file_item)
                total += 1
            self.tree.addTopLevelItem(course_item)
            course_item.setExpanded(True)

        if total == 0:
            set_status_text(self.status_label, self.tr('No old file copies found.'), 'success')
        else:
            set_status_text(self.status_label, self.tr('{} old file(s) found.').format(total), 'info')

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)

    def _on_error(self, error_msg: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.unsetCursor()
        set_status_text(self.status_label, self.tr('Error: {}').format(error_msg), 'error')

    def _on_selection_changed(self) -> None:
        selected = [item for item in self.tree.selectedItems() if item.data(0, Qt.ItemDataRole.UserRole) is not None]
        self.delete_btn.setEnabled(len(selected) > 0)

    def _on_delete_selected(self) -> None:
        """Delete selected old files from disk and database."""
        selected = [item for item in self.tree.selectedItems() if item.data(0, Qt.ItemDataRole.UserRole) is not None]
        if not selected:
            return

        reply = QMessageBox.question(
            self,
            self.tr('Delete Old Files'),
            self.tr('Delete {} old file(s) from disk and database?\nThis action cannot be undone.').format(
                len(selected)
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from moodle_dl.database import StateRecorder

        files = [item.data(0, Qt.ItemDataRole.UserRole) for item in selected]

        # Delete files from disk
        deleted_count = 0
        for f in files:
            if f.saved_to and os.path.exists(f.saved_to):
                try:
                    os.remove(f.saved_to)
                    deleted_count += 1
                except OSError as e:
                    logging.warning('Failed to delete %s: %s', f.saved_to, e)

        # Delete entries from database
        database = StateRecorder(self.config, self.opts)
        database.batch_delete_files_from_db(files)
        set_status_text(
            self.status_label,
            self.tr('Deleted {} file(s) from disk and {} DB entry(ies). Refreshing\u2026').format(
                deleted_count, len(files)
            ),
            'success',
        )
        self._load_files()
