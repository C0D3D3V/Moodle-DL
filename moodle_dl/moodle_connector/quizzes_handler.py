from moodle_dl.moodle_connector.request_helper import RequestHelper, RequestRejectedError
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.path_tools import PathTools
from moodle_dl.moodle_connector.moodle_constants import moodle_html_footer, moodle_html_header


class QuizzesHandler:
    """
    Fetches and parses the various endpoints in Moodle for Quiz Entries.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_quizzes(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Quizzes List for all courses from the
        Moodle system
        @return: A Dictionary of all quizzes,
                 indexed by courses, then quizzes
        """
        # do this only if version is greater then 3.1
        # because mod_quiz_get_quizzes_by_courses will fail
        if self.version < 2016052300:
            return {}

        print('\rDownloading quizzes information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        quizzes_result = self.request_helper.post_REST('mod_quiz_get_quizzes_by_courses', extra_data)

        quizzes = quizzes_result.get('quizzes', [])

        result = {}
        for quiz in quizzes:
            # This is the instance id with which we can make the API queries.
            quiz_id = quiz.get('id', 0)
            quiz_name = quiz.get('name', 'quiz')
            quiz_intro = quiz.get('intro', '')
            quiz_course_module_id = quiz.get('coursemodule', 0)
            quiz_introfiles = quiz.get('introfiles', [])
            course_id = quiz.get('course', 0)

            # normalize
            for quiz_file in quiz_introfiles:
                file_type = quiz_file.get('type', '')
                if file_type is None or file_type == '':
                    quiz_file.update({'type': 'quiz_introfile'})

            if quiz_intro != '':
                # Add Intro File
                intro_file = {
                    'filename': 'Quiz intro',
                    'filepath': '/',
                    'description': quiz_intro,
                    'type': 'description',
                }
                quiz_introfiles.append(intro_file)

            quiz_entry = {
                quiz_course_module_id: {
                    'id': quiz_id,
                    'name': quiz_name,
                    'intro': quiz_intro,
                    'files': quiz_introfiles,
                }
            }

            course_dic = result.get(course_id, {})

            course_dic.update(quiz_entry)

            result.update({course_id: course_dic})

        return result

    def fetch_quizzes_files(self, userid: int, quizzes: {}) -> {}:
        """
        Fetches for the quizzes list of all courses the additionally
        entries. This is kind of waste of resources, because there
        is no API to get all entries at once.
        @param userid: the user id.
        @param quizzes: the dictionary of quizzes of all courses.
        @return: A Dictionary of all quizzes,
                 indexed by courses, then quizzes
        """
        # do this only if version is greater then 3.1
        # because mod_quiz_get_user_attempts will fail
        if self.version < 2016052300:
            return quizzes

        counter = 0
        total = 0
        # count total quizzes for nice console output
        for course_id in quizzes:
            for quiz_id in quizzes[course_id]:
                total += 1

        for course_id in quizzes:
            for quiz_id in quizzes[course_id]:
                counter += 1
                quiz = quizzes[course_id][quiz_id]
                real_id = quiz.get('id', 0)
                data = {'quizid': real_id, 'userid': userid, 'status': 'all'}

                shorted_quiz_name = quiz.get('name', '')
                if len(shorted_quiz_name) > 17:
                    shorted_quiz_name = shorted_quiz_name[:15] + '..'

                print(
                    '\rDownloading quiz infos %3d/%3d [%-17s|%6s]\033[K'
                    % (counter, total, shorted_quiz_name, course_id),
                    end='',
                )

                attempts_result = self.request_helper.post_REST('mod_quiz_get_user_attempts', data)
                attempts = attempts_result.get('attempts', [])

                quiz_files = self._get_files_of_attempts(attempts, quiz.get('name', ''))
                quiz['files'] += quiz_files

        return quizzes

    def _get_files_of_attempts(self, attempts: [], quiz_name: str) -> []:
        result = []

        for i, attempt in enumerate(attempts):
            attempt_id = attempt.get('id', 0)
            attempt_state = attempt.get('state', 'unknown')

            attempt_filename = PathTools.to_valid_name(
                quiz_name + ' (attempt ' + str(attempt_id) + ' ' + attempt_state + ').html'
            )

            shorted_quiz_name = quiz_name
            if len(shorted_quiz_name) > 17:
                shorted_quiz_name = shorted_quiz_name[:15] + '..'

            # print(
            #     '\rDownloading attempt of quiz [%-17s|%6s] %3d/%3d\033[K'
            #     % (shorted_quiz_name, attempt_id, i, len(attempts) - 1),
            #     end='',
            # )

            data = {'attemptid': attempt_id}

            try:
                if attempt_state == 'finished':
                    attempt_result = self.request_helper.post_REST('mod_quiz_get_attempt_review', data)
                elif attempt_state == 'inprogress':
                    attempt_result = self.request_helper.post_REST('mod_quiz_get_attempt_summary', data)
                else:
                    continue
            except RequestRejectedError:
                continue

            questions = attempt_result.get('questions', [])

            # build quiz HTML
            quiz_html = moodle_html_header
            for question in questions:

                question_html = question.get('html', '').split('<script>')[0]
                if question_html is None:
                    question_html = ''

                quiz_html += question_html + '\n'

                question_files = question.get('responsefileareas', [])
                for question_file in question_files:
                    file_type = question_file.get('type', '')
                    if file_type is None or file_type == '':
                        question_file.update({'type': 'quiz_file'})
                    result.append(question_file)

            quiz_html += moodle_html_footer
            attempt_file = {
                'filename': attempt_filename,
                'filepath': '/',
                'timemodified': 0,
                'html': quiz_html,
                'type': 'html',
            }
            result.append(attempt_file)

        return result
