from config_service.config_helper import ConfigHelper


class ConfigService:
    def __init__(self, config_helper: ConfigHelper):
        self.config_helper = config_helper

    def interactively_acquire_config(self):
        """
        Guides the user through the process of configuring the downloader
        for the courses to be downloaded and in what way
        """
        print('Not yet implemented')
