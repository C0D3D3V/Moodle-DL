import logging

from typing import Dict, List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.mods import MoodleMod
from moodle_dl.state_recorder import Course, File


class PagesHandler(MoodleMod):
    MOD_NAME = 'page'
    MOD_MIN_VERSION = 2017051500  # 3.3

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        # TODO: Add download condition
        return True

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        pages = await self.client.async_post(
            'mod_page_get_pages_by_courses', self.get_data_for_mod_entries_endpoint(courses)
        ).get('pages', [])

        result = {}
        for page in pages:
            page_id = page.get('id', 0)
            page_name = page.get('name', 'unnamed page')
            page_intro = page.get('intro', '')
            page_content = page.get('content', '')
            page_course_module_id = page.get('coursemodule', 0)
            page_files = page.get('introfiles', [])
            page_files += page.get('contentfiles', [])
            course_id = page.get('course', 0)
            page_timemodified = page.get('timemodified', 0)

            # normalize
            for page_file in page_files:
                file_type = page_file.get('type', '')
                if file_type is None or file_type == '':
                    page_file.update({'type': 'page_file'})

            if page_intro != '':
                # Add intro file
                intro_file = {
                    'filename': 'Page intro',
                    'filepath': '/',
                    'description': page_intro,
                    'type': 'description',
                }
                page_files.append(intro_file)

            if page_content != '':
                # Add content file
                content_file = {
                    'filename': page_name,
                    'filepath': '/',
                    'html': page_content,
                    'filter_urls_during_search_containing': ['/mod_page/content/'],
                    'no_hash': True,
                    'type': 'html',
                    'timemodified': page_timemodified,
                    'filesize': len(page_content),
                }
                page_files.append(content_file)

            page_entry = {
                page_course_module_id: {
                    'id': page_id,
                    'name': page_name,
                    'intro': page_intro,
                    'files': page_files,
                }
            }

            course_dic = result.get(course_id, {})
            course_dic.update(page_entry)
            result.update({course_id: course_dic})

        return result
