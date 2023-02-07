from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.types import Course, File


class PageMod(MoodleMod):
    MOD_NAME = 'page'
    MOD_PLURAL_NAME = 'pages'
    MOD_MIN_VERSION = 2017051500  # 3.3

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        # TODO: Add download condition
        return True

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        pages = (
            await self.client.async_post(
                'mod_page_get_pages_by_courses', self.get_data_for_mod_entries_endpoint(courses)
            )
        ).get('pages', [])

        result = {}
        for page in pages:
            course_id = page.get('course', 0)
            page_name = page.get('name', 'unnamed page')
            page_content = page.get('content', '')

            page_files = page.get('introfiles', [])
            page_files += page.get('contentfiles', [])
            self.set_files_types_if_empty(page_files, 'page_file')

            page_intro = page.get('intro', '')
            if page_intro != '':
                page_files.append(
                    {
                        'filename': 'Page intro',
                        'filepath': '/',
                        'description': page_intro,
                        'type': 'description',
                    }
                )

            if page_content != '':
                page_files.append(
                    {
                        'filename': page_name,
                        'filepath': '/',
                        'html': page_content,
                        'filter_urls_during_search_containing': ['/mod_page/content/'],
                        'no_hash': True,
                        'type': 'html',
                        'timemodified': page.get('timemodified', 0),
                        'filesize': len(page_content),
                    }
                )

            self.add_module(
                result,
                course_id,
                page.get('coursemodule', 0),
                {
                    'id': page.get('id', 0),
                    'name': page_name,
                    'files': page_files,
                },
            )

        return result
