import os
import json

from pathlib import Path


class ConfigHelper:
    """
    Handles the saving, formatting and loading of the local configuration.
    """

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
            with open(self.config_path, 'r') as config_file:
                config_raw = config_file.read()
                self._whole_config = json.loads(config_raw)
        except IOError:
            raise ValueError('No config found!')

    def _save(self):
        # Saves the JSON object back to file
        with open(self.config_path, 'w+', encoding='utf-8') as config_file:
            config_formatted = json.dumps(self._whole_config, indent=4)
            config_file.write(config_formatted)

    def get_property(self, key: str) -> any:
        # returns a property if configured
        try:
            return self._whole_config[key]
        except KeyError:
            raise ValueError('The %s-Property is not yet configured!' % (key))

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
        # returns a stored boolean if submissions should be downloaded
        try:
            return self.get_property('download_submissions')
        except ValueError:
            return False

    def get_download_descriptions(self) -> bool:
        # returns a stored boolean if descriptions should be downloaded
        try:
            return self.get_property('download_descriptions')
        except ValueError:
            return False

    def get_download_links_in_descriptions(self) -> bool:
        # returns a stored boolean if links in descriptions should be downloaded
        try:
            return self.get_property('download_links_in_descriptions')
        except ValueError:
            return False

    def get_download_databases(self) -> bool:
        # returns a stored boolean if databases should be downloaded
        try:
            return self.get_property('download_databases')
        except ValueError:
            return False

    def get_download_forums(self) -> bool:
        # returns a stored boolean if forums should be downloaded
        try:
            return self.get_property('download_forums')
        except ValueError:
            return False

    def get_download_quizzes(self) -> bool:
        # returns a stored boolean if quizzes should be downloaded
        try:
            return self.get_property('download_quizzes')
        except ValueError:
            return False

    def get_userid_and_version(self) -> (str, int):
        # returns the userid and a version
        try:
            userid = self.get_property('userid')
            version = int(self.get_property('version'))
            return userid, version
        except ValueError:
            return None, None

    def get_download_course_ids(self) -> str:
        # returns a stored list of course ids hat should be downloaded
        try:
            return self.get_property('download_course_ids')
        except ValueError:
            return []

    def get_download_public_course_ids(self) -> str:
        # returns a stored list of public course ids hat should be downloaded
        try:
            return self.get_property('download_public_course_ids')
        except ValueError:
            return []

    def get_token(self) -> str:
        # returns a stored token
        try:
            return self.get_property('token')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_privatetoken(self) -> str:
        # returns a stored privatetoken
        try:
            return self.get_property('privatetoken')
        except ValueError:
            return None

    def get_moodle_domain(self) -> str:
        # returns a stored moodle_domain
        try:
            return self.get_property('moodle_domain')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_path(self) -> str:
        # returns a stored moodle_path
        try:
            return self.get_property('moodle_path')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_options_of_courses(self) -> str:
        # returns a stored dictionary of options for courses
        try:
            return self.get_property('options_of_courses')
        except ValueError:
            return {}

    def get_dont_download_course_ids(self) -> str:
        # returns a stored list of ids that should not be downloaded
        try:
            return self.get_property('dont_download_course_ids')
        except ValueError:
            return []

    def get_download_linked_files(self) -> {}:
        # returns if linked files should be downloaded
        try:
            return self.get_property('download_linked_files')
        except ValueError:
            return False

    def get_exclude_file_extensions(self) -> {}:
        # returns a list of file extensions that should not be downloaded
        try:
            exclude_file_extensions = self.get_property('exclude_file_extensions')
            if not type(exclude_file_extensions) is list:
                exclude_file_extensions = [exclude_file_extensions]
            return exclude_file_extensions
        except ValueError:
            return []

    def get_download_also_with_cookie(self) -> {}:
        # returns if files for which a cookie is required should be downloaded
        try:
            return self.get_property('download_also_with_cookie')
        except ValueError:
            return False

    def get_download_options(self) -> {}:
        # returns the option dictionary for downloading files
        options = {}
        try:
            options.update({'download_linked_files': self.get_property('download_linked_files')})
        except ValueError:
            options.update({'download_linked_files': False})

        try:
            options.update({'download_domains_whitelist': self.get_property('download_domains_whitelist')})
        except ValueError:
            options.update({'download_domains_whitelist': []})

        try:
            options.update({'download_domains_blacklist': self.get_property('download_domains_blacklist')})
        except ValueError:
            options.update({'download_domains_blacklist': []})

        cookies_path = str(Path(self.storage_path) / 'Cookies.txt')
        if os.path.exists(cookies_path):
            options.update({'cookies_path': cookies_path})
        else:
            options.update({'cookies_path': None})

        try:
            options.update({'youtube_dl_options': self.get_property('youtube_dl_options')})
        except ValueError:
            options.update({'youtube_dl_options': {}})

        try:
            options.update({'videopasswords': self.get_property('videopasswords')})
        except ValueError:
            options.update({'videopasswords': {}})

        try:
            options.update({'external_file_downloaders': self.get_property('external_file_downloaders')})
        except ValueError:
            options.update({'external_file_downloaders': {}})

        return options

    def get_restricted_filenames(self) -> {}:
        # returns the filenames should be restricted
        try:
            return self.get_property('restricted_filenames')
        except ValueError:
            return False

    def get_use_http(self) -> bool:
        # returns a stored boolean if http should be used instead of https
        try:
            return self.get_property('use_http')
        except ValueError:
            return False
