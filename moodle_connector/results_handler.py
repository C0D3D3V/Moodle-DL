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
                       course.get("fullname", ""))
            )
        return results

    def fetch_files(self, course_id: str) -> [File]:
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
                        module_modname == "folder"):
                    for content in module_contents:
                        content_type = content.get("type", "")
                        content_filename = content.get("filename", "")
                        content_filepath = content.get("filepath", "")
                        content_filesize = int(content.get("filesize", 0))
                        content_fileurl = content.get("fileurl", "")
                        content_timemodified = int(
                            content.get("timemodified", 0))
                        content_isexternalfile = bool(content.get(
                            "isexternalfile", False))

                        files.append(File(module_id=module_id,
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
