import os
import json

from pathlib import Path
from typing import Dict, List, Tuple

from moodle_dl.types import MoodleURL, MoodleDlOpts, DownloadOptions
from moodle_dl.utils import PathTools as PT


class ConfigHelper:
    "Handles the saving, formatting and loading of the local configuration."

    class NoConfigError(ValueError):
        """An Exception which gets thrown if config could not be loaded."""

        pass

    def __init__(self, storage_path: str):
        self._whole_config = {}
        self.storage_path = storage_path
        self.config_path = str(Path(storage_path) / 'config.json')

    def is_present(self) -> bool:
        # Tests if a configuration file exists
        return os.path.isfile(self.config_path)

    def load(self):
        # Opens the configuration file and parse it to a JSON object
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                config_raw = config_file.read()
                self._whole_config = json.loads(config_raw)
        except (IOError, OSError) as err_load:
            raise ConfigHelper.NoConfigError(f'Configuration could not be loaded from {self.config_path}\n{err_load!s}')

    def _save(self):
        config_formatted = json.dumps(self._whole_config, indent=4)
        # Saves the JSON object back to file
        with open(self.config_path, 'w+', encoding='utf-8') as config_file:
            config_file.write(config_formatted)

    def get_property(self, key: str) -> any:
        # return a property if configured
        try:
            return self._whole_config[key]
        except KeyError:
            raise ValueError(f'The {key}-Property is not yet configured!')

    def get_property_or(self, key: str, default: any = None) -> any:
        # return a property if configured
        try:
            return self._whole_config[key]
        except KeyError:
            return default

    def set_property(self, key: str, value: any):
        # sets a property in the JSON object
        self._whole_config.update({key: value})
        self._save()

    def remove_property(self, key):
        # removes a property from the JSON object
        self._whole_config.pop(key, None)
        #                           ^ behavior if the key is not present
        self._save()

    # ---------------------------- GETTERS ------------------------------------

    def get_download_submissions(self) -> str:
        # return a stored boolean if submissions should be downloaded
        return self.get_property_or('download_submissions', False)

    def get_download_descriptions(self) -> bool:
        # return a stored boolean if descriptions should be downloaded
        return self.get_property_or('download_descriptions', False)

    def get_download_links_in_descriptions(self) -> bool:
        # return a stored boolean if links in descriptions should be downloaded
        return self.get_property_or('download_links_in_descriptions', False)

    def get_download_databases(self) -> bool:
        # return a stored boolean if databases should be downloaded
        return self.get_property_or('download_databases', False)

    def get_download_forums(self) -> bool:
        # return a stored boolean if forums should be downloaded
        return self.get_property_or('download_forums', False)

    def get_download_quizzes(self) -> bool:
        # return a stored boolean if quizzes should be downloaded
        return self.get_property_or('download_quizzes', False)

    def get_download_lessons(self) -> bool:
        # return a stored boolean if lessons should be downloaded
        return self.get_property_or('download_lessons', False)

    def get_download_workshops(self) -> bool:
        # return a stored boolean if workshops should be downloaded
        return self.get_property_or('download_workshops', False)

    def get_userid_and_version(self) -> Tuple[str, int]:
        # return the userid and a version
        try:
            user_id = self.get_property('userid')
            version = int(self.get_property('version'))
            return user_id, version
        except ValueError:
            return None, None

    def get_do_not_ask_to_save_userid_and_version(self) -> bool:
        return self.get_property_or('do_not_ask_to_save_userid_and_version', False)

    def get_download_course_ids(self) -> str:
        # return a stored list of course ids hat should be downloaded
        return self.get_property_or('download_course_ids', [])

    def get_download_public_course_ids(self) -> str:
        # return a stored list of public course ids hat should be downloaded
        return self.get_property_or('download_public_course_ids', [])

    def get_token(self) -> str:
        # return a stored token
        try:
            return self.get_property('token')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_privatetoken(self) -> str:
        # return a stored privatetoken
        return self.get_property_or('privatetoken', None)

    def get_moodle_URL(self) -> MoodleURL:
        moodle_domain = self.get_moodle_domain()
        moodle_path = self.get_moodle_path()
        use_http = self.get_use_http()
        return MoodleURL(use_http, moodle_domain, moodle_path)

    def get_moodle_domain(self) -> str:
        # return a stored moodle_domain
        try:
            return self.get_property('moodle_domain')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_path(self) -> str:
        # return a stored moodle_path
        try:
            return self.get_property('moodle_path')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_options_of_courses(self) -> Dict:
        # return a stored dictionary of options for courses
        return self.get_property_or('options_of_courses', {})

    def get_dont_download_course_ids(self) -> List:
        # return a stored list of ids that should not be downloaded
        return self.get_property_or('dont_download_course_ids', [])

    def get_download_linked_files(self) -> bool:
        # return if linked files should be downloaded
        return self.get_property_or('download_linked_files', False)

    def get_download_domains_whitelist(self) -> List:
        # return a list of white listed domains that should be downloaded
        return self.get_property_or('download_domains_whitelist', [])

    def get_download_domains_blacklist(self) -> List:
        # return a list of black listed domains that should not be downloaded
        return self.get_property_or('download_domains_blacklist', [])

    def get_cookies_text(self) -> str:
        # return the text to the cookies file, if it exists
        cookies_path = PT.get_cookies_path(self.storage_path)
        if os.path.isfile(cookies_path):
            with open(cookies_path, 'r', encoding='utf-8') as cookie_file:
                return cookie_file.read()
        return None

    def get_yt_dlp_options(self) -> Dict:
        # return additional yt-dlp options
        return self.get_property_or('yt_dlp_options', {})

    def get_video_passwords(self) -> Dict:
        # return dict with passwords that get passed to yt-dlp
        return self.get_property_or('video_passwords', {})

    def get_external_file_downloaders(self) -> Dict:
        # return dict with configured external downloaders
        return self.get_property_or('external_file_downloaders', {})

    def get_exclude_file_extensions(self) -> Dict:
        # return a list of file extensions that should not be downloaded
        try:
            exclude_file_extensions = self.get_property('exclude_file_extensions')
            if not isinstance(exclude_file_extensions, list):
                exclude_file_extensions = [exclude_file_extensions]
            return exclude_file_extensions
        except ValueError:
            return []

    def get_download_also_with_cookie(self) -> Dict:
        # return if files for which a cookie is required should be downloaded
        return self.get_property_or('download_also_with_cookie', False)

    def get_download_options(self, opts: MoodleDlOpts) -> DownloadOptions:
        # return the option dictionary for downloading files
        return DownloadOptions(
            token=self.get_token(),
            download_linked_files=self.get_download_linked_files(),
            download_domains_whitelist=self.get_download_domains_whitelist(),
            download_domains_blacklist=self.get_download_domains_blacklist(),
            cookies_text=self.get_cookies_text(),
            yt_dlp_options=self.get_yt_dlp_options(),
            video_passwords=self.get_video_passwords(),
            external_file_downloaders=self.get_external_file_downloaders(),
            restricted_filenames=self.get_restricted_filenames(),
            global_opts=opts,
        )

    def get_restricted_filenames(self) -> Dict:
        # return the filenames should be restricted
        return self.get_property_or('restricted_filenames', False)

    def get_use_http(self) -> bool:
        # return a stored boolean if http should be used instead of https
        return self.get_property_or('use_http', False)

    # ---------------------------- SETTERS ------------------------------------

    def set_moodle_URL(self, moodle_url: MoodleURL):
        self.set_property('moodle_domain', moodle_url.domain)
        self.set_property('moodle_path', moodle_url.path)
        if moodle_url.use_http is True:
            self.set_property('use_http', moodle_url.use_http)
        else:
            if self.get_use_http():
                self.set_property('use_http', moodle_url.use_http)

    def set_tokens(self, moodle_token: str, moodle_privatetoken: str):
        self.set_property('token', moodle_token)
        if moodle_privatetoken is not None:
            self.set_property('privatetoken', moodle_privatetoken)
