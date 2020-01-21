import json
import os


class ConfigHelper:
    """
    Handles the saving, formatting and loading of the local configuration.
    """

    def __init__(self, storage_path: str):
        self._whole_config = {}
        self.config_path = os.path.join(storage_path, "config.json")

    def is_present(self) -> bool:
        # Tests if a configuration file exists
        return os.path.isfile(self.config_path)

    def load(self):
        # Opens the conficuration file and parse it to a json object
        try:
            with open(self.config_path, 'r') as f:
                config_raw = f.read()
                self._whole_config = json.loads(config_raw)
        except IOError:
            raise ValueError('No config found!')

    def _save(self):
        # Saves the json object back to file
        with open(self.config_path, 'w+') as f:
            config_formatted = json.dumps(self._whole_config, indent=4)
            f.write(config_formatted)

    def get_property(self, key: str) -> any:
        # returns a property if configured
        try:
            return self._whole_config[key]
        except KeyError:
            raise ValueError('The %s-Property is not yet configured!' % (key))

    def set_property(self, key: str, value: any):
        # sets a property in the json object
        self._whole_config.update({key: value})
        self._save()

    def remove_property(self, key):
        # removes a property from the json object
        self._whole_config.pop(key, None)
        #                           ^ behaviour if the key is not present
        self._save()
