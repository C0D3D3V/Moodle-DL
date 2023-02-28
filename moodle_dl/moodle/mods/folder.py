from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.types import Course, File


class FolderMod(MoodleMod):
    MOD_NAME = 'folder'
    MOD_PLURAL_NAME = 'folders'
    MOD_MIN_VERSION = 2017051500  # 3.3

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        # TODO: Add download condition
        return True

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        folders = (
            await self.client.async_post(
                'mod_folder_get_folders_by_courses', self.get_data_for_mod_entries_endpoint(courses)
            )
        ).get('folders', [])

        result = {}
        for folder in folders:
            course_id = folder.get('course', 0)
            folder_files = folder.get('introfiles', [])
            folder_time_modified = folder.get('timemodified', 0)
            self.set_files_types_if_empty(folder_files, 'folder_file')

            folder_intro = folder.get('intro', '')
            if folder_intro != '':
                folder_files.append(
                    {
                        'filename': 'Folder intro',
                        'filepath': '/',
                        'description': folder_intro,
                        'timemodified': folder_time_modified,
                        'filter_urls_during_search_containing': ['/mod_folder/intro'],
                        'type': 'description',
                    }
                )

            self.add_module(
                result,
                course_id,
                folder.get('coursemodule', 0),
                {
                    'id': folder.get('id', 0),
                    'name': folder.get('name', 'unnamed folder'),
                    'timemodified': folder_time_modified,
                    'files': folder_files,
                },
            )

        return result
