from moodle_dl.state_recorder.course import Course
from moodle_dl.moodle_connector.request_helper import RequestHelper


class FoldersHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_folders(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Folder List for all courses from the
        Moodle system
        @return: A Dictionary of all folders,
                 indexed by courses, then folders
        """
        # do this only if version is greater then 3.3
        # because mod_folder_get_folders_by_courses will fail
        if self.version < 2017051500:
            return {}

        print('\rDownloading folders information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        folders_result = self.request_helper.post_REST('mod_folder_get_folders_by_courses', extra_data)

        folders = folders_result.get('folders', [])

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
