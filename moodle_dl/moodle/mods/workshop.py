import logging

from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.moodle.request_helper import RequestRejectedError
from moodle_dl.types import Course, File


class WorkshopMod(MoodleMod):
    MOD_NAME = 'workshop'
    MOD_PLURAL_NAME = 'workshops'
    MOD_MIN_VERSION = 2017111300  # 3.4

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        return config.get_download_workshops() or (not (file.module_modname.endswith(cls.MOD_NAME) and file.deleted))

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        workshops = (
            await self.client.async_post(
                'mod_workshop_get_workshops_by_courses', self.get_data_for_mod_entries_endpoint(courses)
            )
        ).get('workshops', [])

        result = {}
        for workshop in workshops:
            course_id = workshop.get('course', 0)
            workshop_files = workshop.get('introfiles', [])
            workshop_files += workshop.get('instructauthorsfiles', [])
            workshop_files += workshop.get('instructreviewersfiles', [])
            workshop_files += workshop.get('conclusionfiles', [])
            self.set_files_types_if_empty(workshop_files, 'workshop_introfile')

            workshop_intro = workshop.get('intro', '')
            if workshop_intro != '':
                workshop_files.append(
                    {
                        'filename': 'Workshop intro',
                        'filepath': '/',
                        'description': workshop_intro,
                        'type': 'description',
                    }
                )

            workshop_instruct_authors = workshop.get('instructauthors', '')
            if workshop_instruct_authors != '':
                workshop_files.append(
                    {
                        'filename': 'Instructions for submission',
                        'filepath': '/',
                        'description': workshop_instruct_authors,
                        'type': 'description',
                    }
                )

            workshop_instruct_reviewers = workshop.get('instructreviewers', '')
            if workshop_instruct_reviewers != '':
                workshop_files.append(
                    {
                        'filename': 'Instructions for assessment',
                        'filepath': '/',
                        'description': workshop_instruct_reviewers,
                        'type': 'description',
                    }
                )

            workshop_conclusion = workshop.get('conclusion', '')
            if workshop_conclusion != '':
                workshop_files.append(
                    {
                        'filename': 'Conclusion',
                        'filepath': '/',
                        'description': workshop_conclusion,
                        'type': 'description',
                    }
                )

            self.add_module(
                result,
                course_id,
                workshop.get('coursemodule', 0),
                {
                    'id': workshop.get('id', 0),
                    'name': workshop.get('name', 'unnamed workshop'),
                    'files': workshop_files,
                },
            )

        await self.add_workshops_files(result)
        return result

    async def add_workshops_files(self, workshops: Dict[int, Dict[int, Dict]]):
        """
        Fetches for the workshops list the forum posts
        @param workshops: Dictionary of all workshops, indexed by courses, then module id
        """
        if not self.config.get_download_workshops():
            return

        if self.version < 2017111300:  # 3.4
            return

        await self.run_async_load_function_on_mod_entries(workshops, self.load_workshop_files)

    async def load_workshop_files(self, workshop: Dict):
        workshop_id = workshop.get('id', 0)
        data = {'workshopid': workshop_id, 'userid': self.user_id}

        try:
            submissions = (await self.client.async_post('mod_workshop_get_submissions', data)).get('submissions', [])
        except RequestRejectedError:
            logging.debug("No access rights for workshop %d", workshop_id)
            return

        try:
            assessments = (await self.client.async_post('mod_workshop_get_reviewer_assessments', data)).get(
                'assessments', []
            )
        except RequestRejectedError:
            assessments = []
        submissions += await self.run_async_collect_function_on_list(
            assessments,
            self.load_foreign_submission,
            'foreign submission',
            {'collect_id': 'submissionid', 'collect_name': 'title'},
        )

        try:
            grades = await self.client.async_post('mod_workshop_get_grades', data)
        except RequestRejectedError:
            grades = {}

        workshop_files = self._get_files_of_workshop(submissions, grades)
        workshop['files'] += workshop_files

    async def load_foreign_submission(self, assessment: Dict) -> Dict:
        # assessment_id = assessment.get('id', 0)
        # assessment_reviewer_id = assessment.get('reviewerid', 0)

        assessment_files = assessment.get('feedbackcontentfiles', [])
        assessment_files += assessment.get('feedbackattachmentfiles', [])

        feedback_author = assessment.get('feedbackauthor', '')
        if feedback_author != '':
            assessment_files.append(
                {
                    'filename': 'Feedback for the author',
                    'filepath': '/',
                    'description': feedback_author,
                    'type': 'description',
                }
            )

        feedback_reviewer = assessment.get('feedbackreviewer', '')
        if feedback_reviewer != '':
            assessment_files.append(
                {
                    'filename': 'Feedback for the reviewer',
                    'filepath': '/',
                    'description': feedback_reviewer,
                    'type': 'description',
                }
            )
        assessment_submission_id = assessment.get('submissionid', 0)
        # Get submissions of assessments
        data = {'submissionid': assessment_submission_id}
        try:
            submission = (await self.client.async_post('mod_workshop_get_submission', data)).get('submission', {})
            submission['files'] = assessment_files
            return submission
        except RequestRejectedError:
            logging.debug("No access rights for workshop submission %d", assessment_submission_id)
            return None

    def _get_files_of_workshop(self, submissions: List[Dict], grades: Dict) -> List:
        result = []

        # Grades
        assessment_long_str_grade = grades.get('assessmentlongstrgrade', '')
        if assessment_long_str_grade != '':
            result.append(
                {
                    'filename': 'Assessment grade',
                    'filepath': '/',
                    'description': assessment_long_str_grade,
                    'type': 'description',
                }
            )

        submission_long_str_grade = grades.get('submissionlongstrgrade', '')
        if submission_long_str_grade != '':
            result.append(
                {
                    'filename': 'Submission grade',
                    'filepath': '/',
                    'description': submission_long_str_grade,
                    'type': 'description',
                }
            )

        # Own and foreign submissions
        for submission in submissions:
            submission_content = submission.get('content', 0)

            filepath = f"/submissions {submission.get('id', 0)}/"

            submission_files = submission.get('contentfiles', [])
            submission_files += submission.get('attachmentfiles', [])
            submission_files += submission.get('files', [])

            for submission_file in submission_files:
                self.set_file_type_if_empty(submission_file, 'workshop_file')
                submission_file['filepath'] = filepath

            if submission_content != '':
                submission_files.append(
                    {
                        'filename': submission.get('title', 0),
                        'filepath': filepath,
                        'description': submission_content,
                        'timemodified': submission.get('timemodified', 0),
                        'type': 'description',
                    }
                )
            result += submission_files

        return result
