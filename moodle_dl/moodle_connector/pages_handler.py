from moodle_dl.state_recorder.course import Course
from moodle_dl.moodle_connector.request_helper import RequestHelper


class PagesHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_pages(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Pages List for all courses from the
        Moodle system
        @return: A Dictionary of all pages,
                 indexed by courses, then pages
        """
        # do this only if version is greater then 3.3
        # because mod_page_get_pages_by_courses will fail
        if self.version < 2017051500:
            return {}

        print('\rDownloading pages information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        pages_result = self.request_helper.post_REST('mod_page_get_pages_by_courses', extra_data)

        pages = pages_result.get('pages', [])

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
