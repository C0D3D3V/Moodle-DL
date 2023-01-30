import logging

from abc import ABCMeta, abstractmethod
from typing import Dict, List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector import RequestHelper
from moodle_dl.state_recorder import Course, File


class MoodleMod(metaclass=ABCMeta):
    """
    Common class for a Moodle module endpoint
    """

    MOD_NAME = None
    MOD_MIN_VERSION = None

    def __init__(
        self,
        request_helper: RequestHelper,
        moodle_version: int,
        user_id: int,
        last_timestamps: Dict[str, Dict[int, int]],
        config: ConfigHelper,
    ):
        """
        @param last_timestamps: A Dict per mod of timestamps per course module id,
                                prevents downloading older content of a corse module
        """

        self.client = request_helper
        self.version = moodle_version
        self.user_id = user_id
        self.last_timestamps = last_timestamps
        self.config = config

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

    async def fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        if self.version < self.MOD_MIN_VERSION:
            return {}

        logging.info('Loading %s mod entries...', self.MOD_NAME)

        return self.real_fetch_mod_entries(courses)

    def get_data_for_mod_entries_endpoint(self, courses: List[Course]):
        # Create a dictionary with all the courses we want to request
        course_ids = {}
        for index, course in enumerate(courses):
            course_ids.update({str(index): course.id})
        return {'courseids': course_ids}

    @abstractmethod
    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        """
        Fetches the mod entries for all courses
        @return: A dictionary of all course modules of that mod type, indexed by course id, then course module id
        """
        pass
