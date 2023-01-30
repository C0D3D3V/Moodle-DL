import logging

from typing import Dict, List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.mods import MoodleMod
from moodle_dl.state_recorder import Course, File


class FoldersHandler(MoodleMod):
    MOD_NAME = 'folder'
    MOD_MIN_VERSION = 2017051500  # 3.3

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        # TODO: Add download condition
        return True

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        folders = await self.client.async_post(
            'mod_folder_get_folders_by_courses', self.get_data_for_mod_entries_endpoint(courses)
        ).get('folders', [])

        result = {}
        for folder in folders:
            folder_id = folder.get('id', 0)
            folder_name = folder.get('name', 'unnamed folder')
            folder_intro = folder.get('intro', '')
            folder_course_module_id = folder.get('coursemodule', 0)
            folder_files = folder.get('introfiles', [])
            course_id = folder.get('course', 0)
            folder_timemodified = folder.get('timemodified', 0)

            # normalize
            for folder_file in folder_files:
                file_type = folder_file.get('type', '')
                if file_type is None or file_type == '':
                    folder_file.update({'type': 'folder_file'})

            if folder_intro != '':
                # Add intro file
                intro_file = {
                    'filename': 'Folder intro',
                    'filepath': '/',
                    'description': folder_intro,
                    'timemodified': folder_timemodified,
                    'filter_urls_during_search_containing': ['/mod_folder/intro'],
                    'type': 'description',
                }
                folder_files.append(intro_file)

            folder_entry = {
                folder_course_module_id: {
                    'id': folder_id,
                    'name': folder_name,
                    'intro': folder_intro,
                    'files': folder_files,
                }
            }

            course_dic = result.get(course_id, {})
            course_dic.update(folder_entry)
            result.update({course_id: course_dic})

        return result
