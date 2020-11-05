import os
import json

from pathlib import Path


class ConfigHelper:
    """
    Handles the saving, formatting and loading of the local configuration.
    """

    def __init__(self, storage_path: str):
        """
        Initialize configuration file.

        Args:
            self: (todo): write your description
            storage_path: (str): write your description
        """
        self._whole_config = {}
        self.storage_path = storage_path
        self.config_path = str(Path(storage_path) / 'config.json')

    def is_present(self) -> bool:
        """
        Return true if the config file exists.

        Args:
            self: (todo): write your description
        """
        # Tests if a configuration file exists
        return os.path.isfile(self.config_path)

    def load(self):
        """
        Load config file.

        Args:
            self: (todo): write your description
        """
        # Opens the configuration file and parse it to a JSON object
        try:
            with open(self.config_path, 'r') as config_file:
                config_raw = config_file.read()
                self._whole_config = json.loads(config_raw)
        except IOError:
            raise ValueError('No config found!')

    def _save(self):
        """
        Save config to disk. json file.

        Args:
            self: (todo): write your description
        """
        # Saves the JSON object back to file
        with open(self.config_path, 'w+', encoding='utf-8') as config_file:
            config_formatted = json.dumps(self._whole_config, indent=4)
            config_file.write(config_formatted)

    def get_property(self, key: str) -> any:
        """
        Returns the value of a given value.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        # returns a property if configured
        try:
            return self._whole_config[key]
        except KeyError:
            raise ValueError('The %s-Property is not yet configured!' % (key))

    def set_property(self, key: str, value: any):
        """
        Sets a value in the given key.

        Args:
            self: (todo): write your description
            key: (str): write your description
            value: (todo): write your description
        """
        # sets a property in the JSON object
        self._whole_config.update({key: value})
        self._save()

    def remove_property(self, key):
        """
        Removes the value of a key.

        Args:
            self: (todo): write your description
            key: (str): write your description
        """
        # removes a property from the JSON object
        self._whole_config.pop(key, None)
        #                           ^ behavior if the key is not present
        self._save()

    # ---------------------------- GETTERS ------------------------------------

    def get_download_submissions(self) -> str:
        """
        Return the download submissions.

        Args:
            self: (todo): write your description
        """
        # returns a stored boolean if submissions should be downloaded
        try:
            return self.get_property('download_submissions')
        except ValueError:
            return False

    def get_download_descriptions(self) -> bool:
        """
        Returns : class : ~.

        Args:
            self: (todo): write your description
        """
        # returns a stored boolean if descriptions should be downloaded
        try:
            return self.get_property('download_descriptions')
        except ValueError:
            return False

    def get_download_links_in_descriptions(self) -> bool:
        """
        Returns the number of link links.

        Args:
            self: (todo): write your description
        """
        # returns a stored boolean if links in descriptions should be downloaded
        try:
            return self.get_property('download_links_in_descriptions')
        except ValueError:
            return False

    def get_download_databases(self) -> bool:
        """
        Get download download download download databases.

        Args:
            self: (todo): write your description
        """
        # returns a stored boolean if databases should be downloaded
        try:
            return self.get_property('download_databases')
        except ValueError:
            return False

    def get_download_forums(self) -> bool:
        """
        Returns true if download download download.

        Args:
            self: (todo): write your description
        """
        # returns a stored boolean if forums should be downloaded
        try:
            return self.get_property('download_forums')
        except ValueError:
            return False

    def get_download_course_ids(self) -> str:
        """
        Returns the course ids.

        Args:
            self: (todo): write your description
        """
        # returns a stored list of course ids hat should be downloaded
        try:
            return self.get_property('download_course_ids')
        except ValueError:
            return []

    def get_token(self) -> str:
        """
        Returns the token of token.

        Args:
            self: (todo): write your description
        """
        # returns a stored token
        try:
            return self.get_property('token')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_privatetoken(self) -> str:
        """
        Returns the value of the privileges.

        Args:
            self: (todo): write your description
        """
        # returns a stored privatetoken
        try:
            return self.get_property('privatetoken')
        except ValueError:
            return None

    def get_moodle_domain(self) -> str:
        """
        Returns the domain of the domain.

        Args:
            self: (todo): write your description
        """
        # returns a stored moodle_domain
        try:
            return self.get_property('moodle_domain')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_moodle_path(self) -> str:
        """
        Returns the path of the moodle file path

        Args:
            self: (todo): write your description
        """
        # returns a stored moodle_path
        try:
            return self.get_property('moodle_path')
        except ValueError:
            raise ValueError('Not yet configured!')

    def get_options_of_courses(self) -> str:
        """
        Gets the options for the options.

        Args:
            self: (todo): write your description
        """
        # returns a stored dictionary of options for courses
        try:
            return self.get_property('options_of_courses')
        except ValueError:
            return {}

    def get_dont_download_course_ids(self) -> str:
        """
        Returns course ids

        Args:
            self: (todo): write your description
        """
        # returns a stored list of ids that should not be downloaded
        try:
            return self.get_property('dont_download_course_ids')
        except ValueError:
            return []

    def get_download_linked_files(self) -> {}:
        """
        Gets the download link.

        Args:
            self: (todo): write your description
        """
        # returns if linked files should be downloaded
        try:
            return self.get_property('download_linked_files')
        except ValueError:
            return False

    def get_download_also_with_cookie(self) -> {}:
        """
        Returns the download cookie.

        Args:
            self: (todo): write your description
        """
        # returns if files for which a cookie is required should be downloaded.
        try:
            return self.get_property('download_also_with_cookie')
        except ValueError:
            return False

    def get_download_options(self) -> {}:
        """
        Get download options.

        Args:
            self: (todo): write your description
        """
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

        return options

    def get_restricted_filenames(self) -> {}:
        """
        Returns a list of filenames. filenames.

        Args:
            self: (todo): write your description
        """
        # returns the filenames should be restricted
        try:
            return self.get_property('restricted_filenames')
        except ValueError:
            return False
