import base64
import logging
import re
import sys

from getpass import getpass
from typing import List, Tuple
from urllib.parse import urlparse

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.cookie_handler import CookieHandler
from moodle_dl.moodle_connector.core_handler import CoreHandler
from moodle_dl.moodle_connector.mods import fetch_mods_files, get_all_mods, get_all_mods_classes, get_mod_plurals
from moodle_dl.moodle_connector.request_helper import RequestRejectedError, RequestHelper
from moodle_dl.moodle_connector.result_builder import ResultBuilder
from moodle_dl.state_recorder.state_recorder import StateRecorder
from moodle_dl.types import Course, MoodleURL
from moodle_dl.utils import Log, determine_ext, PathTools as PT


class MoodleService:
    def __init__(self, config: ConfigHelper, opts):
        self.config = config
        self.opts = opts
        self.recorder = StateRecorder(opts)

    def interactively_acquire_token(self, use_stored_url: bool = False) -> str:
        if self.opts.sso or self.opts.token is not None:
            self.interactively_acquire_sso_token(use_stored_url=use_stored_url)
        else:
            self.interactively_acquire_normal_token(use_stored_url=use_stored_url)

    def interactively_get_moodle_url(self, use_stored_url: bool) -> MoodleURL:
        if use_stored_url:
            return self.config.get_moodle_URL()

        url_ok = False
        while not url_ok:
            url_ok = True
            moodle_url = input('URL of Moodle:   ')

            use_http = False
            if moodle_url.startswith('http://'):
                Log.warning(
                    'Warning: You have entered an insecure URL! Are you sure that the Moodle is'
                    + ' not accessible via `https://`? All your data will be transferred'
                    + ' insecurely! If your Moodle is accessible via `https://`, then run'
                    + ' the process again using `https://` to protect your data.'
                )
                use_http = True
            elif not moodle_url.startswith('https://'):
                Log.error('The url of your moodle must start with `https://`')
                url_ok = False

        moodle_domain, moodle_path = self.split_moodle_url(moodle_url)
        return MoodleURL(use_http, moodle_domain, moodle_path)

    def interactively_acquire_normal_token(self, use_stored_url: bool = False) -> str:
        """
        Walks the user through executing a login into the Moodle-System to get
        the Token and saves it.
        @return: The Token for Moodle.
        """

        automated = False
        stop_automatic_generation = False
        if self.opts.username is not None and self.opts.password is not None:
            automated = True

        if not automated:
            print('[The following Credentials are not saved, it is only used temporarily to generate a login token.]')

        moodle_token = None
        while moodle_token is None or (stop_automatic_generation and automated):
            moodle_url = self.interactively_get_moodle_url(use_stored_url)

            if self.opts.username is not None:
                moodle_username = self.opts.username
                stop_automatic_generation = True
            else:
                moodle_username = input('Username for Moodle:   ')

            if self.opts.password is not None:
                moodle_password = self.opts.password
            else:
                moodle_password = getpass('Password for Moodle [no output]:   ')

            try:
                moodle_token, moodle_privatetoken = self.obtain_login_token(
                    moodle_username, moodle_password, moodle_url
                )

            except RequestRejectedError as error:
                Log.error(f'Login Failed! ({error}) Please try again.')
            except (ValueError, RuntimeError) as error:
                Log.error(f'Error while communicating with the Moodle System! ({error}) Please try again.')
            except ConnectionError as error:
                Log.error(str(error))

        if automated is True and moodle_token is None:
            sys.exit(1)

        self.config.set_tokens(moodle_token, moodle_privatetoken)
        self.config.set_moodle_URL(moodle_url)

        Log.success('Token successfully saved!')

        return moodle_token

    def obtain_login_token(self, username: str, password: str, moodle_url: MoodleURL) -> str:
        "Send the login credentials to the Moodle-System and extracts the resulting Login-Token"
        login_data = {'username': username, 'password': password, 'service': 'moodle_mobile_app'}
        response = RequestHelper(self.opts, moodle_url).get_login(login_data)

        if 'token' not in response:
            # = we didn't get an error page (checked by the RequestHelper) but
            # somehow we don't have the needed token
            raise RuntimeError('Invalid response received from the Moodle System!  No token was received.')

        if 'privatetoken' not in response:
            return response.get('token', ''), None
        return response.get('token', ''), response.get('privatetoken', '')

    def interactively_acquire_sso_token(self, use_stored_url: bool = False) -> str:
        """
        Walks the user through the receiving of a SSO token
        @return: The Token for Moodle.
        """

        moodle_url = self.interactively_get_moodle_url(use_stored_url)

        if self.opts.token is not None:
            moodle_token = self.opts.token
        else:
            Log.warning('Please use the Chrome browser for the following procedure')
            print('1. Log into your Moodle Account')
            print('2. Open the developer console (press F12) and go to the Network tab')
            print('3. Then visit the following URL in the same browser tab you have logged in:')

            print(
                moodle_url.url_base
                + 'admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=12345&urlscheme=moodledl'
            )
            print()
            print(
                'If you open the link, no web page should load, instead an error will occur.'
                + ' In the Network tab of the developer console you opened before there should be an error entry.'
            )

            print('The script expects a URL that looks something like this:')
            Log.info('moodledl://token=$apptoken')
            print(
                ' Where $apptoken looks random and "moodledl" can also be a different url scheme '
                + ' like "moodlemobile". In reality $apptoken is a Base64 string containing the token to access moodle.'
            )

            print(
                '4. Copy the link address of the website that could not be loaded'
                + ' (right click the list entry, then click on Copy, then click on copy link address)'
            )

            token_address = input('Then insert the link address here:   ')

            moodle_token, moodle_privatetoken = self.extract_token(token_address)
            if moodle_token is None:
                raise ValueError('Invalid URL!')

        self.config.set_tokens(moodle_token, moodle_privatetoken)
        self.config.set_moodle_URL(moodle_url)

        Log.success('Token successfully saved!')

        return moodle_token

    @staticmethod
    def extract_token(address: str) -> str:
        """
        Extracts a token from a returned URL
        See https://github.com/moodle/moodle/blob/master/admin/tool/mobile/launch.php for details
        """
        splitted = address.split('token=')

        if len(splitted) < 2:
            return None

        decoded = str(base64.b64decode(splitted[1]))

        splitted = decoded.split(':::')
        if len(splitted) < 2:
            return None

        token = re.sub(r'[^A-Za-z0-9]+', '', splitted[1])

        if len(splitted) < 3:
            return token, None

        secret_token = re.sub(r'[^A-Za-z0-9]+', '', splitted[2])
        return (token, secret_token)

    def get_courses_list(self, core_handler: CoreHandler, user_id: int) -> List[Course]:
        download_course_ids = self.config.get_download_course_ids()
        download_public_course_ids = self.config.get_download_public_course_ids()
        dont_download_course_ids = self.config.get_dont_download_course_ids()

        courses_list = core_handler.fetch_courses(user_id)
        courses = []
        # Filter unselected courses
        for course in courses_list:
            if MoodleService.should_download_course(course.id, download_course_ids, dont_download_course_ids):
                courses.append(course)

        public_courses_list = core_handler.fetch_courses_info(download_public_course_ids)
        courses.extend(public_courses_list)
        return courses

    def get_user_id_and_version(self, core_handler: CoreHandler) -> Tuple[int, int]:
        user_id, version = self.config.get_userid_and_version()
        if user_id is None or version is None:
            logging.info('Downloading account information')
            user_id, version = core_handler.fetch_userid_and_version()
            logging.debug('Detected moodle version: %d', version)
        else:
            core_handler.version = version
        return user_id, version

    async def fetch_state(self) -> List[Course]:
        """
        Fetch the current status of the configured Moodle account and compare it with the last known state
        It does not change the known state, nor does it download the files.
        @return: List with detected changes between the new and old state
        """
        logging.debug('Fetching current Moodle state...')
        token = self.config.get_token()
        privatetoken = self.config.get_privatetoken()
        moodle_url = self.config.get_moodle_URL()

        request_helper = RequestHelper(self.opts, moodle_url, token)
        core_handler = CoreHandler(request_helper)
        user_id, version = self.get_user_id_and_version(core_handler)

        cookie_handler = None
        if self.config.get_download_also_with_cookie():
            cookie_handler = CookieHandler(request_helper, version, self.opts.path)
            cookie_handler.check_and_fetch_cookies(privatetoken, user_id)

        courses = self.get_courses_list(core_handler, user_id)

        mods = get_all_mods(
            request_helper, version, user_id, self.recorder.get_last_timestamp_per_mod_module(), self.config
        )
        fetched_mods_files = await fetch_mods_files(mods, courses)
        course_cores = await core_handler.async_load_course_cores(courses)

        logging.debug('Combine API results...')
        result_builder = ResultBuilder(moodle_url, version, get_mod_plurals())
        result_builder.add_files_to_courses(courses, course_cores, fetched_mods_files)

        logging.debug('Checking for changes...')
        changes = self.recorder.changes_of_new_version(courses)
        changes = self.add_options_to_courses(changes)
        changes = self.filter_courses(changes, self.config, cookie_handler, courses)

        return changes

    def add_options_to_courses(self, courses: List[Course]):
        "Updates the courses with their options"
        options_of_courses = self.config.get_options_of_courses()
        for course in courses:
            options = options_of_courses.get(str(course.id), None)
            if options is not None:
                course.overwrite_name_with = options.get('overwrite_name_with', None)
                course.create_directory_structure = options.get('create_directory_structure', True)
                course.excluded_sections = options.get("excluded_sections", [])

        return courses

    @staticmethod
    def filter_courses(
        changes: List[Course],
        config: ConfigHelper,
        cookie_handler: CookieHandler = None,
        courses_list: List[Course] = None,
    ) -> List[Course]:
        """
        Filters the changes course list from courses that
        should not get downloaded
        @param config: ConfigHelper to obtain all the different filter configs
        @param cookie_handler: CookieHandler to check if the cookie is valid
        @param courses_list: A list of all courses that are available online
        @return: filtered changes course list
        """

        download_course_ids = config.get_download_course_ids()
        dont_download_course_ids = config.get_dont_download_course_ids()
        download_public_course_ids = config.get_download_public_course_ids()
        download_descriptions = config.get_download_descriptions()
        download_links_in_descriptions = config.get_download_links_in_descriptions()
        exclude_file_extensions = config.get_exclude_file_extensions()

        download_also_with_cookie = config.get_download_also_with_cookie()
        if cookie_handler is not None:
            download_also_with_cookie = cookie_handler.test_cookies()

        all_mods_classes = get_all_mods_classes()
        filtered_changes = []

        for course in changes:
            if not MoodleService.should_download_course(
                course.id, download_course_ids + download_public_course_ids, dont_download_course_ids
            ):
                # Filter courses that should not be downloaded
                continue

            if courses_list is not None:
                not_online = True
                # Filter courses that are not available online
                for online_course in courses_list:
                    if online_course.id == course.id:
                        not_online = False
                        break
                if not_online:
                    logging.warning('The Moodle course with id %d is no longer available online.', course.id)
                    continue

            course_files = []
            for file in course.files:
                # Filter files based on module options
                modules_conditions_met = True
                for mod in all_mods_classes:
                    if not mod.download_condition(config, file):
                        modules_conditions_met = False
                        break

                # Filter Files based on other options
                if (
                    modules_conditions_met
                    # Filter Description Files (except the forum posts)
                    and (
                        download_descriptions
                        or file.content_type != 'description'
                        or (
                            file.module_modname == 'forum'
                            and file.content_type == 'description'
                            and file.content_filename != 'Forum intro'
                        )
                    )
                    # Filter Files that requiere a Cookie
                    and (download_also_with_cookie or (not file.module_modname.startswith('cookie_mod-')))
                    # Exclude files whose file extension is blacklisted
                    and (determine_ext(file.content_filename) not in exclude_file_extensions)
                    # Exclude files that are in excluded sections
                    and (MoodleService.should_download_section(file.section_id, course.excluded_sections))
                ):
                    course_files.append(file)
            course.files = course_files

            # Filter Description URLs
            course_files = []
            for file in course.files:
                if not file.content_type == 'description-url':
                    course_files.append(file)

                elif download_links_in_descriptions:
                    add_description_url = True
                    for test_file in course.files:
                        if file.content_fileurl == test_file.content_fileurl:
                            if test_file.content_type != 'description-url':
                                # If a URL in a description also exists as a real link in the course,
                                # then ignore this URL
                                add_description_url = False
                                break
                            if file.module_id > test_file.module_id:
                                # Always use the link from the older description.
                                add_description_url = False
                                break

                    if add_description_url:
                        course_files.append(file)
            course.files = course_files

            if len(course.files) > 0:
                filtered_changes.append(course)

        return filtered_changes

    @staticmethod
    def should_download_course(
        course_id: int, download_course_ids: List[int], dont_download_course_ids: List[int]
    ) -> bool:
        "Checks if a course is in whitelist and not in blacklist"
        inBlacklist = course_id in dont_download_course_ids
        inWhitelist = course_id in download_course_ids or len(download_course_ids) == 0

        return inWhitelist and not inBlacklist

    @staticmethod
    def should_download_section(section_id: int, dont_download_sections_ids: List[int]) -> bool:
        "Checks if a section is not in blacklist"
        return section_id not in dont_download_sections_ids or len(dont_download_sections_ids) == 0

    @staticmethod
    def split_moodle_url(moodle_url: str) -> Tuple[str, str]:
        """
        Splits a given Moodle URL into the domain and the installation path
        @return: moodle_domain, moodle_path as strings
        """
        moodle_uri = urlparse(moodle_url)
        moodle_domain = moodle_uri.netloc
        moodle_path = moodle_uri.path
        if not moodle_path.endswith('/'):
            moodle_path = moodle_path + '/'

        if moodle_path == '':
            moodle_path = '/'

        return moodle_domain, moodle_path
