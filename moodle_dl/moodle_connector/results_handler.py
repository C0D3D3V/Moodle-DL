import re
import html
import logging
import hashlib
import urllib.parse as urlparse

from moodle_dl.state_recorder.course import Course
from moodle_dl.state_recorder.file import File
from moodle_dl.moodle_connector.request_helper import RequestHelper


class ResultsHandler:
    """
    Fetches and parses the various endpoints in Moodle.
    """

    def __init__(self, request_helper: RequestHelper, moodle_domain: str, moodle_path: str):
        self.request_helper = request_helper
        # oldest supported Moodle version
        self.version = 2011120500
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path
        self.course_fetch_addons = {}

    def setVersion(self, version: int):
        self.version = version

        logging.debug('Detected moodle version: %d', version)

    @staticmethod
    def should_download_course(course_id: int, download_course_ids: [int], dont_download_course_ids: [int]) -> bool:
        """
        Checks if a course is in White-list and not in Blacklist
        """
        inBlacklist = course_id in dont_download_course_ids
        inWhitelist = course_id in download_course_ids or len(download_course_ids) == 0

        return inWhitelist and not inBlacklist

    @staticmethod
    def should_download_section(section_id: int, dont_download_sections_ids: [int]) -> bool:
        """
        Checks if a section is not in Blacklist
        """

        return section_id not in dont_download_sections_ids or len(dont_download_sections_ids) == 0

    def _get_files_in_sections(self, course_sections: []) -> [File]:
        """
        Iterates over all sections of a course to find files (or modules).
        @param course_sections: The course object returned by Moodle,
                                containing the sections of the course.
        @return: A list of files of the course.
        """
        files = []
        for section in course_sections:
            section_id = section.get('id', 0)
            section_name = section.get('name', '')
            section_modules = section.get('modules', [])
            section_summary = section.get('summary', '')
            if section_summary is not None and section_summary != '':
                files += self._handle_description(
                    section_name, section_id, 'Section summary', 'section_summary', 0, section_summary
                )

            files += self._get_files_in_modules(section_name, section_id, section_modules)

        return files

    def _get_files_in_modules(self, section_name: str, section_id: int, section_modules: []) -> [File]:
        """
        Iterates over all modules to find files (or content) in them.
        @param section_name: The name of the section to be iterated over.
        @param section_id: The id of the section to be iterated over.
        @param section_modules: The modules of the section.
        @return: A list of files of the section.
        """
        files = []
        for module in section_modules:
            module_name = module.get('name', '')
            module_modname = module.get('modname', '')
            module_url = module.get('url', '')
            module_id = module.get('id', 0)

            module_contents = module.get('contents', [])

            module_description = module.get('description', None)

            # handle not supported modules that results in an index.html special
            if module_modname in ['moodecvideo']:
                module_modname = 'index_mod-' + module_modname

            if module_modname in ['page'] and self.version < 2017051500:
                module_modname = 'index_mod-' + module_modname

            if module_description is not None and module_modname not in [
                'page',
                'forum',
                'database',
                'lesson',
                'quiz',
                'workshop',
                'assign',
            ]:
                # Handle descriptions of Files, Labels and all that we do not handle in seperate modules
                files += self._handle_description(
                    section_name, section_id, module_name, module_modname, module_id, module_description
                )

            if module_modname in ['kalvidres', 'helixmedia', 'lti']:
                module_modname = 'cookie_mod-' + module_modname
                files += self._handle_cookie_mod(
                    section_name, section_id, module_name, module_modname, module_id, module_url
                )

            elif module_modname.startswith(('resource', 'akarifolder', 'url', 'index_mod')):
                files += self._handle_files(
                    section_name, section_id, module_name, module_modname, module_id, module_contents
                )

            elif module_modname.startswith(('folder')):
                # Modules whose content is directly linked, and additional content exists in their module.
                if module_modname in self.course_fetch_addons:
                    # find addon with same module_id
                    addon = self.course_fetch_addons.get(module_modname, {}).get(module_id, {})
                    addon_files = addon.get('files', [])
                    module_contents += addon_files

                files += self._handle_files(
                    section_name, section_id, module_name, module_modname, module_id, module_contents
                )

            elif module_modname in self.course_fetch_addons:
                # find addon with same module_id
                addon = self.course_fetch_addons.get(module_modname, {}).get(module_id, {})
                addon_files = addon.get('files', [])

                files += self._handle_files(
                    section_name, section_id, module_name, module_modname, module_id, addon_files
                )
            else:
                logging.debug('Got unhandled module: name=%s mod=%s url=%s', module_name, module_modname, module_url)

        return files

    @staticmethod
    def _filter_changing_attributes(description: str) -> str:
        """
        Tries to filter ids and stuff,
        that is knowing to change over time in descriptions.
        """
        if description is None:
            return ''

        if not isinstance(description, str):
            return description

        # to avoid changing encodings (see issue #96) we unencode and unquote everything
        description = html.unescape(description)
        description = urlparse.unquote(description)

        # ids can change very quickly
        description = re.sub(r'id="[^"]*"', "", description)
        description = re.sub(r"id='[^']*'", "", description)

        # Embedded images from Moodle can change their timestemp (is such a theme feature)
        # We change every timestemp to -1 the default.
        description = re.sub(
            r"\/theme\/image.php\/(\w+)\/(\w+)\/\d+\/",
            r"/theme/image.php/\g<1>/\g<2>/-1/",
            description,
        )

        # some folder downloads inside a description file may have some session key inside which will always be
        # different. We remove it, to prevent always tagging this file as "modified".
        description = re.sub(r'<input type="hidden" name="sesskey" value="[0-9a-zA-Z]*" \/>', "", description)
        description = re.sub(r"<input type='hidden' name='sesskey' value='[0-9a-zA-Z]*' \/>", "", description)

        return description

    def _find_all_urls(
        self,
        section_name: str,
        section_id: int,
        module_name: str,
        module_modname: str,
        module_id: str,
        content_filepath: str,
        content_html: str,
        no_search_for_moodle_urls: bool,
        filter_urls_containing: [str],
    ) -> [File]:
        """Parses a html string to find all urls in it. Then it creates for every url a file entry.

        Args:
            section_name (str): The name of the course section
            section_id (int): The id of the course section
            module_name (str): Name of the Module
            module_modname (str): Type of the Module
            module_id (str): Module Id
            content_html (str): The html string

        Returns:
            [File]: A list of created file entries.
        """

        urls = list(set(re.findall(r'href=[\'"]?([^\'" >]+)', content_html)))
        urls += list(set(re.findall(r'<a[^>]*>(http[^<]*)<\/a>', content_html)))
        urls += list(set(re.findall(r'src=[\'"]?([^\'" >]+)', content_html)))
        urls = list(set(urls))

        result = []
        original_module_modname = module_modname

        for url in urls:
            if url == '':
                continue

            # To avoid different encodings and quotes and so that youtube-dl downloads correctly
            # (See issues #96 and #103), we remove all encodings.
            url = html.unescape(url)
            url = urlparse.unquote(url)

            url_parts = urlparse.urlparse(url)
            if (
                url_parts.hostname == self.moodle_domain
                or url_parts.netloc == self.moodle_domain
                and no_search_for_moodle_urls
            ):
                # Skip if no moodle urls should be found
                continue

            for filter_str in filter_urls_containing:
                # Skip url if a filter matches
                if url.find(filter_str) >= 0:
                    continue

            if url_parts.hostname == self.moodle_domain and url_parts.path.find('/theme/image.php/') >= 0:
                url = re.sub(
                    r"\/theme\/image.php\/(\w+)\/(\w+)\/\d+\/",
                    r"/theme/image.php/\g<1>/\g<2>/-1/",
                    url,
                )

            module_modname = 'url-description-' + original_module_modname

            if url_parts.hostname == self.moodle_domain and url_parts.path.find('/webservice/') >= 0:
                module_modname = 'index_mod-description-' + original_module_modname

            elif url_parts.hostname == self.moodle_domain:
                module_modname = 'cookie_mod-description-' + original_module_modname

            fist_guess_filename = url
            if fist_guess_filename.startswith('data:image/'):
                file_extension_guess = 'png'
                if len(fist_guess_filename.split(';')) > 1:
                    if len(fist_guess_filename.split(';')[0].split('/')) > 1:
                        file_extension_guess = fist_guess_filename.split(';')[0].split('/')[1]

                fist_guess_filename = 'inline_image.' + file_extension_guess

            if len(fist_guess_filename) > 254:
                fist_guess_filename = fist_guess_filename[:254]

            new_file = File(
                module_id=module_id,
                section_name=section_name,
                section_id=section_id,
                module_name=module_name,
                content_filepath=content_filepath,
                content_filename=fist_guess_filename,
                content_fileurl=url,
                content_filesize=0,
                content_timemodified=0,
                module_modname=module_modname,
                content_type='description-url',
                content_isexternalfile=True,
            )
            result.append(new_file)
        return result

    def _handle_cookie_mod(
        self, section_name: str, section_id: int, module_name: str, module_modname: str, module_id: str, module_url: str
    ) -> [File]:
        """
        Creates a list of files out of a cookie module
        @param module_url: The url to the cookie module.
        @params: All necessary parameters to create a file.
        @return: A list of files that were created out of the module.
        """
        files = []

        new_file = File(
            module_id=module_id,
            section_name=section_name,
            section_id=section_id,
            module_name=module_name,
            content_filepath='/',
            content_filename=module_name,
            content_fileurl=module_url,
            content_filesize=0,
            content_timemodified=0,
            module_modname=module_modname,
            content_type='cookie_mod',
            content_isexternalfile=True,
        )

        files.append(new_file)
        return files

    def _handle_files(
        self,
        section_name: str,
        section_id: int,
        module_name: str,
        module_modname: str,
        module_id: str,
        module_contents: [],
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
            content_type = content.get('type', '')
            content_filename = content.get('filename', '')
            content_filepath = content.get('filepath', '/')
            if content_filepath is None:
                content_filepath = '/'
            content_filesize = content.get('filesize', 0)
            content_fileurl = content.get('fileurl', '')
            content_timemodified = content.get('timemodified', 0)
            content_isexternalfile = content.get('isexternalfile', False)

            # description related
            content_description = content.get('description', '')
            no_search_for_urls = content.get('no_search_for_urls', False)
            no_search_for_moodle_urls = content.get('no_search_for_moodle_urls', False)
            filter_urls_during_search_containing = content.get('filter_urls_during_search_containing', [])
            content_no_hash = content.get('no_hash', False)

            # html related
            content_html = content.get('html', '')

            if content_fileurl == '' and module_modname.startswith(('url', 'index_mod', 'cookie_mod')):
                continue

            # Add the extention condition to avoid renaming pdf files or other downloaded content from moodle pages.
            if module_modname.startswith('index_mod') and content_filename.endswith('.html'):
                content_filename = module_name

            hash_description = None
            if content_type == 'description' and not content_no_hash:
                hashable_description = ResultsHandler._filter_changing_attributes(content_description)
                m = hashlib.sha1()
                m.update(hashable_description.encode('utf-8'))
                hash_description = m.hexdigest()

            new_file = File(
                module_id=module_id,
                section_name=section_name,
                section_id=section_id,
                module_name=module_name,
                content_filepath=content_filepath,
                content_filename=content_filename,
                content_fileurl=content_fileurl,
                content_filesize=content_filesize,
                content_timemodified=content_timemodified,
                module_modname=module_modname,
                content_type=content_type,
                content_isexternalfile=content_isexternalfile,
                file_hash=hash_description,
            )

            if content_type == 'description':
                new_file.text_content = content_description
                content_html = content_description
            if content_type == 'html':
                new_file.html_content = content_html

            if content_type in ['description', 'html'] and not no_search_for_urls:
                files += self._find_all_urls(
                    section_name,
                    section_id,
                    module_name,
                    module_modname,
                    module_id,
                    content_filepath,
                    content_html,
                    no_search_for_moodle_urls,
                    filter_urls_during_search_containing,
                )

            files.append(new_file)
        return files

    def _handle_description(
        self,
        section_name: str,
        section_id: int,
        module_name: str,
        module_modname: str,
        module_id: str,
        module_description: str,
    ) -> [File]:
        """
        Creates a description file
        @param module_description: The description of the module
        @params: All necessary parameters to create a file.
        @return: A list of files that exist in a module.
        """
        files = []
        content_type = 'description'
        content_filename = module_name
        content_filepath = '/'
        content_filesize = len(module_description)
        content_fileurl = ''
        content_timemodified = 0
        content_isexternalfile = False

        m = hashlib.sha1()
        hashable_description = ResultsHandler._filter_changing_attributes(module_description)
        m.update(hashable_description.encode('utf-8'))
        hash_description = m.hexdigest()

        if module_modname.startswith(('url', 'index_mod')):
            module_modname = 'url_description'

        description = File(
            module_id=module_id,
            section_name=section_name,
            section_id=section_id,
            module_name=module_name,
            content_filepath=content_filepath,
            content_filename=content_filename,
            content_fileurl=content_fileurl,
            content_filesize=content_filesize,
            content_timemodified=content_timemodified,
            module_modname=module_modname,
            content_type=content_type,
            content_isexternalfile=content_isexternalfile,
            file_hash=hash_description,
        )

        no_search_for_moodle_urls = False
        filter_urls_during_search_containing = []

        description.text_content = module_description
        files += self._find_all_urls(
            section_name,
            section_id,
            module_name,
            module_modname,
            module_id,
            content_filepath,
            module_description,
            no_search_for_moodle_urls,
            filter_urls_during_search_containing,
        )

        files.append(description)

        return files

    def set_fetch_addons(self, course_fetch_addons: {}):
        """
        Sets the optional data that will be added to the result list
         during the process.
        @params course_fetch_addons: The dictionary of assignments, databases, forums, quizzes, lessons,
         workshops, pages, ... per course
        """
        self.course_fetch_addons = course_fetch_addons

    def fetch_files(self, course: Course) -> [File]:
        """
        Queries the Moodle system for all the files that
        are present in a course
        @param course_id: The id of the course for which you want to enquirer.
        @return: A list of Files
        """

        data = {'courseid': course.id}
        course_sections = self.request_helper.post_REST('core_course_get_contents', data)

        files = self._get_files_in_sections(course_sections)

        return files
