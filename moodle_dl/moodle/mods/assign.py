from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.types import Course, File


class AssignMod(MoodleMod):
    MOD_NAME = 'assign'
    MOD_PLURAL_NAME = 'assignments'
    MOD_MIN_VERSION = 2012120300  # 2.4

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        # TODO: Add condition for assignments not only submissions
        return config.get_download_submissions() or (not (file.module_modname.endswith(cls.MOD_NAME) and file.deleted))

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        assign_courses = (
            await self.client.async_post('mod_assign_get_assignments', self.get_data_for_mod_entries_endpoint(courses))
        ).get('courses', [])

        result = {}
        for assign_course in assign_courses:
            course_id = assign_course.get('id', 0)
            result[course_id] = self.extract_assign_modules(assign_course.get('assignments', []))

        await self.add_submissions(result)
        return result

    def extract_assign_modules(self, assignments: List[Dict]) -> Dict[int, Dict]:
        result = {}
        for assign in assignments:
            assign_files = assign.get('introfiles', [])
            assign_files += assign.get('introattachments', [])

            self.set_files_types_if_empty(assign_files, 'assign_file')

            assign_intro = assign.get('intro', '')
            if assign_intro != '':
                assign_files.append(
                    {
                        'filename': 'Assignment intro',
                        'filepath': '/',
                        'description': assign_intro,
                        'type': 'description',
                    }
                )

            result[assign.get('cmid', 0)] = {
                'id': assign.get('id', 0),
                'name': assign.get('name', ''),
                'timemodified': assign.get('timemodified', 0),
                'files': assign_files,
            }
        return result

    async def add_submissions(self, assignments: Dict[int, Dict[int, Dict]]):
        """
        Fetches for the assignments list additionally the submissions
        @param assignments: Dictionary of all assignments, indexed by courses, then module id
        """
        if not self.config.get_download_submissions():
            return

        if self.version < 2016052300:  # 3.1
            return

        await self.run_async_load_function_on_mod_entries(assignments, self.load_submissions)

    async def load_submissions(self, assign: Dict):
        "Fetches for a given assign module the submissions"
        data = {'userid': self.user_id, 'assignid': assign.get('id', 0)}
        submission = await self.client.async_post('mod_assign_get_submission_status', data)
        assign['files'] += self._get_files_of_submission(submission)

    def _get_files_of_submission(self, submission: Dict) -> List[Dict]:
        result = []
        # get own submissions
        last_attempt = submission.get('lastattempt', {})
        last_submission = last_attempt.get('submission', {})
        last_team_submission = last_attempt.get('teamsubmission', {})

        # get teachers feedback
        feedback = submission.get('feedback', {})

        result += self._get_files_of_plugins(last_submission)
        result += self._get_files_of_plugins(last_team_submission)
        result += self._get_files_of_plugins(feedback)
        result += self._get_grade_of_feedback(feedback)

        return result

    def _get_grade_of_feedback(self, feedback: Dict) -> List[Dict]:
        grade_for_display = feedback.get('gradefordisplay', "")
        graded_date = feedback.get('gradeddate', 0)
        if graded_date is None or grade_for_display is None or graded_date == 0 or grade_for_display == "":
            return []

        return [
            {
                'filename': 'grade',
                'filepath': '/',
                'timemodified': graded_date,
                'description': grade_for_display,
                'type': 'description',
            }
        ]

    def _get_files_of_plugins(self, obj: Dict) -> List[Dict]:
        result = []
        plugins = obj.get('plugins', [])

        for plugin in plugins:
            for file_area in plugin.get('fileareas', []):
                files = file_area.get('files', [])
                self.set_files_types_if_empty(files, 'submission_file')
                result += files

            for editor_field in plugin.get('editorfields', []):
                filename = editor_field.get('description', '')
                description = editor_field.get('text', '')
                if filename != '' and description != '':
                    description_file = {
                        'filename': filename,
                        'description': description,
                        'type': 'description',
                    }
                    result.append(description_file)

        return result
