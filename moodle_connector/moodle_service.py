import sys
import shutil
import logging

from pathlib import Path
from getpass import getpass
from urllib.parse import urlparse

from utils import cutie
from config_service.config_helper import ConfigHelper
from state_recorder.course import Course
from state_recorder.state_recorder import StateRecorder
from moodle_connector import login_helper
from moodle_connector import sso_token_receiver
from moodle_connector.results_handler import ResultsHandler
from moodle_connector.request_helper import RequestRejectedError, RequestHelper


class MoodleService:
    def __init__(self, config_helper: ConfigHelper, storage_path: str,
                 skip_cert_verify: bool = False):
        self.config_helper = config_helper
        self.storage_path = storage_path
        self.recorder = StateRecorder(
            Path(storage_path) / 'moodle_state.db')
        self.skip_cert_verify = skip_cert_verify

    def interactively_acquire_token(self) -> str:
        """
        Walks the user through executing a login into the Moodle-System to get
        the Token and saves it.
        @return: The Token for Moodle.
        """
        print('[The following Credentials are not saved, it is only used' +
              ' temporarily to generate a login token.]')

        moodle_token = None
        while moodle_token is None:
            moodle_url = input('URL of Moodle:   ')
            moodle_username = input('Username for Moodle:   ')
            moodle_password = getpass('Password for Moodle [no output]:   ')

            moodle_uri = urlparse(moodle_url)

            moodle_domain, moodle_path = self._split_moodle_uri(moodle_uri)

            try:
                moodle_token = login_helper.obtain_login_token(
                    moodle_username,
                    moodle_password,
                    moodle_domain,
                    moodle_path,
                    self.skip_cert_verify)

            except RequestRejectedError as error:
                print('Login Failed! (%s) Please try again.' % (error))
            except (ValueError, RuntimeError) as error:
                print(
                    'Error while communicating with the Moodle System!' +
                    ' (%s) Please try again.' % (error))

        # Saves the created token and the successful Moodle parameters.
        self.config_helper.set_property('token', moodle_token)
        self.config_helper.set_property('moodle_domain', moodle_domain)
        self.config_helper.set_property('moodle_path', moodle_path)

        return moodle_token

    def interactively_acquire_sso_token(self) -> str:
        """
        Walks the user through the receiving of a SSO token for the
        Moodle-System and saves it.
        @return: The Token for Moodle.
        """

        moodle_url = input('URL of Moodle:   ')

        moodle_uri = urlparse(moodle_url)

        moodle_domain, moodle_path = self._split_moodle_uri(moodle_uri)

        version = RequestHelper(moodle_domain, moodle_path, '',
                                self.skip_cert_verify
                                ).get_simple_moodle_version()

        if (version > 3.8):
            print('Between version 3.81 and 3.82 a change was added to' +
                  ' Moodle so that automatic copying of the SSO token' +
                  ' might not work. You can still try it, your version is: ' +
                  str(version))

        print(' If you want to copy the login-token manual,' +
              ' you will be guided through the manual copy process.')
        do_automatic = cutie.prompt_yes_or_no(
            'Do you want to try to receive the SSO token automatically?')

        print('Please log into Moodle on this computer and then visit' +
              ' the following address in your web browser: ')

        print('https://' + moodle_domain + moodle_path +
              'admin/tool/mobile/launch.php?service=' +
              'moodle_mobile_app&passport=12345&' +
              'urlscheme=http%3A%2F%2Flocalhost')

        if do_automatic:
            moodle_token = sso_token_receiver.receive_token()
        else:
            print('If you open the link in the browser, no web page should' +
                  ' load, instead an error will occur. Open the' +
                  ' developer console (press F12) and go to the Network Tab,' +
                  ' if there is no error, reload the web page.')

            print('Copy the link address of the website that could not be' +
                  ' loaded (right click, then click on Copy, then click' +
                  ' on copy link address).')

            token_address = input('Then insert the address here:   ')

            moodle_token = sso_token_receiver.extract_token(token_address)
            if(moodle_token is None):
                raise ValueError('Invalid URL!')

        # Saves the created token and the successful Moodle parameters.
        self.config_helper.set_property('token', moodle_token)
        self.config_helper.set_property('moodle_domain', moodle_domain)
        self.config_helper.set_property('moodle_path', moodle_path)

        return moodle_token

    def fetch_state(self) -> [Course]:
        """
        Gets the current status of the configured Moodle account and compares
        it with the last known status for changes. It does not change the
        known state, nor does it download the files.
        @return: List with detected changes
        """
        logging.debug('Fetching current Moodle State...')

        token = self.get_token()
        moodle_domain = self.get_moodle_domain()
        moodle_path = self.get_moodle_path()

        request_helper = RequestHelper(moodle_domain, moodle_path, token,
                                       self.skip_cert_verify)
        results_handler = ResultsHandler(request_helper)

        download_course_ids = self.get_download_course_ids()
        dont_download_course_ids = self.get_dont_download_course_ids()
        download_submissions = self.get_download_submissions()

        courses = []
        filtered_courses = []
        try:

            sys.stdout.write('\rDownload account information')
            sys.stdout.flush()

            userid, version = results_handler.fetch_userid_and_version()
            results_handler.setVersion(version)

            courses = results_handler.fetch_courses(userid)
            courses = self.add_options_to_courses(courses)

            assignments = results_handler.fetch_assignments()

            if(download_submissions):
                assignments = results_handler.fetch_submissions(
                    userid, assignments, download_course_ids,
                    dont_download_course_ids)

            index = 0
            for course in courses:
                index += 1

                skip = False
                if (not ResultsHandler._should_download_course(
                    course.id, download_course_ids,
                        dont_download_course_ids)):
                    skip = True

                # to limit the output to one line
                limits = shutil.get_terminal_size()

                shorted_course_name = course.fullname
                if (len(course.fullname) > 17):
                    shorted_course_name = course.fullname[:15] + '..'

                into = '\rDownload course information'
                if (skip):
                    into = '\r    Skip course information'

                status_message = (into + ' %3d/%3d [%17s|%6s]'
                                  % (index, len(courses),
                                      shorted_course_name,
                                      course.id))

                if (len(status_message) > limits.columns):
                    status_message = status_message[0:limits.columns]

                sys.stdout.write(status_message)
                sys.stdout.flush()

                if (skip):
                    continue

                course_assignments = assignments.get(course.id, [])
                course.files = results_handler.fetch_files(
                    course.id, course_assignments)

                filtered_courses.append(course)
            print("")

        except (RequestRejectedError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                'Error while communicating with the Moodle System! (%s)' % (
                    error))

        logging.debug('Checking for changes...')
        changes = self.recorder.changes_of_new_version(filtered_courses)

        # Filter changes
        changes = self._filter_courses(changes, download_course_ids,
                                       dont_download_course_ids,
                                       download_submissions)

        return changes

    def add_options_to_courses(self, courses: [Course]):
        """
        Updates a array of courses with its options
        """
        options_of_courses = self.get_options_of_courses()
        for course in courses:
            options = options_of_courses.get(str(course.id), None)
            if options is not None:
                course.overwrite_name_with = options.get(
                    'overwrite_name_with', None)
                course.create_file_structure = options.get(
                    'create_file_structure', True)

        return courses

    @staticmethod
    def _filter_courses(changes: [Course],
                        download_course_ids: [int],
                        dont_download_course_ids: [int],
                        download_submissions: bool) -> [Course]:
        """
        Filters the changes course list from courses that
        should not get downloaded
        @param download_course_ids: list of course ids
                                         that should be downloaded
        @param dont_download_course_ids: list of course ids
                                         that should not be downloaded
        @param download_submissions: boolean if submissions
                                    should be downloaded
        @return: filtered changes course list
        """

        filtered_changes = []

        for course in changes:
            if (not download_submissions):
                course_files = []
                for file in course.files:
                    if (file.content_type != "submission_file"):
                        course_files.append(file)
                course.files = course_files

            if(ResultsHandler._should_download_course(
                course.id, download_course_ids,
                dont_download_course_ids) and
                    len(course.files) > 0):
                filtered_changes.append(course)

        return filtered_changes

    @staticmethod
    def _split_moodle_uri(moodle_uri: str):
        """
        Splits a given Moodle-Uri into the domain and the installation path
        @return: moodle_domain, moodle_path as strings
        """

        moodle_domain = moodle_uri.netloc
        moodle_path = moodle_uri.path
        if not moodle_path.endswith('/'):
            moodle_path = moodle_path + "/"

        if(moodle_path == ''):
            moodle_path = '/'

        return moodle_domain, moodle_path

    def get_download_submissions(self) -> bool:
        # returns a stored bool of download_submissions
        try:
            return self.config_helper.get_property(
                'download_submissions')
        except ValueError:
            return False

    def get_download_course_ids(self) -> str:
        # returns a stored list of course ids hat should be downloaded
        try:
            return self.config_helper.get_property(
                'download_course_ids')
        except ValueError:
            return []

    def get_dont_download_course_ids(self) -> str:
        # returns a stored list of dont_download_course_ids
        try:
            return self.config_helper.get_property(
                'dont_download_course_ids')
        except ValueError:
            return []

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

    def get_options_of_courses(self) -> str:
        # returns a stored dictionary of options for courses
        try:
            return self.config_helper.get_property('options_of_courses')
        except ValueError:
            return {}
