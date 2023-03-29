import logging
from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.moodle.request_helper import RequestRejectedError
from moodle_dl.types import Course, File
from moodle_dl.utils import PathTools as PT


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
        await self.add_foreign_submissions(result)
        return result

    def extract_assign_modules(self, assignments: List[Dict]) -> Dict[int, Dict]:
        result = {}
        for assign in assignments:
            assign_files = assign.get('introfiles', [])
            assign_files += assign.get('introattachments', [])

            self.set_props_of_files(assign_files, type='assign_file')

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

    async def add_foreign_submissions(self, assignments: Dict[int, Dict[int, Dict]]):
        """
        Fetches for the assignments list additionally the submissions of other students
        @param assignments: Dictionary of all assignments, indexed by courses, then module id
        """
        if not self.config.get_download_submissions():
            return

        if self.version < 2013051400:  # 2.5
            return

        # get submissions of all students for all assignments (only teachers can see that)
        indexed_assignment_ids = self.get_indexed_ids_of_mod_instances(assignments)
        if len(indexed_assignment_ids) <= 0:
            return

        assignments_with_all_submissions = (
            await self.client.async_post('mod_assign_get_submissions', {'assignmentids': indexed_assignment_ids})
        ).get('assignments', [])

        if len(assignments_with_all_submissions) <= 0:
            return

        for course_id, modules in assignments.items():
            found_assignment_in_course = False
            for assignment in assignments_with_all_submissions:
                for _module_id, module in modules.items():
                    if assignment['assignmentid'] == module['id']:
                        found_assignment_in_course = True
                        break
                if found_assignment_in_course:
                    break
            if not found_assignment_in_course:
                continue
            # TODO: Extract the API call to get enrolled users, if we need the information also in another mod
            try:
                course_users = await self.client.async_post('core_enrol_get_enrolled_users', {'courseid': course_id})
            except RequestRejectedError:
                logging.debug("No access rights for enrolled users list of course %d", course_id)
                return

            for assignment in assignments_with_all_submissions:
                found_module = None
                for _module_id, module in modules.items():
                    if assignment['assignmentid'] == module['id']:
                        found_module = module
                        break
                if found_module is None:
                    continue

                for submission in assignment.get('submissions', []):
                    user_id = submission.get('userid', 0)
                    group_id = submission.get('groupid', 0)
                    subfolder = None
                    if user_id == 0:
                        # Its a group submission
                        found_users = []
                        group_name = None
                        for user in course_users:
                            for group in user.get('groups', []):
                                if group.get('id', 0) == group_id:
                                    found_users.append(user)
                                    if group_name is None:
                                        group_name = group.get('name')
                                    break
                        if len(found_users) == 0:
                            # should not happen
                            continue
                        all_usernames = ' & '.join(
                            (f"{user.get('fullname')} ({user.get('idnumber') or user.get('id', 0)})")
                            for user in found_users
                        )
                        subfolder = PT.to_valid_name(
                            f"{group_name or 'Unnamed group'} ({group_id}): {all_usernames}", is_file=False
                        )
                    else:
                        # Its a user submission
                        found_user = None
                        for user in course_users:
                            if user.get('id', 0) == user_id:
                                found_user = user
                                break
                        if found_user is None:
                            # should not happen
                            continue
                        subfolder = PT.to_valid_name(
                            f"{found_user.get('fullname')} ({found_user.get('idnumber') or found_user.get('id', 0)})",
                            is_file=False,
                        )
                    found_module['files'] += self._get_files_of_plugins(submission, f'/all_submissions/{subfolder}/')

    async def load_submissions(self, assign: Dict):
        "Fetches for a given assign module the submissions"
        data = {'userid': self.user_id, 'assignid': assign.get('id', 0)}
        submission = await self.client.async_post('mod_assign_get_submission_status', data)
        assign['files'] += self._get_files_of_submission(submission)

    def _get_files_of_submission(self, submission: Dict) -> List[Dict]:
        result = []
        # get own submission
        last_attempt = submission.get('lastattempt', {})
        last_submission = last_attempt.get('submission', {})
        last_team_submission = last_attempt.get('teamsubmission', {})
        # We could also extract previous attempts, but for now we are only interested in last attempt
        # Multiple attempts on assignments are very raw and therefore not implemented yet

        # get teachers feedback
        feedback = submission.get('feedback', {})

        base_file_path = '/submissions/'
        result += self._get_files_of_plugins(last_submission, base_file_path)
        result += self._get_files_of_plugins(last_team_submission, base_file_path)
        result += self._get_files_of_plugins(feedback, base_file_path)
        result += self._get_grade_of_feedback(feedback, base_file_path)

        return result

    def _get_grade_of_feedback(self, feedback: Dict, base_file_path: str) -> List[Dict]:
        grade_for_display = feedback.get('gradefordisplay')
        graded_date = feedback.get('gradeddate')
        if graded_date is None or grade_for_display is None:
            return []

        return [
            {
                'filename': 'grade',
                'filepath': base_file_path,
                'timemodified': graded_date,
                'description': grade_for_display,
                'type': 'description',
            }
        ]

    def _get_files_of_plugins(self, obj: Dict, base_file_path: str) -> List[Dict]:
        result = []
        plugins = obj.get('plugins', [])

        for plugin in plugins:
            # We could use the plugin name in the file structure, but it is most of the time unnecessary information
            for file_area in plugin.get('fileareas', []):
                files = file_area.get('files', [])
                self.set_props_of_files(files, type='submission_file')
                self.set_base_file_path_of_files(files, base_file_path)
                result += files

            for editor_field in plugin.get('editorfields', []):
                filename = editor_field.get('description', '')
                description = editor_field.get('text', '')
                if filename != '' and description != '':
                    result.append(
                        {
                            'filename': filename,
                            'description': description,
                            'type': 'description',
                            'filepath': base_file_path,
                        }
                    )

        return result
