from moodle_connector.request_helper import RequestHelper


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


    def fetch_courses(self, userid : str) -> [str]:

        data = {
            'userid':  userid
        }

        result = self.request_helper.get_REST('core_enrol_get_users_courses', data)
       

        results = []
        for course in result:
            results.append({
                "id" : course.get("id", ""),
                "fullname" : course.get("fullname", "")
                })

        return results


    def fetch_files(self, course_id: str) -> {str: (str , str)}:
        data = {
            'courseid':  course_id
        }

        result = self.request_helper.get_REST('core_course_get_contents', data)
        
        files = []

        for section in result:
            section_name = section.get("name", "")
            section_modules = section.get("modules", [])

            for module in section_modules:
                module_name = module.get("name", "")
                module_modname = module.get("modname", "")

                module_contents = module.get("contents", [])

                if (module_modname == "resource" or module_modname == "folder"):
                    for content in module_contents:
                        content_type = content.get("type", "")
                        content_filename = content.get("filename", "")
                        content_filepath = content.get("filepath", "")
                        content_filesize = content.get("filesize", "")
                        content_fileurl = content.get("fileurl", "")
                        content_timemodified = content.get("timemodified", "")
                        content_isexternalfile = content.get("isexternalfile", "")


                        files.append({
                            "section_name" : section_name,
                            "module_name" : module_name,
                            "module_modname" : module_modname,
                            "content_type" : content_type,
                            "content_filename" : content_filename,
                            "content_filepath" : content_filepath,
                            "content_filesize" : content_filesize,
                            "content_fileurl" : content_fileurl,
                            "content_timemodified" : content_timemodified,
                            "content_isexternalfile" : content_isexternalfile
                        })
        return files


