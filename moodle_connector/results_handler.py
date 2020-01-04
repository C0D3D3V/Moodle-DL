from moodle_connector.request_helper import RequestHelper
from utils.state_recorder import Course, File


class ResultsHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper):
        self.request_helper = request_helper

    def fetch_userid(self) -> [str]:
        result = self.request_helper.get_REST('core_webservice_get_site_info')

        if ("userid" not in result):
            raise RuntimeError(
                'Error could not receive your user ID!')

        return result.get("userid", "")

    def fetch_courses(self, userid: str) -> [Course]:

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

    def fetch_files(self, course_id: str) -> [File]:

        # first get the assignments
        assign_data = {
            'courseids[0]': course_id
        }

        assign_result = self.request_helper.get_REST(
            'mod_assign_get_assignments', assign_data)

        assign_courses = assign_result.get('courses', [])

        # normaly there is only on course with exactly the id
        # of course_id but who knows
        matched_assign_course = None
        for assign_course in assign_courses:
            assign_course_id = assign_course.get("id", 0)
            if(assign_course_id == course_id):
                matched_assign_course = assign_course
                break

        data = {
            'courseid': course_id
        }
        result = self.request_helper.get_REST('core_course_get_contents', data)

        files = []

        for section in result:
            section_name = section.get("name", "")
            section_modules = section.get("modules", [])

            for module in section_modules:
                module_name = module.get("name", "")
                module_modname = module.get("modname", "")
                module_id = int(module.get("id", 0))

                module_contents = module.get("contents", [])

                if (module_modname == "resource" or
                        module_modname == "folder" or module_modname == "url"):
                    for content in module_contents:
                        content_type = content.get("type", "")
                        content_filename = content.get("filename", "")
                        content_filepath = content.get("filepath", "")
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
                elif (module_modname == "assign"):
                    # find assign with same module_id
                    if (matched_assign_course is None):
                        continue

                    assignments = matched_assign_course.get('assignments', [])

                    for assignment in assignments:
                        assignment_id = assignment.get('cmid', 0)
                        if (assignment_id == module_id):
                            assignment_files = assignment.get(
                                'introattachments', [])

                            for assignment_file in assignment_files:
                                content_type = 'assign_file'
                                content_filename = assignment_file.get(
                                    "filename", "")
                                content_filepath = assignment_file.get(
                                    "filepath", "")
                                content_filesize = int(
                                    assignment_file.get("filesize", 0))
                                content_fileurl = assignment_file.get(
                                    "fileurl", "")
                                content_timemodified = int(
                                    assignment_file.get("timemodified", 0))
                                content_isexternalfile = bool(
                                    assignment_file.get(
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
                            break

        return files
