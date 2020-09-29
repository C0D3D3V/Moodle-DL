from moodle_dl.state_recorder.course import Course
from moodle_dl.moodle_connector.request_helper import RequestHelper


class AssignmentsHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_assignments(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Assignments List for all courses from the
        Moodle system
        @return: A Dictionary of all assignments,
                 indexed by courses, then assignment
        """
        # do this only if version is greater then 2.4
        # because mod_assign_get_assignments will fail
        if self.version < 2012120300:
            return {}

        print('\rDownloading assignments information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        assign_result = self.request_helper.post_REST('mod_assign_get_assignments', extra_data)

        assign_courses = assign_result.get('courses', [])

        result = {}
        for assign_course in assign_courses:
            course_id = assign_course.get('id', 0)
            course_assigns = {}
            course_assign_objs = assign_course.get('assignments', [])

            for course_assign_obj in course_assign_objs:
                assign_id = course_assign_obj.get('cmid', 0)
                assign_rid = course_assign_obj.get('id', 0)
                assign_files = []
                assign_files += course_assign_obj.get('introfiles', [])
                assign_files += course_assign_obj.get('introattachments', [])

                # normalize
                for assign_file in assign_files:
                    file_type = assign_file.get('type', '')
                    if file_type is None or file_type == '':
                        assign_file.update({'type': 'assign_file'})

                course_assigns.update({assign_id: {'id': assign_rid, 'files': assign_files}})

            result.update({course_id: course_assigns})

        return result

    def fetch_submissions(self, userid: int, assignments: {int: {int: {}}}) -> {int: {int: {}}}:
        """
        Fetches for the assignments list of all courses the additionally
        submissions. This is kind of waste of resources, because there
        is no API to get all submissions at once
        @param userid: the user id.
        @param assignments: the dictionary of assignments of all courses.
        @return: A Dictionary of all assignments,
                 indexed by courses, then assignment
        """
        # do this only if version is greater then 3.1
        # because mod_assign_get_submission_status will fail
        if self.version < 2016052300:
            return assignments

        intro = '\rDownloading submission information'

        counter = 0
        total = 0

        # count total assignments for nice console output
        for course_id in assignments:
            for assignment_id in assignments[course_id]:
                total += 1

        for course_id in assignments:
            for assignment_id in assignments[course_id]:
                counter += 1
                real_id = assignments[course_id][assignment_id].get('id', 0)
                data = {'userid': userid, 'assignid': real_id}

                print(intro + ' %3d/%3d [%6s|%6s]\033[K' % (counter, total, course_id, real_id), end='')

                submission = self.request_helper.post_REST('mod_assign_get_submission_status', data)

                submission_files = self._get_files_of_submission(submission)
                assignments[course_id][assignment_id]['files'] += submission_files

        return assignments

    @staticmethod
    def _get_files_of_submission(submission: {}) -> []:
        result = []
        # get own submissions
        lastattempt = submission.get('lastattempt', {})
        l_submission = lastattempt.get('submission', {})
        l_teamsubmission = lastattempt.get('teamsubmission', {})

        # get teachers feedback
        feedback = submission.get('feedback', {})

        result += AssignmentsHandler._get_files_of_plugins(l_submission)
        result += AssignmentsHandler._get_files_of_plugins(l_teamsubmission)
        result += AssignmentsHandler._get_files_of_plugins(feedback)

        return result

    @staticmethod
    def _get_files_of_plugins(obj: {}) -> []:
        result = []
        plugins = obj.get('plugins', [])

        for plugin in plugins:
            fileareas = plugin.get('fileareas', [])

            for filearea in fileareas:
                files = filearea.get('files', [])

                for file in files:
                    file_type = file.get('type', '')
                    if file_type is None or file_type == '':
                        file.update({'type': 'submission_file'})

                    result.append(file)

        for plugin in plugins:
            editorfields = plugin.get('editorfields', [])

            for editorfield in editorfields:

                filename = editorfield.get('description', '')
                description = editorfield.get('text', '')
                if filename != '' and description != '':
                    description_file = {'filename': filename, 'description': description, 'type': 'description'}
                    result.append(description_file)

        return result
