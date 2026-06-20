from enum import Enum, auto

from PySide6.QtCore import (
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
)

from moodle_dl.types import Course, TaskState
from moodle_dl.utils import format_bytes


class Phase(Enum):
    IDLE = auto()
    SCANNING = auto()
    PREVIEW = auto()
    DOWNLOADING = auto()


# ---------------------------------------------------------------------------
# Delegates
# ---------------------------------------------------------------------------


class SkipButtonDelegate(QStyledItemDelegate):
    """Draws a 'Skip' push-button in cells where the model returns True for UserRole."""

    clicked = Signal(QModelIndex)

    def paint(self, painter, option, index):
        skippable = index.data(Qt.ItemDataRole.UserRole)
        if not skippable:
            return  # draw nothing for non-skippable rows

        opt = QStyleOptionButton()
        opt.rect = option.rect.adjusted(4, 2, -4, -2)
        opt.text = self.tr('Skip')
        opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Active
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_PushButton, opt, painter, option.widget)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            skippable = index.data(Qt.ItemDataRole.UserRole)
            if skippable and option.rect.adjusted(4, 2, -4, -2).contains(event.position().toPoint()):
                self.clicked.emit(index)
                return True
        return False

    def sizeHint(self, option, index):
        return QSize(60, 28)


class SelectCheckBoxDelegate(QStyledItemDelegate):
    """Draws a clickable checkbox for the selection column."""

    toggled = Signal(QModelIndex, bool)

    def paint(self, painter, option, index):
        state = index.data(Qt.ItemDataRole.CheckStateRole)
        if state is None:
            return  # no checkbox for always-skipped rows

        opt = QStyleOptionButton()
        opt.rect = self._checkbox_rect(option)
        opt.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Active
        if state == Qt.CheckState.Checked:
            opt.state |= QStyle.StateFlag.State_On
        else:
            opt.state |= QStyle.StateFlag.State_Off
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_CheckBox, opt, painter, option.widget)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            current = index.data(Qt.ItemDataRole.CheckStateRole)
            if current is not None and self._checkbox_rect(option).contains(event.position().toPoint()):
                new_state = Qt.CheckState.Unchecked if current == Qt.CheckState.Checked else Qt.CheckState.Checked
                model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
                self.toggled.emit(index, new_state == Qt.CheckState.Checked)
                return True
        return False

    def sizeHint(self, option, index):
        return QSize(32, 28)

    @staticmethod
    def _checkbox_rect(option):
        rect = option.rect
        size = 20
        x = rect.x() + (rect.width() - size) // 2
        y = rect.y() + (rect.height() - size) // 2
        return QRect(x, y, size, size)


# ---------------------------------------------------------------------------
# Preview table model
# ---------------------------------------------------------------------------


class PreviewTableModel(QAbstractTableModel):
    """Table model for displaying files pending download in preview."""

    COL_SELECT = 0
    COL_ID = 1
    COL_FILENAME = 2
    COL_COURSE = 3
    COL_SIZE = 4
    COL_STATUS = 5

    COLUMNS = ['', '#', 'Filename', 'Course', 'Size', 'Status']

    def __init__(self) -> None:
        super().__init__()
        # User-facing header labels are translated here so they re-translate via self.tr.
        self._headers = ['', '#', self.tr('Filename'), self.tr('Course'), self.tr('Size'), self.tr('Status')]
        self._entries = []  # list of (course, file, row_index)
        self._always_skip = set()
        self._selected = set()  # row indices currently checked
        self._always_skipped_rows = set()  # row indices of always-skipped entries

    @staticmethod
    def file_key(course, file) -> str:
        """Stable identity key for a file across sessions."""
        return f'{course.id}::{file.module_id}::{file.content_filepath}::{file.content_filename}'

    def set_data(self, courses, always_skip_keys) -> None:
        """Populate the model from courses. Filters out deleted files."""
        self.beginResetModel()
        self._always_skip = set(always_skip_keys)
        self._entries = []
        self._selected.clear()
        self._always_skipped_rows.clear()
        idx = 0
        for course in courses:
            for f in course.files:
                if not f.deleted:
                    row = len(self._entries)
                    self._entries.append((course, f, idx))
                    if self.file_key(course, f) in self._always_skip:
                        self._always_skipped_rows.add(row)
                    idx += 1
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._entries)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._entries):
            return None

        row = index.row()
        course, file, row_idx = self._entries[row]
        col = index.column()
        is_skipped = row in self._always_skipped_rows

        if role == Qt.ItemDataRole.CheckStateRole:
            if col == self.COL_SELECT:
                if is_skipped:
                    return None  # no checkbox for always-skipped rows
                return Qt.CheckState.Checked if row in self._selected else Qt.CheckState.Unchecked
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_ID:
                return str(row + 1)
            elif col == self.COL_FILENAME:
                return file.content_filename
            elif col == self.COL_COURSE:
                return course.fullname
            elif col == self.COL_SIZE:
                if file.content_filesize > 0:
                    return format_bytes(file.content_filesize)
                return '\u2014'
            elif col == self.COL_STATUS:
                if is_skipped:
                    return self.tr('Always Skipped')
                if file.modified:
                    return self.tr('Modified')
                elif file.moved:
                    return self.tr('Moved')
                return self.tr('New')
            return None

        elif role == Qt.ItemDataRole.ForegroundRole:
            if is_skipped:
                return QColor(160, 160, 160)
            if col == self.COL_STATUS:
                if file.modified:
                    return QColor(255, 165, 0)  # orange
                elif file.moved:
                    return QColor(0, 100, 200)  # blue
                return QColor(0, 128, 0)  # green for New

        elif role == Qt.ItemDataRole.FontRole:
            if is_skipped:
                font = QFont()
                font.setStrikeOut(True)
                return font

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (self.COL_ID, self.COL_SIZE):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == self.COL_SELECT:
            row = index.row()
            if row in self._always_skipped_rows:
                return False
            if value == Qt.CheckState.Checked:
                self._selected.add(row)
            else:
                self._selected.discard(row)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == self.COL_SELECT and index.row() not in self._always_skipped_rows:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def remove_row(self, row) -> None:
        """Remove a single entry (one-time skip)."""
        if 0 <= row < len(self._entries):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._entries.pop(row)
            self._selected.discard(row)
            self._selected = {r - 1 if r > row else r for r in self._selected}
            self._always_skipped_rows.discard(row)
            self._always_skipped_rows = {r - 1 if r > row else r for r in self._always_skipped_rows}
            self.endRemoveRows()

    def remove_rows(self, rows) -> None:
        """Batch-remove multiple rows."""
        if not rows:
            return
        to_remove = set(rows)
        self.beginResetModel()
        self._entries = [e for i, e in enumerate(self._entries) if i not in to_remove]
        self._selected.clear()
        self._always_skipped_rows.clear()
        for i, (course, file, _) in enumerate(self._entries):
            if self.file_key(course, file) in self._always_skip:
                self._always_skipped_rows.add(i)
        self.endResetModel()

    def mark_always_skipped(self, rows) -> None:
        """Mark rows as always-skipped (visual only — config persistence is caller's job)."""
        for row in rows:
            entry = self.get_entry(row)
            if entry:
                key = self.file_key(entry[0], entry[1])
                self._always_skip.add(key)
                self._always_skipped_rows.add(row)
                self._selected.discard(row)
        if self._entries:
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def unmark_always_skipped(self, rows) -> None:
        """Restore rows from always-skipped state."""
        for row in rows:
            entry = self.get_entry(row)
            if entry:
                key = self.file_key(entry[0], entry[1])
                self._always_skip.discard(key)
                self._always_skipped_rows.discard(row)
        if self._entries:
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def is_always_skipped(self, row) -> bool:
        return row in self._always_skipped_rows

    def selected_rows(self) -> set:
        return set(self._selected)

    def has_selection(self) -> bool:
        return len(self._selected) > 0

    def get_remaining_courses(self):
        """Build a filtered list of Course objects from remaining entries (excludes always-skipped)."""
        course_map = {}
        for i, (course, file, _) in enumerate(self._entries):
            if i in self._always_skipped_rows:
                continue
            if course.id not in course_map:
                c = Course(course.id, course.fullname)
                c.overwrite_name_with = course.overwrite_name_with
                c.create_directory_structure = course.create_directory_structure
                c.excluded_sections = course.excluded_sections
                course_map[course.id] = c
            course_map[course.id].files.append(file)
        return list(course_map.values())

    def get_entry(self, row):
        """Return (course, file, idx) tuple for the given row."""
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def get_always_skip_keys(self):
        """Return the current set of always-skip keys."""
        return set(self._always_skip)


# ---------------------------------------------------------------------------
# Download task table model (unchanged from original)
# ---------------------------------------------------------------------------


class TaskTableModel(QAbstractTableModel):
    """Table model for displaying download tasks."""

    COL_ID = 0
    COL_FILENAME = 1
    COL_COURSE = 2
    COL_STATUS = 3
    COL_SIZE = 4
    COL_PROGRESS = 5
    COL_SKIP = 6

    COLUMNS = ['#', 'Filename', 'Course', 'Status', 'Size', 'Progress', 'Skip']

    def __init__(self) -> None:
        super().__init__()
        # User-facing header labels are translated here so they re-translate via self.tr.
        self._headers = [
            '#',
            self.tr('Filename'),
            self.tr('Course'),
            self.tr('Status'),
            self.tr('Size'),
            self.tr('Progress'),
            self.tr('Skip'),
        ]
        self._tasks = []

    def set_tasks(self, tasks) -> None:
        """Replace the task list and reset the model."""
        self.beginResetModel()
        self._tasks = tasks
        self.endResetModel()

    def refresh(self) -> None:
        """Notify the view that all data may have changed."""
        if self._tasks:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._tasks) - 1, len(self.COLUMNS) - 1),
            )

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._tasks):
            return None

        task = self._tasks[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_ID:
                return str(task.task_id)
            elif col == self.COL_FILENAME:
                return task.file.content_filename
            elif col == self.COL_COURSE:
                return task.course.fullname
            elif col == self.COL_STATUS:
                if task.status.skip_requested:
                    return self.tr('Skipped')
                return task.status.state.value
            elif col == self.COL_SIZE:
                total = task.file.content_filesize + task.status.external_total_size
                if total > 0:
                    return format_bytes(total)
                return '\u2014'
            elif col == self.COL_PROGRESS:
                total = task.file.content_filesize + task.status.external_total_size
                if total > 0:
                    pct = int(task.status.bytes_downloaded * 100 / total)
                    return f'{min(pct, 100)}%'
                if task.status.state == TaskState.FINISHED:
                    return '100%'
                return '\u2014'
            elif col == self.COL_SKIP:
                if task.status.state == TaskState.STARTED and not task.status.skip_requested:
                    return self.tr('Skip')
                return ''

        elif role == Qt.ItemDataRole.UserRole:
            if col == self.COL_SKIP:
                return task.status.state == TaskState.STARTED and not task.status.skip_requested
            return None

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (self.COL_ID, self.COL_SIZE, self.COL_PROGRESS):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_STATUS:
                state = task.status.state
                if task.status.skip_requested:
                    return QColor(255, 165, 0)  # orange
                if state == TaskState.FAILED:
                    return QColor(255, 0, 0)
                if state == TaskState.FINISHED:
                    return QColor(0, 128, 0)

        return None

    def get_task(self, row: int):
        """Return the task at the given row, or None."""
        if 0 <= row < len(self._tasks):
            return self._tasks[row]
        return None
