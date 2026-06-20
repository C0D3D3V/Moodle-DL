from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from moodle_dl.config import ConfigHelper
from moodle_dl.gui.style_utils import set_status_text
from moodle_dl.gui.workers import FetchSectionsWorker


class CourseOptionsDialog(QDialog):
    """Dialog for per-course customization (custom name, directory structure, section exclusion)."""

    def __init__(self, config: ConfigHelper, opts, course_id: int, course_name: str, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.opts = opts
        self.course_id = course_id
        self.course_name = course_name
        self._sections_worker = None
        self._section_checkboxes = {}

        self.setWindowTitle(self.tr('Options for: {}').format(course_name))
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)

        self._setup_ui()
        self._load_options()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText(self.course_name)
        self.custom_name_input.setToolTip(self.tr('Override the course folder name. Leave empty to use the default.'))
        form.addRow(self.tr('Custom Name:'), self.custom_name_input)

        self.cb_create_dir = QCheckBox(self.tr('Create Directory Structure'))
        self.cb_create_dir.setChecked(True)
        self.cb_create_dir.setToolTip(self.tr('Create subdirectories matching the Moodle course section structure.'))
        form.addRow(self.cb_create_dir)

        layout.addLayout(form)

        # Section Exclusion
        sections_group = QGroupBox(self.tr('Section Exclusion'))
        sections_layout = QVBoxLayout()

        sections_hint = QLabel(self.tr('Uncheck sections to exclude them from downloads.'))
        sections_hint.setStyleSheet('color: #666; font-style: italic;')
        sections_layout.addWidget(sections_hint)

        self.load_sections_btn = QPushButton(self.tr('Load Sections'))
        self.load_sections_btn.setToolTip(self.tr('Fetch available sections from Moodle.'))
        self.load_sections_btn.clicked.connect(self._on_fetch_sections)
        sections_layout.addWidget(self.load_sections_btn)

        self.sections_status = QLabel('')
        sections_layout.addWidget(self.sections_status)

        self.sections_scroll = QScrollArea()
        self.sections_scroll.setWidgetResizable(True)
        self.sections_list_widget = QWidget()
        self.sections_list_layout = QVBoxLayout(self.sections_list_widget)
        self.sections_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sections_scroll.setWidget(self.sections_list_widget)
        sections_layout.addWidget(self.sections_scroll)

        sections_group.setLayout(sections_layout)
        layout.addWidget(sections_group, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_options(self) -> None:
        """Load existing per-course options from config."""
        options = self.config.get_property_or('options_of_courses', {})
        course_opts = options.get(str(self.course_id), {})
        self.custom_name_input.setText(course_opts.get('overwrite_name_with', ''))
        self.cb_create_dir.setChecked(course_opts.get('create_directory_structure', True))

    def _on_fetch_sections(self) -> None:
        """Fetch sections from Moodle for this course."""
        self.load_sections_btn.setEnabled(False)
        self.load_sections_btn.setText(self.tr('Fetching\u2026'))
        self.setCursor(QCursor(Qt.CursorShape.BusyCursor))
        set_status_text(self.sections_status, self.tr('Fetching sections\u2026'), 'info')

        self._sections_worker = FetchSectionsWorker(self.config, self.opts, self.course_id)
        self._sections_worker.sections_fetched.connect(self._on_sections_fetched)
        self._sections_worker.error_occurred.connect(self._on_sections_error)
        self._sections_worker.start()

    def _on_sections_fetched(self, sections: list) -> None:
        """Populate section checkboxes."""
        self.load_sections_btn.setEnabled(True)
        self.load_sections_btn.setText(self.tr('Load Sections'))
        self.unsetCursor()
        set_status_text(self.sections_status, self.tr('Found {} sections.').format(len(sections)), 'success')

        # Clear existing checkboxes
        for cb in self._section_checkboxes.values():
            self.sections_list_layout.removeWidget(cb)
            cb.deleteLater()
        self._section_checkboxes.clear()

        # Load excluded sections from config
        options = self.config.get_property_or('options_of_courses', {})
        course_opts = options.get(str(self.course_id), {})
        excluded = set(course_opts.get('excluded_sections', []))

        for section in sections:
            section_id = section['id']
            section_name = section.get('name', self.tr('Section {}').format(section_id))
            cb = QCheckBox(self.tr('{} (ID: {})').format(section_name, section_id))
            cb.setChecked(section_id not in excluded)
            self.sections_list_layout.addWidget(cb)
            self._section_checkboxes[section_id] = cb

    def _on_sections_error(self, error_msg: str) -> None:
        self.load_sections_btn.setEnabled(True)
        self.load_sections_btn.setText(self.tr('Load Sections'))
        self.unsetCursor()
        set_status_text(self.sections_status, self.tr('Error: {}').format(error_msg), 'error')

    def _on_save(self) -> None:
        """Save per-course options to config."""
        options = self.config.get_property_or('options_of_courses', {})
        if not isinstance(options, dict):
            options = {}

        course_opts = {}
        custom_name = self.custom_name_input.text().strip()
        if custom_name:
            course_opts['overwrite_name_with'] = custom_name
        course_opts['create_directory_structure'] = self.cb_create_dir.isChecked()

        # Save excluded sections
        if self._section_checkboxes:
            excluded = [sid for sid, cb in self._section_checkboxes.items() if not cb.isChecked()]
            if excluded:
                course_opts['excluded_sections'] = excluded

        options[str(self.course_id)] = course_opts
        self.config.set_property('options_of_courses', options)
        self.accept()
