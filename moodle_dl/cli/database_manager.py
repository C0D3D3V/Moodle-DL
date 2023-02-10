import os

from moodle_dl.config import ConfigHelper
from moodle_dl.database import StateRecorder
from moodle_dl.moodle.moodle_service import MoodleService
from moodle_dl.types import File, MoodleDlOpts
from moodle_dl.utils import Cutie, Log


class DatabaseManager:
    def __init__(self, config: ConfigHelper, opts: MoodleDlOpts):
        self.config = config
        self.opts = opts
        self.state_recorder = StateRecorder(opts)

    def interactively_manage_database(self):
        stored_files = self.state_recorder.get_stored_files()

        stored_files = MoodleService.filter_courses(stored_files, self.config)

        if len(stored_files) <= 0:
            return

        course_options = []
        courses = []
        for course in stored_files:
            for course_file in course.files:
                if not os.path.exists(course_file.saved_to):
                    course_options.append(Log.blue_str(course.fullname))
                    courses.append(course)
                    break

        print(
            'This management tool will navigate you through a menu to'
            + ' selectively remove file entries from the database so'
            + ' that these files can be downloaded again.'
        )

        Log.warning(
            'Only files that are missing locally but stored in the local'
            + ' database are displayed in this tool. If a file is not missing'
            + ' from a course, it will not be listed here at all.  Also, only'
            + ' courses that are selected for download are displayed.'
        )

        Log.magenta(
            'For more complicated operations on the database a DB browser for SQLite'
            + ' is advantageous (https://sqlitebrowser.org/).'
        )

        if not courses:
            print('No files are missing locally but stored in the local database. Nothing to do.')
            return

        print('Choose one of the courses:')
        print('[Confirm your selection with the Enter key]')
        print('')
        selected_course_id = Cutie.select(options=course_options)

        selected_course = courses[selected_course_id]

        section_options = []
        sections = []

        # Add the option to select all sections
        section_options.append(Log.magenta_str('[All sections]'))
        sections.append(None)  # Add None at index 0 to avoid index shifting

        for course_file in selected_course.files:
            if not os.path.exists(course_file.saved_to) and (course_file.section_name not in sections):
                section_options.append(Log.magenta_str(course_file.section_name))
                sections.append(course_file.section_name)

        print('From which sections you want to select files?')
        print('[You can select with the space bar and confirm your selection with the enter key]')
        print('')

        selected_sections_ids = Cutie.select_multiple(options=section_options, minimal_count=1)

        selected_sections = []
        for selected_sections_id in selected_sections_ids:
            if selected_sections_id == 0:
                selected_sections = sections[1:]
                break
            elif (selected_sections_id) < len(sections):
                selected_sections.append(sections[selected_sections_id])

        file_options = []
        files = []

        # Add the option to select all files
        file_options.append(Log.cyan_str('[All files]'))
        files.append(None)  # Add None at index 0 to avoid index shifting

        for course_file in selected_course.files:
            if not os.path.exists(course_file.saved_to) and (course_file.section_name in selected_sections):
                file_options.append(Log.cyan_str(course_file.content_filename))
                files.append(course_file)

        print('Which of the files should be removed form the database, so that they will be re-downloaded?')
        print('[You can select with the space bar and confirm your selection with the enter key]')
        print('')
        selected_files = Cutie.select_multiple(options=file_options)

        files_to_delete = []
        for file_index in selected_files:
            if file_index == 0:  # If all files is selected
                for file_to_delete in files[1:]:  # Ignore the first element of the array set as None
                    if isinstance(file_to_delete, File):
                        files_to_delete.append(file_to_delete)

                break

            elif file_index < len(files) and isinstance(files[file_index], File):
                files_to_delete.append(files[file_index])

        self.state_recorder.batch_delete_files_from_db(files_to_delete)

    def delete_old_files(self):
        stored_files = self.state_recorder.get_old_files()

        if len(stored_files) <= 0:
            print('No old copies of files found. Nothing to do.')
            return

        print(
            'This management tool will navigate you through a menu to'
            + ' selectively remove old copies of files from the database '
            + ' and form the file system'
        )

        course_options = []
        for course in stored_files:
            course_options.append(Log.blue_str(course.fullname))

        print('Choose one of the courses:')
        print('[Confirm your selection with the Enter key]')
        print('')
        selected_course_id = Cutie.select(options=course_options)

        selected_course = stored_files[selected_course_id]

        section_options = []
        sections = []

        # Add the option to select all sections
        section_options.append(Log.magenta_str('[All sections]'))
        sections.append(None)  # Add None at index 0 to avoid index shifting

        for course_file in selected_course.files:
            if course_file.section_name not in sections:
                section_options.append(Log.magenta_str(course_file.section_name))
                sections.append(course_file.section_name)

        print('From which sections you want to delete old files?')
        print('[You can select with the space bar and confirm your selection with the enter key]')
        print('')

        selected_sections_ids = Cutie.select_multiple(options=section_options, minimal_count=1)

        selected_sections = []
        for selected_sections_id in selected_sections_ids:
            if selected_sections_id == 0:
                selected_sections = sections[1:]
                break
            elif (selected_sections_id) < len(sections):
                selected_sections.append(sections[selected_sections_id])

        file_options = []
        files = []

        # Add the option to select all files
        file_options.append(Log.cyan_str('[All files]'))
        files.append(None)  # Add None at index 0 to avoid index shifting

        for course_file in selected_course.files:
            if course_file.section_name in selected_sections:
                file_options.append(Log.cyan_str(course_file.content_filename))
                files.append(course_file)

        print('Which of the files should be deleted?')
        print('[You can select with the space bar and confirm your selection with the enter key]')
        print('')
        selected_files = Cutie.select_multiple(options=file_options)

        files_to_delete = []
        for file_index in selected_files:
            if file_index == 0:  # If all files is selected
                for file_to_delete in files[1:]:  # Ignore the first element of the array set as None
                    if isinstance(file_to_delete, File):
                        files_to_delete.append(file_to_delete)
                        if os.path.exists(file_to_delete.saved_to):
                            os.remove(file_to_delete.saved_to)

                break

            elif file_index < len(files) and isinstance(files[file_index], File):
                files_to_delete.append(files[file_index])
                if os.path.exists(files[file_index].saved_to):
                    os.remove(files[file_index].saved_to)

        self.state_recorder.batch_delete_files_from_db(files_to_delete)
