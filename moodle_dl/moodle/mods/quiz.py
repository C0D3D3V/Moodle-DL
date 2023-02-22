import logging

from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.moodle.moodle_constants import moodle_html_footer, moodle_html_header
from moodle_dl.moodle.request_helper import RequestRejectedError
from moodle_dl.types import Course, File
from moodle_dl.utils import PathTools as PT


class QuizMod(MoodleMod):
    MOD_NAME = 'quiz'
    MOD_PLURAL_NAME = 'quizzes'
    MOD_MIN_VERSION = 2016052300  # 3.1

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        return config.get_download_quizzes() or (not (file.module_modname.endswith(cls.MOD_NAME) and file.deleted))

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        quizzes = (
            await self.client.async_post(
                'mod_quiz_get_quizzes_by_courses', self.get_data_for_mod_entries_endpoint(courses)
            )
        ).get('quizzes', [])

        result = {}
        for quiz in quizzes:
            course_id = quiz.get('course', 0)

            quiz_files = quiz.get('introfiles', [])
            self.set_files_types_if_empty(quiz_files, 'quiz_introfile')

            quiz_intro = quiz.get('intro', '')
            if quiz_intro != '':
                quiz_files.append(
                    {
                        'filename': 'Quiz intro',
                        'filepath': '/',
                        'description': quiz_intro,
                        'type': 'description',
                    }
                )

            self.add_module(
                result,
                course_id,
                quiz.get('coursemodule', 0),
                {
                    'id': quiz.get('id', 0),
                    'name': quiz.get('name', 'unnamed quiz'),
                    'files': quiz_files,
                },
            )

        await self.add_quizzes_files(result)
        return result

    async def add_quizzes_files(self, quizzes: Dict[int, Dict[int, Dict]]):
        """
        Fetches for the quizzes list the quizzes files
        @param quizzes: Dictionary of all quizzes, indexed by courses, then module id
        """
        if not self.config.get_download_quizzes():
            return

        if self.version < 2016052300:  # 3.1
            return

        await self.run_async_load_function_on_mod_entries(quizzes, self.load_quiz_files)

    async def load_quiz_files(self, quiz: Dict):
        data = {'quizid': quiz.get('id', 0), 'userid': self.user_id, 'status': 'all'}
        attempts = (await self.client.async_post('mod_quiz_get_user_attempts', data)).get('attempts', [])
        quiz_name = quiz.get('name', '')
        for attempt in attempts:
            attempt['_quiz_name'] = quiz_name

        quiz['files'] += await self.run_async_collect_function_on_list(
            attempts,
            self.load_files_of_attempt,
            'attempt',
            {'collect_id': 'id', 'collect_name': '_quiz_name'},
        )

    async def load_files_of_attempt(self, attempt: Dict) -> List[Dict]:
        result = []

        attempt_id = attempt.get('id', 0)
        attempt_state = attempt.get('state', 'unknown')
        quiz_name = attempt.get('_quiz_name', '')

        attempt_filename = PT.to_valid_name(
            quiz_name + ' (attempt ' + str(attempt_id) + ' ' + attempt_state + ')', is_file=False
        )

        data = {'attemptid': attempt_id}
        try:
            if attempt_state == 'finished':
                questions = (await self.client.async_post('mod_quiz_get_attempt_review', data)).get('questions', [])
            elif attempt_state == 'inprogress':
                questions = (await self.client.async_post('mod_quiz_get_attempt_summary', data)).get('questions', [])
            else:
                return result
        except RequestRejectedError:
            logging.debug("No access rights for quiz attempt %d", attempt_id)
            return result

        # build quiz HTML
        quiz_html = moodle_html_header
        for question in questions:
            question_html = question.get('html', '').split('<script>')[0]
            if question_html is None:
                question_html = ''
            quiz_html += question_html + '\n'

            question_files = question.get('responsefileareas', [])
            self.set_files_types_if_empty(question_files, 'quiz_file')
            result.extend(question_files)

        quiz_html += moodle_html_footer
        result.append(
            {
                'filename': attempt_filename,
                'filepath': '/',
                'timemodified': 0,
                'html': quiz_html,
                'type': 'html',
                'no_search_for_urls': True,
            }
        )

        return result
