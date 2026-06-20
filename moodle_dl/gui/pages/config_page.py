import logging

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.style_utils import set_status_text
from moodle_dl.gui.workers import FetchCoursesWorker


class ConfigPage(QWidget):
    config_saved = Signal()

    def __init__(self, config: ConfigHelper, opts) -> None:
        super().__init__()
        self.config = config
        self.opts = opts
        self._worker = None
        self._course_checkboxes = {}
        self._checkbox_to_course = {}
        self._courses_loaded = False

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Course selection
        courses_group = QGroupBox(self.tr('Courses'))
        courses_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.fetch_btn = QPushButton(self.tr('Fetch Courses'))
        self.fetch_btn.clicked.connect(self._on_fetch_courses)
        btn_row.addWidget(self.fetch_btn)

        self.select_all_btn = QPushButton(self.tr('Select All'))
        self.select_all_btn.clicked.connect(self._select_all_courses)
        self.select_all_btn.setEnabled(False)
        btn_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton(self.tr('Deselect All'))
        self.deselect_all_btn.clicked.connect(self._deselect_all_courses)
        self.deselect_all_btn.setEnabled(False)
        btn_row.addWidget(self.deselect_all_btn)

        btn_row.addStretch()
        courses_layout.addLayout(btn_row)

        # Whitelist / Blacklist mode toggle
        mode_row = QHBoxLayout()
        self.radio_whitelist = QRadioButton(self.tr('Download selected courses'))
        self.radio_blacklist = QRadioButton(self.tr('Download all except selected'))
        self.radio_whitelist.setChecked(True)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.radio_whitelist)
        self._mode_group.addButton(self.radio_blacklist)
        mode_row.addWidget(self.radio_whitelist)
        mode_row.addWidget(self.radio_blacklist)
        mode_row.addStretch()
        courses_layout.addLayout(mode_row)

        self.courses_status = QLabel(self.tr('Click "Fetch Courses" to load your course list.'))
        courses_layout.addWidget(self.courses_status)

        # Course search/filter
        self.course_filter_input = QLineEdit()
        self.course_filter_input.setPlaceholderText(self.tr('Filter courses\u2026'))
        self.course_filter_input.setClearButtonEnabled(True)
        self.course_filter_input.textChanged.connect(self._on_filter_changed)
        courses_layout.addWidget(self.course_filter_input)

        # Hint label for course options
        hint_label = QLabel(self.tr('Double-click a course to set custom name and options.'))
        hint_label.setStyleSheet('color: #666; font-style: italic;')
        courses_layout.addWidget(hint_label)

        # Scrollable course list
        self.course_scroll = QScrollArea()
        self.course_scroll.setWidgetResizable(True)
        self.course_list_widget = QWidget()
        self.course_list_layout = QVBoxLayout(self.course_list_widget)
        self.course_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.course_scroll.setWidget(self.course_list_widget)
        courses_layout.addWidget(self.course_scroll)

        courses_group.setLayout(courses_layout)
        layout.addWidget(courses_group, 1)  # stretch factor so scroll area expands

        # Download options
        options_group = QGroupBox(self.tr('Download Options'))
        options_layout = QVBoxLayout()

        self.opt_submissions = QCheckBox(self.tr('Download Submissions'))
        self.opt_submissions.setToolTip(self.tr('Download student assignment submissions.'))
        self.opt_descriptions = QCheckBox(self.tr('Download Descriptions'))
        self.opt_descriptions.setToolTip(self.tr('Download activity and resource descriptions as HTML files.'))
        self.opt_links_in_desc = QCheckBox(self.tr('Download Links in Descriptions'))
        self.opt_links_in_desc.setToolTip(self.tr('Download files linked within activity descriptions.'))
        self.opt_databases = QCheckBox(self.tr('Download Databases'))
        self.opt_databases.setToolTip(self.tr('Download Moodle database activity entries.'))
        self.opt_forums = QCheckBox(self.tr('Download Forums'))
        self.opt_forums.setToolTip(self.tr('Download forum posts and attachments.'))
        self.opt_quizzes = QCheckBox(self.tr('Download Quizzes'))
        self.opt_quizzes.setToolTip(self.tr('Download quiz attempts and results.'))
        self.opt_lessons = QCheckBox(self.tr('Download Lessons'))
        self.opt_lessons.setToolTip(self.tr('Download lesson activity content.'))
        self.opt_workshops = QCheckBox(self.tr('Download Workshops'))
        self.opt_workshops.setToolTip(self.tr('Download workshop submissions and assessments.'))
        self.opt_books = QCheckBox(self.tr('Download Books'))
        self.opt_books.setToolTip(self.tr('Download book resource content as HTML.'))
        self.opt_calendars = QCheckBox(self.tr('Download Calendars'))
        self.opt_calendars.setToolTip(self.tr('Download course calendar events.'))
        self.opt_linked_files = QCheckBox(self.tr('Download Linked Files'))
        self.opt_linked_files.setToolTip(self.tr('Download externally linked files referenced in courses.'))
        self.opt_cookie_files = QCheckBox(self.tr('Download Files Requiring Cookie'))
        self.opt_cookie_files.setToolTip(self.tr('Also download files that require browser cookies for access.'))

        for cb in [
            self.opt_submissions,
            self.opt_descriptions,
            self.opt_links_in_desc,
            self.opt_databases,
            self.opt_forums,
            self.opt_quizzes,
            self.opt_lessons,
            self.opt_workshops,
            self.opt_books,
            self.opt_calendars,
            self.opt_linked_files,
            self.opt_cookie_files,
        ]:
            options_layout.addWidget(cb)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Save button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.save_btn = QPushButton(self.tr('Save Configuration'))
        self.save_btn.clicked.connect(self._on_save)
        save_layout.addWidget(self.save_btn)
        layout.addLayout(save_layout)
        layout.addStretch()

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        save_shortcut = QShortcut(QKeySequence('Ctrl+S'), self)
        save_shortcut.activated.connect(self._on_save)

    def on_show(self) -> None:
        """Called when this page becomes visible."""
        self._load_current_options()
        if not self._courses_loaded:
            self._on_fetch_courses()

    def _load_current_options(self) -> None:
        """Load current config options into checkboxes."""
        try:
            self.opt_submissions.setChecked(self.config.get_download_submissions())
            self.opt_descriptions.setChecked(self.config.get_download_descriptions())
            self.opt_links_in_desc.setChecked(self.config.get_download_links_in_descriptions())
            self.opt_databases.setChecked(self.config.get_download_databases())
            self.opt_forums.setChecked(self.config.get_download_forums())
            self.opt_quizzes.setChecked(self.config.get_download_quizzes())
            self.opt_lessons.setChecked(self.config.get_download_lessons())
            self.opt_workshops.setChecked(self.config.get_download_workshops())
            self.opt_books.setChecked(self.config.get_download_books())
            self.opt_calendars.setChecked(self.config.get_download_calendars())
            self.opt_linked_files.setChecked(self.config.get_download_linked_files())
            self.opt_cookie_files.setChecked(self.config.get_download_also_with_cookie())
        except (ValueError, ConfigHelper.NoConfigError):
            pass

    def _on_fetch_courses(self) -> None:
        """Fetch the course list from Moodle."""
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText(self.tr('Fetching\u2026'))
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.courses_status, self.tr('Fetching courses\u2026'), 'info')

        self._worker = FetchCoursesWorker(self.config, self.opts)
        self._worker.courses_fetched.connect(self._on_courses_fetched)
        self._worker.error_occurred.connect(self._on_fetch_error)
        self._worker.start()

    def _on_courses_fetched(self, courses: list) -> None:
        """Handle fetched course list."""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText(self.tr('Fetch Courses'))
        self.unsetCursor()
        self._courses_loaded = True
        set_status_text(self.courses_status, self.tr('Found {} courses.').format(len(courses)), 'success')
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)

        # Clear existing checkboxes
        for cb in self._course_checkboxes.values():
            self.course_list_layout.removeWidget(cb)
            cb.deleteLater()
        self._course_checkboxes.clear()
        self._checkbox_to_course.clear()

        # Detect whitelist vs blacklist mode
        download_ids = set(self.config.get_download_course_ids())
        dont_download_ids = set(self.config.get_dont_download_course_ids())
        use_blacklist = self.config.get_course_filter_mode() == 'blacklist'

        if use_blacklist:
            self.radio_blacklist.setChecked(True)
        else:
            self.radio_whitelist.setChecked(True)

        # If no courses configured yet, select all by default
        first_time = len(download_ids) == 0 and len(dont_download_ids) == 0

        # Add checkboxes for each course
        # Checked always means "this course will be downloaded"
        for course_info in courses:
            course_id = course_info['id']
            fullname = course_info['fullname']
            cb = QCheckBox(self.tr('{} (ID: {})').format(fullname, course_id))
            cb.installEventFilter(self)
            self._checkbox_to_course[cb] = (course_id, fullname)
            if first_time:
                cb.setChecked(True)
            elif use_blacklist:
                cb.setChecked(course_id not in dont_download_ids)
            else:
                cb.setChecked(course_id in download_ids)
            self.course_list_layout.addWidget(cb)
            self._course_checkboxes[course_id] = cb

        # Apply current filter
        self._on_filter_changed(self.course_filter_input.text())

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonDblClick and obj in self._checkbox_to_course:
            cid, name = self._checkbox_to_course[obj]
            self._on_course_double_clicked(cid, name)
            return True
        return super().eventFilter(obj, event)

    def _on_fetch_error(self, error_msg: str) -> None:
        """Handle course fetch error."""
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText(self.tr('Fetch Courses'))
        self.unsetCursor()
        set_status_text(self.courses_status, self.tr('Error: {}').format(error_msg), 'error')
        logging.error('Failed to fetch courses: %s', error_msg)

    def _on_filter_changed(self, text: str) -> None:
        """Filter course checkboxes by search text."""
        needle = text.strip().lower()
        for cb in self._course_checkboxes.values():
            cb.setVisible(needle in cb.text().lower() if needle else True)

    def _on_course_double_clicked(self, course_id: int, course_name: str) -> None:
        """Open per-course options dialog."""
        from moodle_dl.gui.dialogs.course_options_dialog import CourseOptionsDialog

        dialog = CourseOptionsDialog(self.config, self.opts, course_id, course_name, self)
        dialog.exec()

    def _select_all_courses(self) -> None:
        """Select all visible course checkboxes."""
        for cb in self._course_checkboxes.values():
            if cb.isVisible():
                cb.setChecked(True)

    def _deselect_all_courses(self) -> None:
        """Deselect all visible course checkboxes."""
        for cb in self._course_checkboxes.values():
            if cb.isVisible():
                cb.setChecked(False)

    def _on_save(self) -> None:
        """Save course selection and download options."""
        use_blacklist = self.radio_blacklist.isChecked()

        if use_blacklist:
            # Blacklist: save UNchecked IDs to dont_download_course_ids
            unchecked_ids = []
            for course_id, cb in self._course_checkboxes.items():
                if not cb.isChecked():
                    unchecked_ids.append(course_id)
            self.config.set_property('dont_download_course_ids', unchecked_ids)
            self.config.remove_property('download_course_ids')
        else:
            # Whitelist: save checked IDs to download_course_ids
            selected_ids = []
            for course_id, cb in self._course_checkboxes.items():
                if cb.isChecked():
                    selected_ids.append(course_id)

            if self._course_checkboxes and not selected_ids:
                QMessageBox.warning(self, self.tr('No courses selected'), self.tr('Please select at least one course.'))
                return

            self.config.set_property('download_course_ids', selected_ids)
            self.config.remove_property('dont_download_course_ids')

        self.config.set_property('course_filter_mode', 'blacklist' if use_blacklist else 'whitelist')

        # Save download options
        self.config.set_property('download_submissions', self.opt_submissions.isChecked())
        self.config.set_property('download_descriptions', self.opt_descriptions.isChecked())
        self.config.set_property('download_links_in_descriptions', self.opt_links_in_desc.isChecked())
        self.config.set_property('download_databases', self.opt_databases.isChecked())
        self.config.set_property('download_forums', self.opt_forums.isChecked())
        self.config.set_property('download_quizzes', self.opt_quizzes.isChecked())
        self.config.set_property('download_lessons', self.opt_lessons.isChecked())
        self.config.set_property('download_workshops', self.opt_workshops.isChecked())
        self.config.set_property('download_books', self.opt_books.isChecked())
        self.config.set_property('download_calendars', self.opt_calendars.isChecked())
        self.config.set_property('download_linked_files', self.opt_linked_files.isChecked())
        self.config.set_property('download_also_with_cookie', self.opt_cookie_files.isChecked())

        QMessageBox.information(self, self.tr('Saved'), self.tr('Configuration saved successfully.'))
        self.config_saved.emit()
