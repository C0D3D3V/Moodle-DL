import logging
import os
from getpass import getpass
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from utils.config_helper import ConfigHelper
from moodle_connector import login_helper
from moodle_connector.request_helper import RequestRejectedError, RequestHelper
from moodle_connector.results_handler import ResultsHandler
from utils.state_recorder import StateRecorder, CollectionOfChanges


class MoodleService:
    def __init__(self, config_helper: ConfigHelper, storage_path : str):
        self.config_helper = config_helper
        self.recorder = StateRecorder(os.path.join(storage_path, 'moodle_state.db'))


    def interactively_acquire_token(self) -> str:
        """
        Walks the user through executing a login into the Moodle-System to get the Token and saves it.
        @return: The Token for Moodle.
        """
        print('[The following Credentials are not saved, it is only used temporarily to generate a login token.]')

        moodle_token = None
        while moodle_token is None:
            moodle_url = input('URL of Moodle:   ')
            moodle_username = input('Username for Moodle:   ')
            moodle_password = getpass('Password for Moodle [no output]:   ')

            moodle_uri = urlparse(moodle_url)

            moodle_domain = moodle_uri.netloc
            moodle_path = os.path.join(os.path.dirname(moodle_uri.path), '')

            try:
                moodle_token = login_helper.obtain_login_token(moodle_username, moodle_password, moodle_domain, moodle_path)
            except RequestRejectedError as error:
                print('Login Failed! (%s) Please try again.' % (error))
            except (ValueError, RuntimeError) as error:
                print(
                    'Error while communicating with the Moodle System! (%s) Please try again.' % (error))

        self.config_helper.set_property('token', moodle_token)
        self.config_helper.set_property('moodle_domain', moodle_domain)
        self.config_helper.set_property('moodle_path', moodle_path)

        return moodle_token

 
    def fetch_state(self) -> (CollectionOfChanges):
        """
        Gets the current status of the configured Moodle account and compares it
        with the last known status for changes. It does not change the known state,
        nor does it download the files. 
        @return: Tuple with (detected changes)
        """
        logging.debug('Fetching current Moodle State...')
        
        token = self.get_token()
        moodle_domain = self.get_moodle_domain()
        moodle_path = self.get_moodle_path()


        request_helper = RequestHelper(moodle_domain, moodle_path, token)
        list_handler = ResultsHandler(request_helper)

        courses = []
        try:

            userid = list_handler.fetch_userid()
            courses = list_handler.fetch_courses(userid)

            for i, course in enumerate(courses):
                course_id = course.get("id")
                courses[i]["files"] = list_handler.fetch_files(course_id)

        except (RequestRejectedError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                'Error while communicating with the Moodle System! (%s)' % (error))

        logging.debug('Checking for changes...')
        changes = self.recorder.changes_of_new_version(courses)

        return changes

 
    def get_token(self) -> str:
        try:
            return self.config_helper.get_property('token')
        except ValueError:
            raise ValueError('Not yet configured!')


    def get_moodle_domain(self) -> str:
        try:
            return self.config_helper.get_property('moodle_domain')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_path(self) -> str:
        try:
            return self.config_helper.get_property('moodle_path')
        except ValueError:
            raise ValueError('Not yet configured!')

