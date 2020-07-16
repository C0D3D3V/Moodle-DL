import re
import logging
import hashlib

from moodle_connector.request_helper import RequestHelper
from state_recorder.file import File


class ResultsHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper):
        self.request_helper = request_helper
        # oldest supported Moodle version
        self.version = 2011120500

    def setVersion(self, version: int):
        self.version = version

        logging.debug('Detected moodle version: %d' % (version))

    @staticmethod
    def _should_download_course(course_id: int, download_course_ids: [int], dont_download_course_ids: [int]) -> bool:
        """
        Checks if a course is in White-list and not in Blacklist
        """
        inBlacklist = course_id in dont_download_course_ids
        inWhitelist = course_id in download_course_ids or len(download_course_ids) == 0

        return inWhitelist and not inBlacklist

    def _get_files_in_sections(self, course_sections: []) -> [File]:
        """
        Iterates over all sections of a course to find files (or modules).
        @param course_sections: The course object returned by Moodle,
                                containing the sections of the course.
        @return: A list of files of the course.
        """
        files = []
        for section in course_sections:
            section_name = section.get("name", "")
            section_modules = section.get("modules", [])
            section_summary = section.get("summary", "")
            if section_summary is not None and section_summary != "":
                files += self._handle_description(
                    section_name, "Section summary", "section_summary", 0, section_summary
                )

            files += self._get_files_in_modules(section_name, section_modules)

        return files

    def _get_files_in_modules(self, section_name: str, section_modules: []) -> [File]:
        """
        Iterates over all modules to find files (or content) in them.
        @param section_name: The name of the section to be iterated over.
        @param section_modules: The modules of the section.
        @return: A list of files of the section.
        """
        files = []
        for module in section_modules:
            module_name = module.get("name", "")
            module_modname = module.get("modname", "")
            module_id = module.get("id", 0)

            module_contents = module.get("contents", [])

            module_description = module.get("description", None)

            if module_description is not None and self.download_descriptions is True:
                files += self._handle_description(
                    section_name, module_name, module_modname, module_id, module_description
                )

            if module_modname in ["resource", "folder", "url", "page"]:
                files += self._handle_files(section_name, module_name, module_modname, module_id, module_contents)

            elif module_modname == "assign":

                # find assign with same module_id
                assign = self.course_assignments.get(module_id, {})
                assign_files = assign.get('files', [])

                files += self._handle_files(section_name, module_name, module_modname, module_id, assign_files)
            elif module_modname == "data":

                # find database with same module_id
                database = self.course_databases.get(module_id, {})
                database_files = database.get('files', [])

                files += self._handle_files(section_name, module_name, module_modname, module_id, database_files)

        return files

    @staticmethod
    def _filter_changing_attributes(description: str) -> str:
        """
        Tries to filter ids and stuff,
        that is knowing to change over time in descriptions.
        """

        description = re.sub(r'id="[^"]*"', "", description)
        description = re.sub(r"id='[^']*'", "", description)
        return description

    @staticmethod
    def _handle_files(
        section_name: str, module_name: str, module_modname: str, module_id: str, module_contents: []
    ) -> [File]:
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
            content_filesize = content.get("filesize", 0)
            content_fileurl = content.get("fileurl", "")
            content_timemodified = content.get("timemodified", 0)
            content_isexternalfile = content.get("isexternalfile", False)

            if content_fileurl == "" and module_modname == "url":
                continue

            hash_description = None
            if content_type == "description":
                content_description = content.get("description", "")
                hashable_description = ResultsHandler._filter_changing_attributes(content_description)
                m = hashlib.sha1()
                m.update(hashable_description.encode('utf-8'))
                hash_description = m.hexdigest()

            new_file = File(
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
                content_isexternalfile=content_isexternalfile,
                hash=hash_description,
            )

            if content_type == "description":
                new_file.text_content = content_description

            files.append(new_file)
        return files

    @staticmethod
    def _handle_description(
        section_name: str, module_name: str, module_modname: str, module_id: str, module_description: str
    ) -> [File]:
        """
        Creates a description file
        @param module_description: The description of the module
        @params: All necessary parameters to create a file.
        @return: A list of files that exist in a module.
        """
        files = []
        content_type = "description"
        content_filename = module_name
        content_filepath = "/"
        content_filesize = len(module_description)
        content_fileurl = ""
        content_timemodified = 0
        content_isexternalfile = False

        m = hashlib.sha1()
        hashable_description = ResultsHandler._filter_changing_attributes(module_description)
        m.update(hashable_description.encode('utf-8'))
        hash_description = m.hexdigest()

        if module_modname == 'url':
            module_modname = 'url_description'

        description = File(
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
            content_isexternalfile=content_isexternalfile,
            hash=hash_description,
        )

        description.text_content = module_description

        files.append(description)

        return files

    def set_fetch_addons(self, course_assignments: {int: {int: {}}}, course_databases: {int: {int: {}}}):
        """
        Sets the optional data that will be added to the result list
         during the process.
        @params course_assignments: The dictionary of assignments per course
        @params course_databases: The dictionary of databases per course
        """
        self.course_assignments = course_assignments
        self.course_databases = course_databases

    def set_fetch_options(self, download_descriptions: bool):
        """
        Sets the possible options for a fetch operation.
        @params download_descriptions: Sets whether descriptions
                                       are to be downloaded.
        """
        self.download_descriptions = download_descriptions

    def fetch_files(self, course_id: str) -> [File]:
        """
        Queries the Moodle system for all the files that
        are present in a course
        @param course_id: The id of the course for which you want to enquirer.
        @return: A list of Files
        """

        data = {'courseid': course_id}
        course_sections = self.request_helper.post_REST('core_course_get_contents', data)

        files = self._get_files_in_sections(course_sections)

        return files
