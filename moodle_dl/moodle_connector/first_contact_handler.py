import json

from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.state_recorder.course import Course


class FirstContactHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper):
        self.request_helper = request_helper
        # oldest supported Moodle version
        self.version = 2011120500

    def fetch_userid_and_version(self) -> str:
        """
        Ask the Moodle system for the user id.
        @return: the userid
        """
        result = self.request_helper.post_REST('core_webservice_get_site_info')

        if 'userid' not in result:
            raise RuntimeError('Error could not receive your user ID!')
        userid = result.get('userid', '')

        version = result.get('version', '2011120500')

        try:
            version = int(version.split('.')[0])
        except Exception as e:
            raise RuntimeError(f'Error could not parse version string: "{version}" Error: {e}')

        self.version = version
        return userid, version

    def fetch_courses(self, userid: str) -> [Course]:
        """
        Queries the Moodle system for all courses the user
        is enrolled in.
        @param userid: the user id
        @return: A list of courses
        """
        data = {'userid': userid}

        courses = self.request_helper.post_REST('core_enrol_get_users_courses', data)

        results = []
        for course in courses:
            results.append(Course(course.get('id', 0), course.get('fullname', '')))
            # We could also extract here the course summary and intro files
        return results

    def fetch_all_visible_courses(self, log_all_courses_to: str = None) -> [Course]:
        """
        Queries the Moodle system for all courses available on the system and returns:
        @return: A list of all visible courses
        """
        # API is only available since version 3.2
        if self.version < 2016120500:
            return []

        result = self.request_helper.post_REST('core_course_get_courses_by_field', timeout=1200)
        if log_all_courses_to is not None:
            with open(log_all_courses_to, 'w', encoding='utf-8') as log_file:
                log_file.write(json.dumps(result, indent=4, ensure_ascii=False))
        courses = result.get('courses', [])

        results = []
        for course in courses:
            if course.get('visible', 0) == 1:
                results.append(Course(course.get('id', 0), course.get('fullname', '')))
        return results

    def fetch_courses_info(self, course_ids: [int]) -> [Course]:
        """
        Queries the Moodle system for info about courses in a list.
        @param course_ids: A list of courses ids
        @return: A list of courses
        """
        # API is only available since version 3.2
        if len(course_ids) == 0 or self.version < 2016120500:
            return []

        data = {
            "field": "ids",
            "value": ",".join(list(map(str, course_ids))),
        }

        result = self.request_helper.post_REST('core_course_get_courses_by_field', data)
        courses = result.get('courses', [])

        results = []
        for course in courses:
            results.append(Course(course.get('id', 0), course.get('fullname', '')))
            # We could also extract here the course summary and intro files
        return results

    def fetch_sections(self, course_id: int) -> [{}]:
        """
        Fetches the Sections List for a course from the Moodle system
        @param course_id: The id of the requested course.
        @return: A List of all section dictionaries
        """
        data = {'courseid': course_id}
        if self.version >= 2015051100:
            data = {
                'courseid': course_id,
                'options[0][name]': 'excludemodules',
                'options[0][value]': 'true',
                'options[1][name]': 'excludecontents',
                'options[1][value]': 'true',
            }
        course_sections = self.request_helper.post_REST('core_course_get_contents', data)

        sections = []
        for section in course_sections:
            sections.append({"id": section.get("id"), "name": section.get("name")})

        return sections
