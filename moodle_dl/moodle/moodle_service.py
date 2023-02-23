import base64
import logging
import re

from typing import List, Tuple
from urllib.parse import urlparse

from moodle_dl.config import ConfigHelper
from moodle_dl.database import StateRecorder
from moodle_dl.moodle.cookie_handler import CookieHandler
from moodle_dl.moodle.core_handler import CoreHandler
from moodle_dl.moodle.mods import fetch_mods_files, get_all_mods, get_all_mods_classes, get_mod_plurals
from moodle_dl.moodle.request_helper import RequestHelper
from moodle_dl.moodle.result_builder import ResultBuilder
from moodle_dl.types import Course, MoodleURL, MoodleDlOpts
from moodle_dl.utils import determine_ext


class MoodleService:
    def __init__(self, config: ConfigHelper, opts: MoodleDlOpts):
        self.config = config
        self.opts = opts

    @staticmethod
    def obtain_login_token(opts, username: str, password: str, moodle_url: MoodleURL) -> str:
        "Send the login credentials to the Moodle-System and extracts the resulting Login-Token"
        login_data = {'username': username, 'password': password, 'service': 'moodle_mobile_app'}
        response = RequestHelper(opts, moodle_url).get_login(login_data)

        if 'token' not in response:
            # = we didn't get an error page (checked by the RequestHelper) but
            # somehow we don't have the needed token
            raise RuntimeError('Invalid response received from the Moodle System!  No token was received.')

        if 'privatetoken' not in response:
            return response.get('token', ''), None
        return response.get('token', ''), response.get('privatetoken', '')

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

    async def fetch_state(self, database: StateRecorder) -> List[Course]:
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
            cookie_handler = CookieHandler(request_helper, version, self.opts)
            cookie_handler.check_and_fetch_cookies(privatetoken, user_id)

        courses = self.get_courses_list(core_handler, user_id)

        mods = get_all_mods(request_helper, version, user_id, database.get_last_timestamp_per_mod_module(), self.config)
        fetched_mods_files = await fetch_mods_files(mods, courses)
        course_cores = await core_handler.async_load_course_cores(courses)

        logging.debug('Combine API results...')
        ResultBuilder(moodle_url, version, get_mod_plurals()).add_files_to_courses(
            courses, course_cores, fetched_mods_files
        )

        logging.debug('Checking for changes...')
        changes = database.changes_of_new_version(courses)
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
