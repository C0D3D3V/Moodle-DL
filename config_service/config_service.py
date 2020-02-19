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

            index = 0
            for course in courses:
                index += 1
                print('%3i. Course:\t%5i\t%s' % (index, course.id,
                                                 course.fullname))
                print('')

        except (RequestRejectedError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                'Error while communicating with the Moodle System! (%s)' % (
                    error))

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
