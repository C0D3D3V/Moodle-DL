import os

from pathlib import Path

from moodle_dl.utils import cutie
from moodle_dl.state_recorder.file import File
from moodle_dl.moodle_connector.moodle_service import MoodleService
from moodle_dl.config_service.config_helper import ConfigHelper
from moodle_dl.state_recorder.state_recorder import StateRecorder


class OfflineService:
    def __init__(self, config_helper: ConfigHelper, storage_path: str):
        """
        Initialize the storage.

        Args:
            self: (todo): write your description
            config_helper: (todo): write your description
            storage_path: (str): write your description
        """
        self.config_helper = config_helper
        self.storage_path = storage_path
        self.state_recorder = StateRecorder(Path(storage_path) / 'moodle_state.db')

    def interactively_manage_database(self):
        """
        Manage files

        Args:
            self: (todo): write your description
        """
        RESET_SEQ = '\033[0m'
        COLOR_SEQ = '\033[1;%dm'

        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

        stored_files = self.state_recorder.get_stored_files()

        stored_files = MoodleService.filter_courses(stored_files, self.config_helper)

        if len(stored_files) <= 0:
            return

        print(
            'This management tool will navigate you through a menu to'
            + ' selectively remove file entries from the database so'
            + ' that these files can be downloaded again.'
        )

        course_options = []
        courses = []
        for course in stored_files:
            for course_file in course.files:
                if not os.path.exists(course_file.saved_to):
                    course_options.append(COLOR_SEQ % BLUE + course.fullname + RESET_SEQ)
                    courses.append(course)
                    break

        print('Choose one of the courses:')
        print('[Confirm your selection with the Enter key]')
        print('')
        selected_course_id = cutie.select(options=course_options)

        selected_course = courses[selected_course_id]

        section_options = []
        sections = []
        for course_file in selected_course.files:
            if not os.path.exists(course_file.saved_to) and (course_file.section_name not in sections):
                section_options.append(COLOR_SEQ % MAGENTA + course_file.section_name + RESET_SEQ)
                sections.append(course_file.section_name)

        print('From which sections you want to select files.')
        print('[You can select with the space bar and confirm your selection with the enter key]')
        print('')

        selected_sections_ids = cutie.select_multiple(options=section_options, minimal_count=1)
        selected_sections = []
        for selected_sections_id in selected_sections_ids:
            if selected_sections_id < len(sections):
                selected_sections.append(sections[selected_sections_id])

        file_options = []
        files = []
        for course_file in selected_course.files:
            if not os.path.exists(course_file.saved_to) and (course_file.section_name in selected_sections):
                file_options.append(COLOR_SEQ % CYAN + course_file.content_filename + RESET_SEQ)
                files.append(course_file)

        print('Which of the files should be removed form the database, so that they will be redownloaded?')
        print('[You can select with the space bar and confirm your selection with the enter key]')
        print('')
        selected_files = cutie.select_multiple(options=file_options)

        files_to_delete = []
        for file_index in selected_files:
            if file_index < len(files) and isinstance(files[file_index], File):
                files_to_delete.append(files[file_index])

        self.state_recorder.batch_delete_files_from_db(files_to_delete)
