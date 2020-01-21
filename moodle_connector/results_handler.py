from state_recorder.file import File
from state_recorder.course import Course
from moodle_connector.request_helper import RequestHelper


class ResultsHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper):
        self.request_helper = request_helper

    def fetch_userid(self) -> str:
        """
        Ask the Moodle system for the user id.
        @return: the userid
        """
        result = self.request_helper.get_REST('core_webservice_get_site_info')

        if ("userid" not in result):
            raise RuntimeError(
                'Error could not receive your user ID!')

        return result.get("userid", "")

    def fetch_courses(self, userid: str) -> [Course]:
        """
        Queries the Moodle system for all courses the user
        is enrolled in.
        @param userid: the user id
        @return: A list of courses
        """
        data = {
            'userid': userid
        }

        result = self.request_helper.get_REST(
            'core_enrol_get_users_courses', data)

        results = []
        for course in result:
            results.append(
                Course(course.get("id", ""),
                       course.get("fullname", ""), [])
            )
        return results

    def fetch_assignments(self, course_id: str) -> {}:
        """
        Fetches the Assignments List for a course from the
        Moodle system
        @param course_id: The id of the course for which the assignments
                          should be fetched.
        @return: A List of assignments or None
        """

        # TODO: do this only on version 2.4
        # "release":"3.4.1+ (Build: 20180216)"
        # in core_webservice_get_site_info
        assign_data = {
            'courseids[0]': course_id
        }

        assign_result = self.request_helper.get_REST(
            'mod_assign_get_assignments', assign_data)

        assign_courses = assign_result.get('courses', [])

        # normaly there is only on course with exactly the id
        # of course_id but who knows...
        # Choose the correct course from the course list
        matched_assign_course = None
        for assign_course in assign_courses:
            assign_course_id = assign_course.get("id", 0)
            if(assign_course_id == course_id):
                matched_assign_course = assign_course
                break

        return matched_assign_course

    @staticmethod
    def _get_files_in_sections(course_sections: [], assignments: []) -> [File]:
        """
        Iterates over all sections of a course to find files (or modules).
        @param course_sections: The course object returned by Moodle,
                                containing the sections of the course.
        @param assignments: the list of assignments of the course.
        @return: A list of files of the course.
        """
        files = []
        for section in course_sections:
            section_name = section.get("name", "")
            section_modules = section.get("modules", [])
            files += ResultsHandler._get_files_in_modules(section_name,
                                                          section_modules,
                                                          assignments)
        return files

    @staticmethod
    def _get_files_in_modules(section_name: str,
                              section_modules: [], assignments: []) -> [File]:
        """
        Iterates over all modules to find files (or content) in them.
        @param section_name: The name of the section to be iterated over.
        @param section_modules: The modules of the section.
        @param assignments: the list of assignments of the course.
        @return: A list of files of the section.
        """
        files = []
        for module in section_modules:
            module_name = module.get("name", "")
            module_modname = module.get("modname", "")
            module_id = int(module.get("id", 0))

            module_contents = module.get("contents", [])

            if (module_modname in ["resource", "folder", "url"]):
                files += ResultsHandler._handle_files(section_name,
                                                      module_name,
                                                      module_modname,
                                                      module_id,
                                                      module_contents)

            elif (module_modname == "assign"):

                # find assign with same module_id
                assign_files = ResultsHandler._get_assign_files_by_id(
                    assignments,
                    module_id)

                files += ResultsHandler._handle_files(section_name,
                                                      module_name,
                                                      module_modname,
                                                      module_id,
                                                      assign_files)

        return files

    @staticmethod
    def _handle_files(section_name: str, module_name: str,
                      module_modname: str, module_id: str,
                      module_contents: []) -> [File]:
        """
        Iterates over all files that are in a module or assignment and
        returns a list of all files
        @param module_contents: The list of content of the module
                                or assignment.
        @params: All necessary parameters to create a file.
        @return: A list of files that exist in a module.
        """
        files = []
        for content in module_contents:
            content_type = content.get("type", "")
            content_filename = content.get("filename", "")
            content_filepath = content.get("filepath", "/")
            if content_filepath is None:
                content_filepath = '/'
            content_filesize = int(content.get("filesize", 0))
            content_fileurl = content.get("fileurl", "")
            content_timemodified = int(
                content.get("timemodified", 0))
            content_isexternalfile = bool(content.get(
                "isexternalfile", False))

            files.append(File(
                module_id=module_id,
                section_name=section_name,
                module_name=module_name,
                content_filepath=content_filepath,
                content_filename=content_filename,
                content_fileurl=content_fileurl,
                content_filesize=content_filesize,
                content_timemodified=content_timemodified,
                module_modname=module_modname,
                content_type=content_type,
                content_isexternalfile=content_isexternalfile)
            )
        return files

    @staticmethod
    def _get_assign_files_by_id(assignments: [], module_id: str) -> []:
        """
        In the assignment list, look for an assignment with the same ID
        and return the list of files of this assignment.
        @param assignments: The list of assignments
        @param module_id: The id of the searched assignment
        @return: A list of files
        """
        # find assign with same module_id
        if (assignments is None):
            return []

        assignments = assignments.get('assignments', [])

        for assignment in assignments:
            assignment_id = assignment.get('cmid', 0)
            if (assignment_id == module_id):
                assignment_files = assignment.get(
                    'introattachments', [])
                break

        # update file type information
        for assignment_file in assignment_files:
            file_type = assignment_file.get("type", "")
            if (file_type is None or file_type == ""):
                assignment_file.update({'type': 'assign_file'})

        return assignment_files

    def fetch_files(self, course_id: str) -> [File]:
        """
        Queries the Moodle system for all the files that
        are present in a course
        @param course_id: The id of the course for which you want to enquire.
        @return: A list of Files
        """

        # first get the assignments
        assignments = self.fetch_assignments(course_id)

        data = {
            'courseid': course_id
        }
        course_sections = self.request_helper.get_REST(
            'core_course_get_contents', data)

        files = self._get_files_in_sections(course_sections, assignments)

        return files
