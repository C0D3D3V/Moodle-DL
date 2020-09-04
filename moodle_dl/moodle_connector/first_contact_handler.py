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
            raise RuntimeError('Error could not parse version string: "%s" Error: %s' % (version, e))

        return userid, version

    def fetch_courses(self, userid: str) -> [Course]:
        """
        Queries the Moodle system for all courses the user
        is enrolled in.
        @param userid: the user id
        @return: A list of courses
        """
        data = {'userid': userid}

        result = self.request_helper.post_REST('core_enrol_get_users_courses', data)

        results = []
        for course in result:
            results.append(Course(course.get('id', 0), course.get('fullname', ''), []))
        return results
