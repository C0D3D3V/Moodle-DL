from utils import cutie
from state_recorder.course import Course
from config_service.config_helper import ConfigHelper
from moodle_connector.results_handler import ResultsHandler
from moodle_connector.request_helper import RequestRejectedError, RequestHelper


class ConfigService:
    def __init__(self, config_helper: ConfigHelper, storage_path: str,
                 skip_cert_verify: bool = False):
        self.config_helper = config_helper
        self.storage_path = storage_path
        self.skip_cert_verify = skip_cert_verify

    def interactively_acquire_config(self):
        """
        Guides the user through the process of configuring the downloader
        for the courses to be downloaded and in what way
        """

        token = self.get_token()
        moodle_domain = self.get_moodle_domain()
        moodle_path = self.get_moodle_path()

        request_helper = RequestHelper(moodle_domain, moodle_path, token,
                                       self.skip_cert_verify)
        results_handler = ResultsHandler(request_helper)

        courses = []
        try:

            userid, version = results_handler.fetch_userid_and_version()
            results_handler.setVersion(version)

            courses = results_handler.fetch_courses(userid)

        except (RequestRejectedError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                'Error while communicating with the Moodle System! (%s)' % (
                    error))

        self._select_courses_to_download(courses)
        self._set_options_of_courses(courses)
        self._select_should_download_submissions()

    def _select_courses_to_download(self, courses: [Course]):
        """
        Asks the user for the courses that should be downloaded.
        @param courses: All available courses
        """
        download_course_ids = self.get_download_course_ids()
        dont_download_course_ids = self.get_dont_download_course_ids()

        print('')
        print('To avoid downloading all the Moodle courses you are' +
              ' enrolled in, you can select which ones you want' +
              ' to download here. ')
        print('')

        choices = []
        defaults = []
        for i, course in enumerate(courses):
            choices.append(('%5i\t%s' %
                            (course.id, course.fullname)))

            if (ResultsHandler._should_download_course(
                    course.id, download_course_ids, dont_download_course_ids)):
                defaults.append(i)

        print('Which of the courses should be downloaded?')
        print('[You can select with the space bar and confirm' +
              ' your selection with the enter key]')
        print('')
        selected_courses = cutie.select_multiple(
            options=choices, ticked_indices=defaults)

        download_course_ids = []
        for i, course in enumerate(courses):
            if i in selected_courses:
                download_course_ids.append(course.id)

        self.config_helper.set_property('download_course_ids',
                                        download_course_ids)

        self.config_helper.remove_property('dont_download_course_ids')

    def _set_options_of_courses(self, courses: [Course]):
        """
        Let the user set special options for every single course
        """
        download_course_ids = self.get_download_course_ids()
        dont_download_course_ids = self.get_dont_download_course_ids()

        print('')
        print('You can set special settings for every single course.' +
              ' You can set these options:\n' +
              '- A different name for the course\n' +
              '- If a directory structure should be created for the course' +
              ' [create_directory_structure (cfs)].')
        print('')

        while(True):

            choices = []
            choices_courses = []

            options_of_courses = self.get_options_of_courses()

            for course in courses:
                if(ResultsHandler._should_download_course(
                        course.id, download_course_ids,
                        dont_download_course_ids)):

                    current_course_settings = options_of_courses.get(
                        str(course.id), None)

                    # create default settings
                    if current_course_settings is None:
                        current_course_settings = {
                            'original_name': course.fullname,
                            'overwrite_name_with': None,
                            'create_directory_structure': True
                        }

                    # create list of options
                    overwrite_name_with = current_course_settings.get(
                        'overwrite_name_with', None)

                    create_directory_structure = current_course_settings.get(
                        'create_directory_structure', True)

                    if(overwrite_name_with is not None and
                            overwrite_name_with != course.fullname):
                        choices.append(('%5i\t%s\t(%s) cfs=%s' %
                                        (course.id, overwrite_name_with,
                                            course.fullname,
                                            create_directory_structure)))

                    else:
                        choices.append(('%5i\t%s  cfs=%s' %
                                        (course.id, course.fullname,
                                            create_directory_structure)))

                    choices_courses.append(course)

            choices.append('None')

            print('')
            print('For which of the following course do you want to change' +
                  ' the settings?')
            print('[Confirm your selection with the Enter key]')
            print('')

            selected_course = cutie.select(options=choices)
            if(selected_course == len(choices_courses)):
                break
            else:
                self._change_settings_of(choices_courses[selected_course],
                                         options_of_courses)

    def _change_settings_of(self, course: Course, options_of_courses: {}):
        """
        Ask for a new Name for the course.
        Then asks if a file structure should be created.
        """

        current_course_settings = options_of_courses.get(
            str(course.id), None)

        # create default settings
        if current_course_settings is None:
            current_course_settings = {
                'original_name': course.fullname,
                'overwrite_name_with': None,
                'create_directory_structure': True
            }

        changed = False

        # Ask for new name
        overwrite_name_with = input(
            ('Enter a new name for this Course [leave blank for "%s"]:   ' %
             (course.fullname,)))

        if (overwrite_name_with == ''):
            overwrite_name_with = None

        if (overwrite_name_with != course.fullname and
                current_course_settings.get(
                    'overwrite_name_with', None) != overwrite_name_with):
            current_course_settings.update(
                {'overwrite_name_with': overwrite_name_with})
            changed = True

        # Ask if a file structure should be created
        create_directory_structure = current_course_settings.get(
            'create_directory_structure', True)

        create_directory_structure = cutie.prompt_yes_or_no(
            'Should a directory structure be created for this course?',
            default_is_yes=create_directory_structure)

        if (create_directory_structure is not current_course_settings.get(
                'create_directory_structure', True)):
            changed = True
            current_course_settings.update(
                {'create_directory_structure': create_directory_structure})

        if(changed):
            options_of_courses.update(
                {str(course.id): current_course_settings})
            self.config_helper.set_property(
                'options_of_courses', options_of_courses)

    def _select_should_download_submissions(self):
        """
        Asks the user if submissions should be downloaded
        """
        download_submissions = self.get_download_submissions()

        print('')
        print('Submissions are files that you or a teacher have uploaded' +
              ' to your assignments. Moodle does not provide an' +
              ' interface for downloading information from all' +
              ' submissions to a course at once. Therefore, it' +
              ' may be slow to monitor changes to submissions.')
        print('')

        download_submissions = cutie.prompt_yes_or_no(
            'Do you want to download submissions of your assignments?',
            default_is_yes=download_submissions)

        self.config_helper.set_property('download_submissions',
                                        download_submissions)

    def get_token(self) -> str:
        # returns a stored token
        try:
            return self.config_helper.get_property('token')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_domain(self) -> str:
        # returns a stored moodle_domain
        try:
            return self.config_helper.get_property('moodle_domain')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_path(self) -> str:
        # returns a stored moodle_path
        try:
            return self.config_helper.get_property('moodle_path')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_download_submissions(self) -> str:
        # returns a stored boolean if submissions should be downloaded
        try:
            return self.config_helper.get_property('download_submissions')
        except ValueError:
            return False

    def get_download_course_ids(self) -> str:
        # returns a stored list of ids that should be downloaded
        try:
            return self.config_helper.get_property('download_course_ids')
        except ValueError:
            return []

    def get_dont_download_course_ids(self) -> str:
        # returns a stored list of ids that should not be downloaded
        try:
            return self.config_helper.get_property('dont_download_course_ids')
        except ValueError:
            return []

    def get_options_of_courses(self) -> str:
        # returns a stored dictionary of options for courses
        try:
            return self.config_helper.get_property('options_of_courses')
        except ValueError:
            return {}
