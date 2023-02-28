import logging

from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.types import Course, File


class DataMod(MoodleMod):
    MOD_NAME = 'data'
    MOD_PLURAL_NAME = 'databases'
    MOD_MIN_VERSION = 2015051100  # 2.9

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        return config.get_download_databases() or file.content_type != 'database_file'

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        databases = (
            await self.client.async_post(
                'mod_data_get_databases_by_courses', self.get_data_for_mod_entries_endpoint(courses)
            )
        ).get('databases', [])

        result = {}
        for database in databases:
            course_id = database.get('course', 0)
            database_files = database.get('introfiles', [])
            self.set_files_types_if_empty(database_files, 'database_introfile')

            database_intro = database.get('intro', '')
            if database_intro != '':
                database_files.append(
                    {
                        'filename': 'Database intro',
                        'filepath': '/',
                        'description': database_intro,
                        'type': 'description',
                    }
                )

            self.add_module(
                result,
                course_id,
                database.get('coursemodule', 0),
                {
                    'id': database.get('id', 0),
                    'name': database.get('name', 'db'),
                    'files': database_files,
                },
            )

        await self.add_database_files(result)
        return result

    async def add_database_files(self, databases: Dict[int, Dict[int, Dict]]):
        """
        Fetches for the databases list the database file entries.
        @param databases: Dictionary of all databases, indexed by courses, then module id
        """
        if not self.config.get_download_databases():
            return

        if self.version < 2017051500:  # 3.3
            return

        await self.run_async_load_function_on_mod_entries(databases, self.load_database_files)

    async def load_database_files(self, database: Dict):
        "Fetches for a given assign database the database files"
        data = {'databaseid': database.get('id', 0)}
        access = await self.client.async_post('mod_data_get_data_access_information', data)
        if not access.get('timeavailable', False):
            logging.debug("No access rights for database %d", database.get('id', 0))
            return

        data.update({'returncontents': 1})
        entries = await self.client.async_post('mod_data_get_entries', data)
        database['files'] += self._get_files_of_db_entries(entries)

    @classmethod
    def _get_files_of_db_entries(cls, entries: Dict) -> List:
        result = []
        for entry in entries.get('entries', []):
            for entry_content in entry.get('contents', []):
                for entry_file in entry_content.get('files', []):
                    filename = entry_file.get('filename', '')
                    if filename.startswith('thumb_'):
                        continue
                    cls.set_file_type_if_empty(entry_file, 'database_file')
                    result.append(entry_file)

        return result
