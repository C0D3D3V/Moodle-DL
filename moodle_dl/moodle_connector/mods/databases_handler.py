import logging

from typing import Dict, List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.mods import MoodleMod
from moodle_dl.state_recorder import Course, File


class DatabasesHandler(MoodleMod):
    MOD_NAME = 'data'
    MOD_MIN_VERSION = 2015051100  # 2.9

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        return config.get_download_databases() or file.content_type != 'database_file'

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        databases = await self.client.async_post(
            'mod_data_get_databases_by_courses', self.get_data_for_mod_entries_endpoint(courses)
        ).get('databases', [])

        result = {}
        for database in databases:
            # This is the instance id with which we can make the API queries.
            database_id = database.get('id', 0)
            database_name = database.get('name', 'db')
            database_intro = database.get('intro', '')
            database_coursemodule = database.get('coursemodule', 0)
            database_introfiles = database.get('introfiles', [])
            course_id = database.get('course', 0)

            # normalize
            for db_file in database_introfiles:
                file_type = db_file.get('type', '')
                if file_type is None or file_type == '':
                    db_file.update({'type': 'database_introfile'})

            if database_intro != '':
                # Add Intro File
                intro_file = {
                    'filename': 'Database intro',
                    'filepath': '/',
                    'description': database_intro,
                    'type': 'description',
                }
                database_introfiles.append(intro_file)

            database_entry = {
                database_coursemodule: {
                    'id': database_id,
                    'name': database_name,
                    'intro': database_intro,
                    'files': database_introfiles,
                }
            }

            course_dic = result.get(course_id, {})

            course_dic.update(database_entry)

            result.update({course_id: course_dic})

        return result

    def fetch_database_files(self, databases: Dict[int, Dict[int, Dict]]) -> Dict[int, Dict[int, Dict]]:
        """
        Fetches for the databases list of all courses the additionally
        entries. This is kind of waste of resources, because there
        is no API to get all entries at once
        @param databases: the dictionary of databases of all courses.
        @return: A Dictionary of all databases,
                 indexed by courses, then databases
        """
        if not self.config.get_download_databases():
            return databases

        # do this only if version is greater then 3.3
        # because mod_data_get_entries will fail
        if self.version < 2017051500:
            return databases

        counter = 0
        total = 0
        intro = '\rDownloading database information'

        # count total databases for nice console output
        for course_id in databases:
            for database_id in databases[course_id]:
                total += 1

        for course_id in databases:
            for database_id in databases[course_id]:
                counter += 1
                real_id = databases[course_id][database_id].get('id', 0)
                data = {'databaseid': real_id}

                access = await self.client.async_post('mod_data_get_data_access_information', data)

                if not access.get('timeavailable', False):
                    continue

                print(intro + f' {counter:3}/{total:3} [{course_id:6}|{real_id:6}]\033[K', end='')

                data.update({'returncontents': 1})

                entries = await self.client.async_post('mod_data_get_entries', data)

                database_files = self._get_files_of_db_entries(entries)
                databases[course_id][database_id]['files'] += database_files

        return databases

    @staticmethod
    def _get_files_of_db_entries(entries: Dict) -> List:
        result = []

        entries_list = entries.get('entries', [])

        for entry in entries_list:
            entry_contents = entry.get('contents', [])

            for entry_content in entry_contents:
                entry_files = entry_content.get('files', [])

                for entry_file in entry_files:
                    filename = entry_file.get('filename', '')
                    if filename.startswith('thumb_'):
                        continue
                    file_type = entry_file.get('type', '')
                    if file_type is None or file_type == '':
                        entry_file.update({'type': 'database_file'})
                    result.append(entry_file)

        return result
