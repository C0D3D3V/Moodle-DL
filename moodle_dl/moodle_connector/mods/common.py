import asyncio
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

        result = self.real_fetch_mod_entries(courses)
        logging.info('Loaded %s mod entries', self.MOD_NAME)
        return result

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
        @return: Dictionary of all course modules of that mod type, indexed by course id, then course module id
        """
        pass

    @staticmethod
    def set_files_types_if_empty(files: [Dict], type_to_set: str):
        for file_dict in files:
            file_type = file_dict.get('type', '')
            if file_type is None or file_type == '':
                file_dict['type'] = type_to_set

    @staticmethod
    async def run_with_final_message(load_function, entry: Dict, message: str, *format_args):
        await load_function(entry)
        logging.info(message, *format_args)

    @classmethod
    async def run_async_load_function_on_mod_entries(cls, entries: Dict[int, Dict[int, Dict]], load_function):
        """
        Runs a load function on every module in a given entries list
        @param entries: Dictionary of all module entries, indexed by courses, then module id
        """
        ctr = 0
        total_entries = 0
        for _, entries_in_course in entries.items():
            total_entries += len(entries_in_course)

        async_features = []
        for course_id, entries_in_course in entries.items():
            for module_id, entry in entries_in_course.items():
                ctr += 1

                # Example: [5/16] Loaded assign 123 in course 456 "Assignment name"
                loaded_message = '[%3d/%-3d] Loaded %10s %-6d in course %-6d "%s"'

                async_features.append(
                    cls.run_with_final_message(
                        load_function,
                        entry,
                        loaded_message,
                        ctr,
                        total_entries,
                        cls.MOD_NAME,
                        course_id,
                        module_id,
                        entry.get('name', ''),
                    )
                )

        await asyncio.gather(*async_features)
