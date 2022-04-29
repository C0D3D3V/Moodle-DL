from moodle_dl.moodle_connector.request_helper import RequestHelper, RequestRejectedError
from moodle_dl.state_recorder.course import Course


class WorkshopsHandler:
    """
    Fetches and parses the various endpoints in Moodle for workshop entries.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_workshops(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Workshops List for all courses from the
        Moodle system
        @return: A Dictionary of all workshops,
                 indexed by courses, then workshops
        """
        # do this only if version is greater then 3.4
        # because mod_workshop_get_workshops_by_courses will fail
        if self.version < 2017111300:
            return {}

        print('\rDownloading workshops information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        workshops_result = self.request_helper.post_REST('mod_workshop_get_workshops_by_courses', extra_data)

        workshops = workshops_result.get('workshops', [])

        result = {}
        for workshop in workshops:
            # This is the instance id with which we can make the API queries.
            workshop_id = workshop.get('id', 0)
            workshop_name = workshop.get('name', 'unnamed workshop')
            workshop_course_module_id = workshop.get('coursemodule', 0)
            workshop_introfiles = workshop.get('introfiles', [])
            workshop_introfiles += workshop.get('instructauthorsfiles', [])
            workshop_introfiles += workshop.get('instructreviewersfiles', [])
            workshop_introfiles += workshop.get('conclusionfiles', [])
            course_id = workshop.get('course', 0)

            # normalize
            for workshop_file in workshop_introfiles:
                file_type = workshop_file.get('type', '')
                if file_type is None or file_type == '':
                    workshop_file.update({'type': 'workshop_introfile'})

            workshop_intro = workshop.get('intro', '')
            if workshop_intro != '':
                # Add Intro File
                intro_file = {
                    'filename': 'Workshop intro',
                    'filepath': '/',
                    'description': workshop_intro,
                    'type': 'description',
                }
                workshop_introfiles.append(intro_file)

            workshop_instructauthors = workshop.get('instructauthors', '')
            if workshop_instructauthors != '':
                # Add Instructions for submission File
                instructauthors_file = {
                    'filename': 'Instructions for submission',
                    'filepath': '/',
                    'description': workshop_instructauthors,
                    'type': 'description',
                }
                workshop_introfiles.append(instructauthors_file)

            workshop_instructreviewers = workshop.get('instructreviewers', '')
            if workshop_instructreviewers != '':
                # Add Instructions for assessment File
                instructreviewers_file = {
                    'filename': 'Instructions for assessment',
                    'filepath': '/',
                    'description': workshop_instructreviewers,
                    'type': 'description',
                }
                workshop_introfiles.append(instructreviewers_file)

            workshop_conclusion = workshop.get('conclusion', '')
            if workshop_conclusion != '':
                # Add Conclusion File
                conclusion_file = {
                    'filename': 'Conclusion',
                    'filepath': '/',
                    'description': workshop_conclusion,
                    'type': 'description',
                }
                workshop_introfiles.append(conclusion_file)

            workshop_entry = {
                workshop_course_module_id: {
                    'id': workshop_id,
                    'name': workshop_name,
                    'intro': workshop_intro,
                    'files': workshop_introfiles,
                }
            }

            course_dic = result.get(course_id, {})

            course_dic.update(workshop_entry)

            result.update({course_id: course_dic})

        return result

    def fetch_workshops_files(self, userid: int, workshops: {}) -> {}:
        """
        Fetches for the workshops list of all courses the additionally
        entries. This is kind of waste of resources, because there
        is no API to get all entries at once.
        @param userid: the user id.
        @param workshops: the dictionary of workshops of all courses.
        @return: A Dictionary of all workshops,
                 indexed by courses, then workshops
        """
        # do this only if version is greater then 3.3
        # because mod_quiz_get_user_attempts will fail
        if self.version < 2017111300:
            return workshops

        counter = 0
        total = 0
        # count total workshops for nice console output
        for course_id in workshops:
            for workshop_id in workshops[course_id]:
                total += 1

        for course_id in workshops:
            for workshop_id in workshops[course_id]:
                counter += 1
                workshop = workshops[course_id][workshop_id]
                real_id = workshop.get('id', 0)
                data = {'workshopid': real_id, 'userid': userid}

                shorted_workshop_name = workshop.get('name', '')
                if len(shorted_workshop_name) > 17:
                    shorted_workshop_name = shorted_workshop_name[:15] + '..'

                print(
                    (
                        '\r'
                        + 'Downloading workshop infos'
                        + f' {counter:3d}/{total:3d}'
                        + f' [{shorted_workshop_name:<17}|{course_id:6}]\033[K'
                    ),
                    end='',
                )

                try:
                    submissions_result = self.request_helper.post_REST('mod_workshop_get_submissions', data)
                except RequestRejectedError:
                    continue

                try:
                    reviewer_assessments_result = self.request_helper.post_REST(
                        'mod_workshop_get_reviewer_assessments', data
                    )
                except RequestRejectedError:
                    reviewer_assessments_result = {}

                try:
                    grades_result = self.request_helper.post_REST('mod_workshop_get_grades', data)
                except RequestRejectedError:
                    grades_result = {}

                workshop_files = self._get_files_of_workshop(
                    submissions_result, reviewer_assessments_result, grades_result
                )
                workshop['files'] += workshop_files

        return workshops

    def _get_files_of_workshop(self, submissions_result: {}, reviewer_assessments_result: {}, grades_result: {}) -> []:
        result = []

        submissions = submissions_result.get('submissions', [])

        reviewer_assessments = reviewer_assessments_result.get('assessments', [])

        for reviewer_assessment in reviewer_assessments:
            # reviewer_assessment_id = reviewer_assessment.get('id', 0)
            reviewer_assessment_submissionid = reviewer_assessment.get('submissionid', 0)
            # reviewer_assessment_reviewerid = reviewer_assessment.get('reviewerid', 0)

            # Get attached files
            reviewer_assessment_files = reviewer_assessment.get('feedbackcontentfiles', [])
            reviewer_assessment_files += reviewer_assessment.get('feedbackattachmentfiles', [])

            feedbackauthor = reviewer_assessment.get('feedbackauthor', '')
            if feedbackauthor != '':
                # Add Feedback for the author
                feedbackauthor_file = {
                    'filename': 'Feedback for the author',
                    'filepath': '/',
                    'description': feedbackauthor,
                    'type': 'description',
                }
                reviewer_assessment_files.append(feedbackauthor_file)

            feedbackreviewer = reviewer_assessment.get('feedbackreviewer', '')
            if feedbackreviewer != '':
                # Add Feedback for the reviewer
                feedbackreviewer_file = {
                    'filename': 'Feedback for the reviewer',
                    'filepath': '/',
                    'description': feedbackreviewer,
                    'type': 'description',
                }
                reviewer_assessment_files.append(feedbackreviewer_file)

            # Get submissions of assessments
            data = {'submissionid': reviewer_assessment_submissionid}
            try:
                submission_result = self.request_helper.post_REST('mod_workshop_get_submission', data)
            except RequestRejectedError:
                submission_result = None

            if submission_result is not None:
                submission = submission_result.get('submission', {})
                submission['files'] = reviewer_assessment_files
                submissions.append(submission)

        assessmentlongstrgrade = grades_result.get('assessmentlongstrgrade', '')
        if assessmentlongstrgrade != '':
            # Add Assessment Grade
            assessmentlongstrgrade_file = {
                'filename': 'Assessment grade',
                'filepath': '/',
                'description': assessmentlongstrgrade,
                'type': 'description',
            }
            result.append(assessmentlongstrgrade_file)

        submissionlongstrgrade = grades_result.get('submissionlongstrgrade', '')
        if submissionlongstrgrade != '':
            # Add Submission Grade
            submissionlongstrgrade_file = {
                'filename': 'Submission grade',
                'filepath': '/',
                'description': submissionlongstrgrade,
                'type': 'description',
            }
            result.append(submissionlongstrgrade_file)

        for submission in submissions:
            submission_id = submission.get('id', 0)
            submission_timemodified = submission.get('timemodified', 0)
            submission_title = submission.get('title', 0)
            submission_content = submission.get('content', 0)

            filepath = f'/submissions {submission_id}/'

            submission_files = submission.get('contentfiles', [])
            submission_files += submission.get('attachmentfiles', [])
            submission_files += submission.get('files', [])

            for submission_file in submission_files:
                file_type = submission_file.get('type', '')
                if file_type is None or file_type == '':
                    submission_file.update({'type': 'workshop_file'})
                submission_file.update({'filepath': filepath})

            if submission_content != '':
                # Add submission content file
                content_file = {
                    'filename': submission_title,
                    'filepath': filepath,
                    'description': submission_content,
                    'timemodified': submission_timemodified,
                    'type': 'description',
                }
                submission_files.append(content_file)
            result += submission_files

        return result
