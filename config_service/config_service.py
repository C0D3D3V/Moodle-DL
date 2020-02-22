import cutie

from state_recorder.course import Course
from config_service.config_helper import ConfigHelper
from moodle_connector.results_handler import ResultsHandler
from moodle_connector.request_helper import RequestRejectedError, RequestHelper


class ConfigService:
    def __init__(self, config_helper: ConfigHelper, storage_path: str):
        self.config_helper = config_helper
        self.storage_path = storage_path

    def interactively_acquire_config(self):
        """
        Guides the user through the process of configuring the downloader
        for the courses to be downloaded and in what way
        """

        token = self.get_token()
        moodle_domain = self.get_moodle_domain()
        moodle_path = self.get_moodle_path()

        request_helper = RequestHelper(moodle_domain, moodle_path, token)
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
        self._select_should_download_submissions()

    def _select_courses_to_download(self, courses: [Course]):
        """
        Asks the userer for the courses that should be downloaded.
        @param courses: All availible courses
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
        print('[You can select with space bar or enter key.' +
              ' All other keys confirm the selection.]')
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
        raw_download_submissions = '-'
        question_extension = '[y/N]   '
        if (download_submissions):
            question_extension = '[Y/n]   '

        while raw_download_submissions not in ['y', 'n', '']:
            raw_download_submissions = input(
                'Do you want to download submissions of your' +
                ' assignments? ' + question_extension).lower()

        if (raw_download_submissions != ''):
            download_submissions = False
            if raw_download_submissions == 'y':
                download_submissions = True

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
