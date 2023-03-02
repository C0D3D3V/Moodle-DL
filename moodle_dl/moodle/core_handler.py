import asyncio
import json
import math

from typing import Dict, List

from moodle_dl.moodle.request_helper import RequestHelper
from moodle_dl.types import Course
from moodle_dl.utils import run_with_final_message


class CoreHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper):
        self.client = request_helper
        # oldest supported Moodle version
        self.version = 2011120500

    def fetch_userid_and_version(self) -> str:
        """
        Ask the Moodle system for the user id.
        @return: the userid
        """
        result = self.client.post('core_webservice_get_site_info')

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

    def fetch_courses(self, userid: str) -> List[Course]:
        """
        Queries the Moodle system for all courses the user
        is enrolled in.
        @param userid: the user id
        @return: A list of courses
        """
        data = {'userid': userid}

        courses = self.client.post('core_enrol_get_users_courses', data)

        results = []
        for course in courses:
            results.append(Course(course.get('id', 0), course.get('fullname', '')))
            # We could also extract here the course summary and intro files
        return results

    def fetch_all_visible_courses(self, log_all_courses_to: str = None) -> List[Course]:
        """
        Queries the Moodle system for all courses available on the system and returns:
        @return: A list of all visible courses
        """
        if self.version < 2016120500:  # 3.2
            return []

        result = self.client.post('core_course_get_courses_by_field', timeout=1200)
        if log_all_courses_to is not None:
            with open(log_all_courses_to, 'w', encoding='utf-8') as log_file:
                log_file.write(json.dumps(result, indent=4, ensure_ascii=False))
        courses = result.get('courses', [])

        results = []
        for course in courses:
            if course.get('visible', 0) == 1:
                results.append(Course(course.get('id', 0), course.get('fullname', '')))
        return results

    def fetch_courses_info(self, course_ids: List[int]) -> List[Course]:
        """
        Queries the Moodle system for info about courses in a list.
        @param course_ids: A list of courses ids
        @return: A list of courses
        """
        if len(course_ids) == 0 or self.version < 2016120500:  # 3.2
            return []

        data = {
            "field": "ids",
            "value": ",".join(list(map(str, course_ids))),
        }

        result = self.client.post('core_course_get_courses_by_field', data)
        courses = result.get('courses', [])

        results = []
        for course in courses:
            results.append(Course(course.get('id', 0), course.get('fullname', '')))
            # We could also extract here the course summary and intro files
        return results

    def fetch_sections(self, course_id: int) -> List[Dict]:
        """
        Fetches the Sections List for a course from the Moodle system
        @param course_id: The id of the requested course.
        @return: A List of all section dictionaries
        """
        data = {'courseid': course_id}
        if self.version >= 2015051100:  # 2.9
            data = {
                'courseid': course_id,
                'options[0][name]': 'excludemodules',
                'options[0][value]': 'true',
                'options[1][name]': 'excludecontents',
                'options[1][value]': 'true',
            }
        course_sections = self.client.post('core_course_get_contents', data)

        sections = []
        for section in course_sections:
            sections.append({"id": section.get("id"), "name": section.get("name")})

        return sections

    async def async_load_course_cores(self, courses: List[Course]) -> Dict[int, List[Dict]]:
        """
        Loads all course core structures for every given course
        @param entries: List of all section entries, indexed by course id
        """
        total_courses = len(courses)

        if total_courses == 0:
            return {}
        ctr_digits = int(math.log10(total_courses)) + 1

        async_features = []
        for ctr, course in enumerate(courses):
            # Example: [ 5/16] Loaded course core 123 "Best course"
            loaded_message = (
                f'[%(ctr){ctr_digits}d/%(total){ctr_digits}d] Loaded course core %(course_id)d "%(course_name)s"'
            )

            async_features.append(
                run_with_final_message(
                    self.async_load_course_core,
                    course,
                    loaded_message,
                    {
                        'ctr': ctr + 1,
                        'total': total_courses,
                        'course_id': course.id,
                        'course_name': course.fullname,
                    },
                )
            )

        cores = await asyncio.gather(*async_features)

        result = {}
        for idx, course in enumerate(courses):
            result[course.id] = cores[idx]
        return result

    async def async_load_course_core(self, course: Course) -> List[Dict]:
        data = {'courseid': course.id}
        return await self.client.async_post('core_course_get_contents', data)
