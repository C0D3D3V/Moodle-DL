from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.state_recorder.course import Course


class DatabasesHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_databases(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Databases List for all courses from the
        Moodle system
        @return: A Dictionary of all databases,
                 indexed by courses, then databases
        """
        # do this only if version is greater then 2.9
        # because mod_data_get_databases_by_courses will fail
        if self.version < 2015051100:
            return {}

        print('\rDownloading databases information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        databases_result = self.request_helper.post_REST('mod_data_get_databases_by_courses', extra_data)

        databases = databases_result.get('databases', [])

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

    def fetch_database_files(self, databases: {int: {int: {}}}) -> {int: {int: {}}}:
        """
        Fetches for the databases list of all courses the additionally
        entries. This is kind of waste of resources, because there
        is no API to get all entries at once
        @param databases: the dictionary of databases of all courses.
        @param download_course_ids: ids of courses for that should
                                    be downloaded
        @return: A Dictionary of all databases,
                 indexed by courses, then databases
        """
        # do this only if version is greater then 3.3
        # because mod_data_get_entries will fail
        if self.version < 2017051500:
            return databases

        counter = 0
        total = 0

        # count total assignments for nice console output
        for course_id in databases:
            for database_id in databases[course_id]:
                total += 1

        for course_id in databases:
            for database_id in databases[course_id]:
                counter += 1
                real_id = databases[course_id][database_id].get('id', 0)
                data = {'databaseid': real_id}

                access = self.request_helper.post_REST('mod_data_get_data_access_information', data)

                if not access.get('timeavailable', False):
                    continue

                data.update({'returncontents': 1})

                entries = self.request_helper.post_REST('mod_data_get_entries', data)

                database_files = self._get_files_of_db_entries(entries)
                databases[course_id][database_id]['files'] += database_files

        return databases

    @staticmethod
    def _get_files_of_db_entries(entries: {}) -> []:
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
