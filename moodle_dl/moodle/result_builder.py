import hashlib
import html
import logging
import mimetypes
import re
import urllib.parse as urlparse

from typing import Dict, List

from moodle_dl.types import Course, File, MoodleURL


class ResultBuilder:
    """
    Combines all fetched mod files and core course files to one result based on File objects
    """

    def __init__(self, moodle_url: MoodleURL, version: int, mod_plurals: Dict):
        self.version = version
        self.moodle_url = moodle_url
        self.moodle_domain = moodle_url.domain
        self.mod_plurals = mod_plurals

    def get_files_in_sections(self, course_sections: List[Dict], fetched_mods: Dict[str, Dict]) -> List[File]:
        """
        Iterates over all sections of a course to find files (or modules).
        @param course_sections: Contains the sections of the course
        @param fetched_mods: Contains the fetched mods of the course
        @return: A list of files of the course.
        """
        files = []
        for section in course_sections:
            location = {
                'section_id': section.get('id', 0),
                'section_name': section.get('name', ''),
            }
            section_modules = section.get('modules', [])
            files += self._get_files_in_modules(section_modules, fetched_mods, **location)

            section_summary = section.get('summary', '')
            if section_summary is not None and section_summary != '':
                location.update(
                    {
                        'module_id': 0,
                        'module_name': 'Section summary',
                        'module_modname': 'section_summary',
                    }
                )
                files += self._handle_description(section_summary, **location)

        files += self._get_files_not_on_main_page(fetched_mods)

        return files

    def _get_files_in_modules(self, section_modules: List, fetched_mods: Dict[str, Dict], **location) -> List[File]:
        """
        Iterates over all modules to find files (or content) in them.
        @param section_modules: The modules of the section.
        @param fetched_mods: Contains the fetched mods of the course
        @param location: contains
            section_id: int,
            section_name: str,
        @return: A list of files of the section.
        """
        files = []
        for module in section_modules:
            location['module_id'] = module.get('id', 0)
            location['module_name'] = module.get('name', '')
            location['module_modname'] = module.get('modname', '')

            module_url = module.get('url', '')
            module_contents = module.get('contents', [])
            module_description = module.get('description', None)

            # handle not supported modules that results in an index.html special
            if location['module_modname'] in ['moodecvideo']:
                location['module_modname'] = 'index_mod-' + location['module_modname']

            if location['module_modname'] in ['page'] and self.version < 2017051500:
                # legacy pages
                location['module_modname'] = 'index_mod-' + location['module_modname']

            if module_description is not None and location['module_modname'] not in fetched_mods:
                # Handle descriptions of Files, Labels and all mods that we do not handle in separately
                files += self._handle_description(module_description, **location)

            if location['module_modname'] in ['kalvidres', 'helixmedia', 'lti']:
                location['module_modname'] = 'cookie_mod-' + location['module_modname']
                files += self._handle_cookie_mod(module_url, **location)

            elif location['module_modname'].startswith(('resource', 'akarifolder', 'url', 'index_mod')):
                files += self._handle_files(module_contents, **location)

            elif location['module_modname'].startswith(('folder')):
                # Modules whose content is directly linked, and additional content exists in their module.
                if location['module_modname'] in fetched_mods:
                    # find mod module with same module_id
                    mod = fetched_mods.get(location['module_modname'], {}).get(location['module_id'], {})
                    mod['on_main_page'] = True
                    mod_files = mod.get('files', [])
                    module_contents += mod_files

                files += self._handle_files(module_contents, **location)

            elif location['module_modname'] in fetched_mods:
                # find mod module with same module_id
                mod = fetched_mods.get(location['module_modname'], {}).get(location['module_id'], {})
                mod['on_main_page'] = True
                mod_files = mod.get('files', [])
                files += self._handle_files(mod_files, **location)
            else:
                if location['module_modname'] not in ['label']:
                    logging.debug(
                        'Got unhandled module: name=%s mod=%s url=%s',
                        location['module_name'],
                        location['module_modname'],
                        module_url,
                    )

        return files

    def get_mod_plural_name(self, mod_name: str) -> str:
        if mod_name in self.mod_plurals:
            return self.mod_plurals[mod_name].capitalize()
        return mod_name.capitalize()

    def _get_files_not_on_main_page(self, fetched_mods: Dict[str, Dict]) -> List[File]:
        """
        Iterates over all mods to find files (or content) that are not listed on the main page.
        @param fetched_mods: Contains the fetched mods of the course
        @return: A list of files of mod modules not on the main page.
        """
        files = []
        for mod_name, mod_modules in fetched_mods.items():
            location = {
                'section_id': -1,
                'section_name': f"{self.get_mod_plural_name(mod_name)} not on main page",
            }

            for _, module in mod_modules.items():
                if 'on_main_page' in module:
                    continue
                location.update(
                    {
                        'module_id': module.get('id', 0),
                        'module_name': module.get('name', ''),
                        'module_modname': mod_name,
                    }
                )

                # Handle not supported modules that results in an index.html special
                if location['module_modname'] in ['page'] and self.version < 2017051500:
                    location['module_modname'] = 'index_mod-' + location['module_modname']

                files += self._handle_files(module.get('files', []), **location)

        return files

    @staticmethod
    def filter_changing_attributes(description: str) -> str:
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
        content_html: str,
        no_search_for_moodle_urls: bool,
        filter_urls_containing: List[str],
        **location,
    ) -> List[File]:
        """Parses a html string to find all urls in it. Then it creates for every url a file entry.

        @param location: contains
            section_id: int,
            section_name: str,
            module_id: str,
            module_name: str,
            module_modname: str,
            content_filepath: str,
        """

        # TODO: Also parse name or alt of an link to get a better name for URLs
        urls = list(set(re.findall(r'href=[\'"]?([^\'" >]+)', content_html)))
        urls += list(set(re.findall(r'<a[^>]*>(http[^<]*)<\/a>', content_html)))
        urls += list(set(re.findall(r'src=[\'"]?([^\'" >]+)', content_html)))
        urls += list(set(re.findall(r'data=[\'"]?([^\'" >]+)', content_html)))
        urls = list(set(urls))

        result = []
        original_module_modname = location['module_modname']

        for url in urls:
            if url == '':
                continue

            # To avoid different encodings and quotes and so that yt-dlp downloads correctly
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

            location['module_modname'] = 'url-description-' + original_module_modname

            if url_parts.hostname == self.moodle_domain and url_parts.path.find('/webservice/') >= 0:
                location['module_modname'] = 'index_mod-description-' + original_module_modname

            elif url_parts.hostname == self.moodle_domain:
                location['module_modname'] = 'cookie_mod-description-' + original_module_modname

            if url.startswith('data:'):
                # Schema: data:[<mime type>][;charset=<Charset>][;base64],<Data>
                embedded_data = url.split(',', 1)[1]
                mime_type = url.split(':', 1)[1].split(',', 1)[0].split(';')[0]
                media_type = mime_type.split('/', 1)[0]
                file_extension_guess = mimetypes.guess_extension(mime_type, strict=False)
                if file_extension_guess is None:
                    file_extension_guess = f'.{media_type}'
                m = hashlib.sha1()
                if len(embedded_data) > 100000:
                    # To improve speed hash only first 100kb if file is bigger
                    m.update(embedded_data[:100000].encode(encoding='utf-8'))
                else:
                    m.update(embedded_data.encode(encoding='utf-8'))
                short_data_hash = m.hexdigest()

                fist_guess_filename = f'embedded_{media_type} ({short_data_hash}){file_extension_guess}'
            else:
                fist_guess_filename = url
                if len(fist_guess_filename) > 254:
                    fist_guess_filename = fist_guess_filename[:254]

            result.append(
                File(
                    **location,
                    content_filename=fist_guess_filename,
                    content_fileurl=url,
                    content_filesize=0,
                    content_timemodified=0,
                    content_type='description-url',
                    content_isexternalfile=True,
                )
            )
        return result

    def _handle_cookie_mod(self, module_url: str, **location) -> List[File]:
        """
        Create a list of files out of a cookie module
        @param module_url: The url to the cookie module.
        @param location: contains
            section_id: int,
            section_name: str,
            module_id: str,
            module_name: str,
            module_modname: str,
        """
        return [
            File(
                **location,
                content_filepath='/',
                content_filename=location['module_name'],
                content_fileurl=module_url,
                content_filesize=0,
                content_timemodified=0,
                content_type='cookie_mod',
                content_isexternalfile=True,
            )
        ]

    def _handle_files(self, module_contents: List, **location) -> List[File]:
        """
        Create a list of all files in a module
        @param module_contents: The list of content of the module
        @param location: contains
            section_id: int,
            section_name: str,
            module_id: str,
            module_name: str,
            module_modname: str,
        """
        files = []
        for content in module_contents:
            content_type = content.get('type', '')
            content_filename = content.get('filename', '')
            content_filepath = content.get('filepath', '/') or '/'
            content_fileurl = content.get('fileurl', '')

            content_description = content.get('description', '')
            content_html = content.get('html', '')

            if content_fileurl == '' and location['module_modname'].startswith(('url', 'index_mod', 'cookie_mod')):
                continue

            # Add the extention condition to avoid renaming pdf files or other downloaded content from moodle pages.
            if location['module_modname'].startswith('index_mod') and content_filename.endswith('.html'):
                content_filename = location['module_name']

            hash_description = None
            if content_type == 'description' and not content.get('no_hash', False):
                hashable_description = self.filter_changing_attributes(content_description)
                m = hashlib.sha1()
                m.update(hashable_description.encode('utf-8'))
                hash_description = m.hexdigest()

            new_file = File(
                **location,
                content_filepath=content_filepath,
                content_filename=content_filename,
                content_fileurl=content_fileurl,
                content_filesize=content.get('filesize', 0),
                content_timemodified=content.get('timemodified', 0),
                content_type=content_type,
                content_isexternalfile=content.get('isexternalfile', False),
                file_hash=hash_description,
            )

            if content_type == 'description':
                new_file.text_content = content_description
                content_html = content_description
            if content_type == 'html':
                new_file.html_content = content_html

            if content_type in ['description', 'html'] and not content.get('no_search_for_urls', False):
                files += self._find_all_urls(
                    content_html,
                    no_search_for_moodle_urls=content.get('no_search_for_moodle_urls', False),
                    filter_urls_containing=content.get('filter_urls_during_search_containing', []),
                    **location,
                    content_filepath=content_filepath,
                )

            files.append(new_file)
        return files

    def _handle_description(
        self,
        module_description: str,
        **location,
    ) -> List[File]:
        """
        Creates a description file
        @param module_description: The description of the module
        @param location: contains
            section_id: int,
            section_name: str,
            module_id: str,
            module_name: str,
            module_modname: str,
        @return: A list of files containing that description and URLs in that description.
        """
        files = []
        content_filepath = '/'

        m = hashlib.sha1()
        hashable_description = self.filter_changing_attributes(module_description)
        m.update(hashable_description.encode('utf-8'))
        hash_description = m.hexdigest()

        if location['module_modname'].startswith(('url', 'index_mod')):
            location['module_modname'] = 'url_description'

        description = File(
            **location,
            content_filepath=content_filepath,
            content_filename=location['module_name'],
            content_fileurl='',
            content_filesize=len(module_description),
            content_timemodified=0,
            content_type='description',
            content_isexternalfile=False,
            file_hash=hash_description,
        )
        description.text_content = module_description
        files.append(description)

        files += self._find_all_urls(
            module_description,
            no_search_for_moodle_urls=False,
            filter_urls_containing=[],
            **location,
            content_filepath=content_filepath,
        )

        return files

    def add_files_to_courses(
        self,
        courses: List[Course],
        course_cores: Dict[int, List[Dict]],
        fetched_mods_files: Dict[str, Dict],
    ):
        """
        @param fetched_mods_files:
            Dictionary of all fetched mod modules files, indexed by mod name, then by courses, then module id
        """
        for course in courses:
            course_sections = course_cores.get(course.id, [])

            fetched_mods = {}
            for mod_name, mod_courses in fetched_mods_files.items():
                fetched_mods[mod_name] = mod_courses.get(course.id, {})

            course.files = self.get_files_in_sections(course_sections, fetched_mods)
