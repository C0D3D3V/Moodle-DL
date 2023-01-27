from typing import Dict, List

from moodle_dl.config_service.config_helper import ConfigHelper
from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.state_recorder.course import Course


class MoodleMod:
    """
    Common class for a Moodle module endpoint
    """

    def __init__(self, request_helper: RequestHelper, moodle_version: int, config: ConfigHelper):
        self.request_helper = request_helper
        self.version = moodle_version
        self.config = config

    async def fetch_module(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        raise NotImplementedError('This method must be implemented by subclasses')
