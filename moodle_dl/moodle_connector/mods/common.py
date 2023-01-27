from abc import ABCMeta, abstractmethod
from typing import Dict, List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.state_recorder import Course


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
