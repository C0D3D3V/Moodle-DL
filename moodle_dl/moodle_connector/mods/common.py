from abc import ABCMeta, abstractmethod
from typing import Dict, List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.state_recorder import Course, File


class MoodleMod(metaclass=ABCMeta):
    """
    Common class for a Moodle module endpoint
    """

    def __init__(self, request_helper: RequestHelper, moodle_version: int, user_id: int, config: ConfigHelper):
        self.request_helper = request_helper
        self.version = moodle_version
        self.user_id = user_id
        self.config = config

    @abstractmethod
    async def fetch_module(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        pass

    @classmethod
    @abstractmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        """
        Return True if moodle-dl is configured to downloaded the given file
        This condition is applied after comparing the current status with the local database
        """
        # TODO: Make module download conditions more granular and more generally
        # (do not only filter "deleted" mod files but all?)
        pass
