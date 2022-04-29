from moodle_dl.moodle_connector.request_helper import RequestHelper, RequestRejectedError
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.path_tools import PathTools
from moodle_dl.moodle_connector.moodle_constants import moodle_html_footer, moodle_html_header


class LessonsHandler:
    """
    Fetches and parses the various endpoints in Moodle for lesson entries.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_lessons(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Lessons List for all courses from the
        Moodle system
        @return: A Dictionary of all lessons,
                 indexed by courses, then lessons
        """
        # do this only if version is greater then 3.3
        # because mod_lesson_get_lessons_by_courses will fail
        if self.version < 2017051500:
            return {}

        print('\rDownloading lessons information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        lessons_result = self.request_helper.post_REST('mod_lesson_get_lessons_by_courses', extra_data)

        lessons = lessons_result.get('lessons', [])

        result = {}
        for lesson in lessons:
            # This is the instance id with which we can make the API queries.
            lesson_id = lesson.get('id', 0)
            lesson_name = lesson.get('name', 'unnamed lesson')
            lesson_intro = lesson.get('intro', '')
            lesson_course_module_id = lesson.get('coursemodule', 0)
            lesson_introfiles = lesson.get('introfiles', [])
            lesson_introfiles += lesson.get('mediafiles', [])
            course_id = lesson.get('course', 0)

            # normalize
            for lesson_file in lesson_introfiles:
                file_type = lesson_file.get('type', '')
                if file_type is None or file_type == '':
                    lesson_file.update({'type': 'lesson_introfile'})

            if lesson_intro != '':
                # Add Intro File
                intro_file = {
                    'filename': 'Lesson intro',
                    'filepath': '/',
                    'description': lesson_intro,
                    'type': 'description',
                }
                lesson_introfiles.append(intro_file)

            lesson_entry = {
                lesson_course_module_id: {
                    'id': lesson_id,
                    'name': lesson_name,
                    'intro': lesson_intro,
                    'files': lesson_introfiles,
                }
            }

            course_dic = result.get(course_id, {})

            course_dic.update(lesson_entry)

            result.update({course_id: course_dic})

        return result

    def fetch_lessons_files(self, userid: int, lessons: {}) -> {}:
        """
        Fetches for the lessons list of all courses the additionally
        entries. This is kind of waste of resources, because there
        is no API to get all entries at once.
        @param userid: the user id.
        @param lessons: the dictionary of lessons of all courses.
        @return: A Dictionary of all lessons,
                 indexed by courses, then lessons
        """
        # do this only if version is greater then 3.3
        # because mod_lesson_get_user_attempt will fail
        if self.version < 2017051500:
            return lessons

        counter = 0
        total = 0
        # count total lessons for nice console output
        for course_id in lessons:
            for lesson_id in lessons[course_id]:
                total += 1

        for course_id in lessons:
            for lesson_id in lessons[course_id]:
                counter += 1
                lesson = lessons[course_id][lesson_id]
                real_id = lesson.get('id', 0)
                data = {'lessonid': real_id, 'userid': userid, 'lessonattempt': 0}

                shorted_lesson_name = lesson.get('name', '')
                if len(shorted_lesson_name) > 17:
                    shorted_lesson_name = shorted_lesson_name[:15] + '..'

                print(
                    (
                        '\r'
                        + 'Downloading lesson infos'
                        + f' {counter:3d}/{total:3d}'
                        + f' [{shorted_lesson_name:<17}|{course_id:6}]\033[K'
                    ),
                    end='',
                )

                try:
                    attempt_result = self.request_helper.post_REST('mod_lesson_get_user_attempt', data)
                except RequestRejectedError:
                    continue

                lesson_files = self._get_files_of_attempt(attempt_result, lesson.get('name', ''))
                lesson['files'] += lesson_files

        return lessons

    def _get_files_of_attempt(self, attempt_result: {}, lesson_name: str) -> []:
        result = []

        answerpages = attempt_result.get('answerpages', [])
        # The review page should actually be generated here.
        # https://github.com/moodle/moodle/blob/511a87f5fc357f18a4c53911f6e6c7f7b526246e/mod/lesson/report.php#L278-L366

        # Grade is in: attempt_result.userstats.gradeinfo.earned  (max points: attempt_result.userstats.gradeinfo.total)
        # Take care, grade can be None

        grade = attempt_result.get('userstats', {}).get('gradeinfo', {}).get('earned', None)
        grade_total = attempt_result.get('userstats', {}).get('gradeinfo', {}).get('total', None)

        if grade is not None and grade_total is not None:
            grade_file = {
                'filename': 'grade',
                'filepath': '/',
                'timemodified': 0,
                'description': str(grade) + ' / ' + str(grade_total),
                'type': 'description',
            }
            result.append(grade_file)

        # build lesson HTML
        lesson_html = moodle_html_header
        attempt_filename = PathTools.to_valid_name(lesson_name)
        lesson_is_empty = True
        for answerpage in answerpages:
            page_id = answerpage.get('page', {}).get('id', 0)
            lesson_id = answerpage.get('page', {}).get('lessonid', 0)

            shorted_lesson_name = lesson_name
            if len(shorted_lesson_name) > 17:
                shorted_lesson_name = shorted_lesson_name[:15] + '..'

            data = {'lessonid': lesson_id, 'pageid': page_id, 'returncontents': 1}

            try:
                page_result = self.request_helper.post_REST('mod_lesson_get_page_data', data)
            except RequestRejectedError:
                continue

            pagecontent = page_result.get('pagecontent', '').split('<script>')[0]

            if pagecontent != '':
                lesson_is_empty = False

            lesson_html += pagecontent + '\n'

            page_files = page_result.get('contentfiles', [])
            for page_file in page_files:
                file_type = page_file.get('type', '')
                if file_type is None or file_type == '':
                    page_file.update({'type': 'lesson_file'})
                result.append(page_file)

        if not lesson_is_empty:
            lesson_html += moodle_html_footer
            attempt_file = {
                'filename': attempt_filename,
                'filepath': '/',
                'timemodified': 0,
                'html': lesson_html,
                'type': 'html',
                'no_search_for_urls': True,
            }
            result.append(attempt_file)

        return result
