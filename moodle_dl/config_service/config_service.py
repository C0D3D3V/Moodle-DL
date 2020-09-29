import os
import shutil

from moodle_dl.utils import cutie
from moodle_dl.utils.logger import Log
from moodle_dl.state_recorder.course import Course
from moodle_dl.config_service.config_helper import ConfigHelper
from moodle_dl.moodle_connector.results_handler import ResultsHandler
from moodle_dl.moodle_connector.first_contact_handler import FirstContactHandler
from moodle_dl.moodle_connector.request_helper import RequestRejectedError, RequestHelper


class ConfigService:
    def __init__(self, config_helper: ConfigHelper, storage_path: str, skip_cert_verify: bool = False):
        self.config_helper = config_helper
        self.storage_path = storage_path
        self.skip_cert_verify = skip_cert_verify

    def interactively_acquire_config(self):
        """
        Guides the user through the process of configuring the downloader
        for the courses to be downloaded and in what way
        """

        token = self.config_helper.get_token()
        moodle_domain = self.config_helper.get_moodle_domain()
        moodle_path = self.config_helper.get_moodle_path()

        request_helper = RequestHelper(moodle_domain, moodle_path, token, self.skip_cert_verify)
        first_contact_handler = FirstContactHandler(request_helper)

        courses = []
        try:

            userid, version = first_contact_handler.fetch_userid_and_version()

            courses = first_contact_handler.fetch_courses(userid)

        except (RequestRejectedError, ValueError, RuntimeError) as error:
            raise RuntimeError('Error while communicating with the Moodle System! (%s)' % (error))

        self._select_courses_to_download(courses)
        self._set_options_of_courses(courses)
        self._select_should_download_submissions()
        self._select_should_download_descriptions()
        self._select_should_download_links_in_descriptions()
        self._select_should_download_databases()
        self._select_should_download_linked_files()
        self._select_should_load_default_filename_character_map()

    def _select_courses_to_download(self, courses: [Course]):
        """
        Asks the user for the courses that should be downloaded.
        @param courses: All available courses
        """
        download_course_ids = self.config_helper.get_download_course_ids()
        dont_download_course_ids = self.config_helper.get_dont_download_course_ids()

        print('')
        Log.info(
            'To avoid downloading all the Moodle courses you are enrolled in, you can select which ones you want'
            + ' to download here. '
        )
        print('')

        choices = []
        defaults = []
        for i, course in enumerate(courses):
            choices.append(('%5i\t%s' % (course.id, course.fullname)))

            if ResultsHandler.should_download_course(course.id, download_course_ids, dont_download_course_ids):
                defaults.append(i)

        Log.special('Which of the courses should be downloaded?')
        Log.info('[You can select with the space bar and confirm your selection with the enter key]')
        print('')
        selected_courses = cutie.select_multiple(options=choices, ticked_indices=defaults)

        download_course_ids = []
        for i, course in enumerate(courses):
            if i in selected_courses:
                download_course_ids.append(course.id)

        self.config_helper.set_property('download_course_ids', download_course_ids)

        self.config_helper.remove_property('dont_download_course_ids')

    def _set_options_of_courses(self, courses: [Course]):
        """
        Let the user set special options for every single course
        """
        download_course_ids = self.config_helper.get_download_course_ids()
        dont_download_course_ids = self.config_helper.get_dont_download_course_ids()

        self.section_seperator()
        Log.info(
            'You can set special settings for every single course.\n'
            + 'You can set these options:\n'
            + ' - A different name for the course\n'
            + ' - If a directory structure should be created for the course'
            + ' [create_directory_structure (cfs)].'
        )
        print('')

        while True:

            choices = []
            choices_courses = []

            options_of_courses = self.config_helper.get_options_of_courses()

            choices.append('None')

            for course in courses:
                if ResultsHandler.should_download_course(course.id, download_course_ids, dont_download_course_ids):

                    current_course_settings = options_of_courses.get(str(course.id), None)

                    # create default settings
                    if current_course_settings is None:
                        current_course_settings = {
                            'original_name': course.fullname,
                            'overwrite_name_with': None,
                            'create_directory_structure': True,
                        }

                    # create list of options
                    overwrite_name_with = current_course_settings.get('overwrite_name_with', None)

                    create_directory_structure = current_course_settings.get('create_directory_structure', True)

                    if overwrite_name_with is not None and overwrite_name_with != course.fullname:
                        choices.append(
                            (
                                '%5i\t%s (%s) cfs=%s'
                                % (course.id, overwrite_name_with, course.fullname, create_directory_structure)
                            )
                        )

                    else:
                        choices.append(('%5i\t%s  cfs=%s' % (course.id, course.fullname, create_directory_structure)))

                    choices_courses.append(course)

            print('')
            Log.special('For which of the following course do you want to change the settings?')
            print('[Confirm your selection with the Enter key]')
            print('')

            selected_course = cutie.select(options=choices)
            if selected_course == 0:
                break
            else:
                self._change_settings_of(choices_courses[selected_course - 1], options_of_courses)

    def _change_settings_of(self, course: Course, options_of_courses: {}):
        """
        Ask for a new Name for the course.
        Then asks if a file structure should be created.
        """

        current_course_settings = options_of_courses.get(str(course.id), None)

        # create default settings
        if current_course_settings is None:
            current_course_settings = {
                'original_name': course.fullname,
                'overwrite_name_with': None,
                'create_directory_structure': True,
            }

        changed = False

        # Ask for new name
        overwrite_name_with = input(
            Log.special_str('Enter a new name for this Course [leave blank for "%s"]:   ' % (course.fullname,))
        )

        if overwrite_name_with == '':
            overwrite_name_with = None

        if (
            overwrite_name_with != course.fullname
            and current_course_settings.get('overwrite_name_with', None) != overwrite_name_with
        ):
            current_course_settings.update({'overwrite_name_with': overwrite_name_with})
            changed = True

        # Ask if a file structure should be created
        create_directory_structure = current_course_settings.get('create_directory_structure', True)

        create_directory_structure = cutie.prompt_yes_or_no(
            Log.special_str('Should a directory structure be created for this course?'),
            default_is_yes=create_directory_structure,
        )

        if create_directory_structure is not current_course_settings.get('create_directory_structure', True):
            changed = True
            current_course_settings.update({'create_directory_structure': create_directory_structure})

        if changed:
            options_of_courses.update({str(course.id): current_course_settings})
            self.config_helper.set_property('options_of_courses', options_of_courses)

    def _select_should_download_submissions(self):
        """
        Asks the user if submissions should be downloaded
        """
        download_submissions = self.config_helper.get_download_submissions()

        self.section_seperator()
        Log.info(
            'Submissions are files that you or a teacher have uploaded'
            + ' to your assignments. Moodle does not provide an'
            + ' interface for downloading information from all'
            + ' submissions to a course at once.'
        )
        Log.warning('Therefore, it may be slow to monitor changes to submissions.')
        print('')

        download_submissions = cutie.prompt_yes_or_no(
            Log.special_str('Do you want to download submissions of your assignments?'),
            default_is_yes=download_submissions,
        )

        self.config_helper.set_property('download_submissions', download_submissions)

    def _select_should_download_databases(self):
        """
        Asks the user if databases should be downloaded
        """
        download_databases = self.config_helper.get_download_databases()

        self.section_seperator()
        Log.info(
            'In the database module of Moodle data can be stored'
            + ' structured with information. Often it is also'
            + ' possible for students to upload data there.  Because'
            + ' the implementation of the downloader has not yet been'
            + ' optimized at this point, it is optional to download the'
            + ' databases. Currently only files are downloaded, thumbails'
            + ' are ignored.'
        )
        print('')

        download_databases = cutie.prompt_yes_or_no(
            Log.special_str('Do you want to download databases of your courses?'), default_is_yes=download_databases
        )

        self.config_helper.set_property('download_databases', download_databases)

    def _select_should_download_descriptions(self):
        """
        Asks the user if descriptions should be downloaded
        """
        download_descriptions = self.config_helper.get_download_descriptions()

        self.section_seperator()
        Log.info(
            'In Moodle courses, descriptions can be added to all kinds'
            + ' of resources, such as files, tasks, assignments or simply'
            + ' free text. These descriptions are usually unnecessary to'
            + ' download because you have already read the information or'
            + ' know it from context. However, there are situations where'
            + ' it might be interesting to download these descriptions. The'
            + ' descriptions are created as Markdown files and can be'
            + ' deleted as desired.'
        )
        Log.debug(
            'Creating the description files does not take extra time, but they can be annoying'
            + ' if they only contain unnecessary information.'
        )

        print('')

        download_descriptions = cutie.prompt_yes_or_no(
            Log.special_str('Would you like to download descriptions of the courses you have selected?'),
            default_is_yes=download_descriptions,
        )

        self.config_helper.set_property('download_descriptions', download_descriptions)

    def _select_should_download_links_in_descriptions(self):
        """
        Asks the user if links in descriptions should be downloaded
        """
        download_links_in_descriptions = self.config_helper.get_download_links_in_descriptions()

        self.section_seperator()
        Log.info(
            'In the descriptions of files, sections, assignments or courses the teacher can add links to webpages,'
            + ' files or videos. That links can pont to a internal page on moodle or to an external webpage.'
        )
        print('')

        download_links_in_descriptions = cutie.prompt_yes_or_no(
            Log.special_str('Would you like to download links in descriptions?'),
            default_is_yes=download_links_in_descriptions,
        )

        self.config_helper.set_property('download_links_in_descriptions', download_links_in_descriptions)

    def _select_should_download_linked_files(self):
        """
        Asks the user if linked files should be downloaded
        """
        download_linked_files = self.config_helper.get_download_linked_files()

        self.section_seperator()
        Log.info(
            'In Moodle courses the teacher can also link to external'
            + ' files. This can be audio, video, text or anything else.'
            + ' In particular, the teacher can link to Youtube videos.'
        )
        Log.debug('To download videos correctly you have to install ffmpeg. ')

        Log.error('These files can increase the download volume considerably.')

        Log.info(
            'If you want to filter the external links by their domain,'
            + ' you can manually set a whitelist and a blacklist'
            + ' (https://github.com/C0D3D3V/Moodle-Downloader-2/'
            + 'wiki/Download-(external)-linked-files'
            + ' for more details).'
        )
        Log.warning(
            'Please note that the size of the external files is determined during the download, so the total size'
            + ' changes during the download.'
        )
        print('')

        download_linked_files = cutie.prompt_yes_or_no(
            Log.special_str('Would you like to download linked files of the courses you have selected?'),
            default_is_yes=download_linked_files,
        )

        self.config_helper.set_property('download_linked_files', download_linked_files)

    def _select_should_load_default_filename_character_map(self):
        """
        Asks the user if the default filename character map should be loaded
        """
        filename_character_map = self.config_helper.get_filename_character_map()

        if os.name != 'nt':
            self.section_seperator()

            Log.info(
                'On Windows many characters are forbidden in filenames and paths, if you want, these characters can be'
                + ' automatically removed from filenames.'
            )

            Log.warning('If you want to view the downloaded files on Windows this is important!')

            print('Current filename character map: {}'.format(filename_character_map))
            Log.special('Do you want to load the default filename character map for Windows?')

            choices = [
                'No, leave it as it was.',
                'No, load the default linux filename character map.',
                'Yes, load the default windows filename character map.',
            ]

            print('[Confirm your selection with the Enter key]')
            print('')

            selected_map = cutie.select(options=choices)

            if selected_map == 0:
                return
            elif selected_map == 1:
                self.config_helper.set_default_filename_character_map(False)
            elif selected_map == 2:
                self.config_helper.set_default_filename_character_map(True)
        else:
            if filename_character_map != ConfigHelper.windows_map:

                self.section_seperator()
                Log.warning(
                    'Warning: Your current filename character map does not match the standard Windows'
                    + ' filename character map!'
                )
                print('Current filename character map: {}'.format(filename_character_map))
                load_default_map = cutie.prompt_yes_or_no(
                    Log.special_str('Do you want to load the default filename character map for Windows?'),
                    default_is_yes=False,
                )
                if load_default_map:
                    self.config_helper.set_default_filename_character_map(True)

    def section_seperator(self):
        """Print a seperator line.
        """
        print('\n' + '-' * shutil.get_terminal_size().columns + '\n')
