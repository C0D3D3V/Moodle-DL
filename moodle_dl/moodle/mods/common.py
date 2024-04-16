import asyncio
import logging
import math
from abc import ABCMeta, abstractmethod
from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.request_helper import RequestHelper
from moodle_dl.types import Course, File
from moodle_dl.utils import PathTools as PT
from moodle_dl.utils import get_nested, run_with_final_message


class MoodleMod(metaclass=ABCMeta):
    """
    Common class for a Moodle module endpoint
    """

    MOD_NAME = None
    MOD_PLURAL_NAME = None
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

    async def fetch_mod_entries(
        self, courses: List[Course], core_contents: Dict[int, List[Dict]]
    ) -> Dict[int, Dict[int, Dict]]:
        if self.version < self.MOD_MIN_VERSION:
            return {}

        result = await self.real_fetch_mod_entries(courses, core_contents)
        logging.info('Loaded all %s', self.MOD_PLURAL_NAME)
        return result

    def get_indexed_ids_of_mod_instances(self, mod_instances: Dict[int, Dict[int, Dict]]):
        """
        @param mod_instances: Dictionary of all mod instanced, indexed by courses, then module id
        """
        mod_instances_ids = {}
        idx = 0
        for _, modules in mod_instances.items():
            for _, mod in modules.items():
                mod_instances_ids[str(idx)] = mod['id']
                idx += 1
        return mod_instances_ids

    def get_data_for_mod_entries_endpoint(self, courses: List[Course]):
        # Create a dictionary with all the courses we want to request
        course_ids = {}
        for idx, course in enumerate(courses):
            course_ids[str(idx)] = course.id
        return {'courseids': course_ids}

    @abstractmethod
    async def real_fetch_mod_entries(
        self, courses: List[Course], core_contents: Dict[int, List[Dict]]
    ) -> Dict[int, Dict[int, Dict]]:
        """
        Fetches the mod entries for all courses
        @return: Dictionary of all course modules of that mod type, indexed by course id, then course module id
        """
        pass

    @staticmethod
    def set_props_of_file(file_dict: Dict, **props):
        for prop, value in props.items():
            if (
                file_dict.get(prop) is not None
                and file_dict[prop] != ''
                and file_dict[prop] != value
                and (prop != 'filepath' or file_dict[prop] != '/')
            ):
                logging.debug('Overwriting %r with %r of file %s', prop, value, file_dict)
            file_dict[prop] = value

    @classmethod
    def set_props_of_files(cls, files: List[Dict], **props):
        for file_dict in files:
            cls.set_props_of_file(file_dict, **props)

    @staticmethod
    def set_base_file_path_of_file(file_dict: Dict, base_file_path: str):
        old_file_path = file_dict.get('filepath')
        if old_file_path is not None and old_file_path != '/':
            file_dict['filepath'] = PT.make_path(base_file_path, old_file_path.strip('/'))
        else:
            file_dict['filepath'] = base_file_path

    @classmethod
    def set_base_file_path_of_files(cls, files: List[Dict], base_file_path: str):
        for file_dict in files:
            cls.set_base_file_path_of_file(file_dict, base_file_path)

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

        if total_entries == 0:
            return
        ctr_digits = int(math.log10(total_entries)) + 1

        async_features = []
        for course_id, entries_in_course in entries.items():
            for module_id, entry in entries_in_course.items():
                ctr += 1

                # Example: [ 5/16] Loaded assign 123 in course 456 "Assignment name"
                loaded_message = (
                    f'[%(ctr){ctr_digits}d/%(total){ctr_digits}d] Loaded %(mod_name)s %(module_id)d'
                    + ' in course %(course_id)d "%(module_name)s"'
                )

                async_features.append(
                    run_with_final_message(
                        load_function,
                        entry,
                        loaded_message,
                        {
                            'ctr': ctr,
                            'total': total_entries,
                            'mod_name': cls.MOD_NAME,
                            'module_id': module_id,
                            'course_id': course_id,
                            'module_name': entry.get('name', ''),
                        },
                    )
                )

        await asyncio.gather(*async_features)

    @classmethod
    async def run_async_collect_function_on_list(
        cls,
        entries: List[Dict],
        collect_function,
        collect_kind: str,
        format_mapping: Dict,
    ) -> List[Dict]:
        "Runs a collect function on every entry in a given entries list"
        total_entries = len(entries)
        if total_entries == 0:
            return []
        ctr_digits = int(math.log10(total_entries)) + 1

        async_features = []
        for ctr, entry in enumerate(entries):
            # Example: [ 5/16] Loaded forum discussion 123 "Good discussion"
            loaded_message = (
                f'[%(ctr){ctr_digits}d/%(total){ctr_digits}d] Loaded %(mod_name)s %(collect_kind)s'
                + ' %(collect_id)d "%(collect_name)s"'
            )

            async_features.append(
                run_with_final_message(
                    collect_function,
                    entry,
                    loaded_message,
                    {
                        'ctr': ctr + 1,
                        'total': total_entries,
                        'mod_name': cls.MOD_NAME,
                        'collect_kind': collect_kind,
                        'collect_id': get_nested(entry, format_mapping['collect_id'], 0),
                        'collect_name': get_nested(entry, format_mapping['collect_name'], ''),
                    },
                )
            )

        result = []
        for feature_result in await asyncio.gather(*async_features):
            if isinstance(feature_result, list):
                result.extend(feature_result)
            elif feature_result is not None:
                result.append(feature_result)
        return result

    @staticmethod
    def get_module_in_core_contents(course_id: int, module_id: int, core_contents: Dict[int, List[Dict]]) -> Dict:
        course_section = core_contents.get(course_id, [])
        for section in course_section:
            for module in section.get('modules', []):
                if module.get('id', 0) == module_id:
                    return module
        return {}

    @staticmethod
    def add_module(result: Dict, course_id: int, module_id: int, module: Dict):
        if course_id not in result:
            result[course_id] = {}
        if module_id in result[course_id]:
            logging.warning('Got duplicated module %s in course %s', module_id, course_id)
        result[course_id][module_id] = module
