import shutil
import sys

from typing import Dict, List, Tuple

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.core_handler import CoreHandler
from moodle_dl.moodle.moodle_service import MoodleService
from moodle_dl.moodle.request_helper import RequestRejectedError, RequestHelper
from moodle_dl.types import Course, MoodleDlOpts
from moodle_dl.utils import Cutie, Log, PathTools as PT


class ConfigWizard:
    def __init__(self, config: ConfigHelper, opts: MoodleDlOpts):
        self.config = config
        self.opts = opts

        self.core_handler = CoreHandler(RequestHelper(opts, self.config.get_moodle_URL(), self.config.get_token()))

    def get_user_id_and_version(self) -> Tuple[int, int]:
        user_id, version = self.config.get_userid_and_version()
        if user_id is None or version is None:
            user_id, version = self.core_handler.fetch_userid_and_version()
            self._select_should_userid_and_version_be_saved(user_id, version)
        else:
            self.core_handler.version = version
        return user_id, version

    def interactively_acquire_config(self):
        """
        Guides the user through the process of configuring the downloader
        for the courses to be downloaded and in what way
        """
        courses = []
        try:
            user_id, _ = self.get_user_id_and_version()
            courses = self.core_handler.fetch_courses(user_id)

        except (RequestRejectedError, ValueError, RuntimeError, ConnectionError) as error:
            Log.error(f'Error while communicating with the Moodle System! ({error})')
            sys.exit(1)

        self._select_courses_to_download(courses)
        self._set_options_of_courses(courses)
        self._select_should_download_submissions()
        self._select_should_download_descriptions()
        self._select_should_download_links_in_descriptions()
        self._select_should_download_databases()
        self._select_should_download_forums()
        self._select_should_download_quizzes()
        self._select_should_download_lessons()
        self._select_should_download_workshops()
        self._select_should_download_linked_files()
        self._select_should_download_also_with_cookie()

        Log.success('Configuration successfully updated!')

    def interactively_add_all_visible_courses(self):
        """
        Guides the user through the process of adding all visible courses
        to the list of courses to download in the configuration
        """
        print('')
        Log.info(
            'It is possible to automatically complete the moodle-dl configuration'
            + ' with all the courses you can see on your moodle. These are either'
            + ' courses to which you have the appropriate rights to see the'
            + ' course or the course is visible without enrollment.'
        )

        Log.magenta(
            'This process can take several minutes for large Moodels, as is common at'
            + ' large universities. Timeout is set to 20 minutes.'
        )

        print('')

        add_all_visible_courses = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to add all visible courses of your Moodle to the configuration?'),
            default_is_yes=False,
        )

        if not add_all_visible_courses:
            return
        else:
            Log.warning(
                'Please wait for the result, this may take several minutes.'
                + ' In addition to adding the courses to the configuration,'
                + ' it will also create an `all_courses.json` file with all'
                + ' the courses available on your Moodle.'
            )

        courses = []
        all_visible_courses = []
        try:
            user_id, _ = self.get_user_id_and_version()
            courses = self.core_handler.fetch_courses(user_id)
            log_all_courses_to = PT.make_path(self.opts.path, 'all_courses.json')
            all_visible_courses = self.core_handler.fetch_all_visible_courses(log_all_courses_to)

        except (RequestRejectedError, ValueError, RuntimeError, ConnectionError) as error:
            Log.error(f'Error while communicating with the Moodle System! ({error})')
            sys.exit(1)

        # Filter out courses the user is enroled in
        filtered_all_courses = []
        for visible_course in all_visible_courses:
            add_to_final_list = True
            for course in courses:
                if visible_course.id == course.id:
                    add_to_final_list = False
                    break
            if add_to_final_list:
                filtered_all_courses.append(visible_course)

        # Update Public Courses IDs
        download_public_course_ids = self.config.get_download_public_course_ids()
        # Update Course settings List for all new Courses
        options_of_courses = self.config.get_options_of_courses()
        for course in filtered_all_courses:
            current_course_settings = options_of_courses.get(str(course.id), None)

            # create default settings
            if current_course_settings is None:
                current_course_settings = {
                    'original_name': course.fullname,
                    'overwrite_name_with': None,
                    'create_directory_structure': True,
                }

                options_of_courses.update({str(course.id): current_course_settings})

            if course.id not in download_public_course_ids:
                download_public_course_ids.append(course.id)

        self.config.set_property('options_of_courses', options_of_courses)
        self.config.set_property('download_public_course_ids', download_public_course_ids)

        Log.success('Configuration successfully updated!')

    def _select_should_userid_and_version_be_saved(self, userid, version):
        """
        Asks the user if the userid and version should be saved in the configuration
        """
        do_not_ask_to_save_userid_and_version = self.config.get_do_not_ask_to_save_userid_and_version()
        if do_not_ask_to_save_userid_and_version:
            return

        print('')
        Log.info(
            'The user id and version number of Moodle are downloaded'
            + ' at the beginning of each run of the downloader.'
            + ' Since this data rarely changes, it can be saved in the'
            + ' configuration.'
        )

        Log.magenta(f'Your user id is `{userid}` and the moodle version is `{version}`')

        print('')

        save_userid_and_version = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to store the user id and version number of Moodle in the configuration?'),
            default_is_yes=False,
        )

        if save_userid_and_version:
            Log.warning(
                'Remember to delete the version number from the'
                + ' configuration once Moodle has been updated'
                + ' and then run the configurator again!'
            )

            self.config.set_property('userid', userid)
            self.config.set_property('version', version)
        else:
            do_not_ask_to_save_userid_and_version = Cutie.prompt_yes_or_no(
                Log.blue_str('Should this question no longer be asked in the future?'),
                default_is_yes=False,
            )
            if do_not_ask_to_save_userid_and_version:
                self.config.set_property('do_not_ask_to_save_userid_and_version', True)

        self.section_seperator()

    def _select_courses_to_download(self, courses: List[Course]):
        """
        Asks the user for the courses that should be downloaded.
        @param courses: All available courses
        """
        download_course_ids = self.config.get_download_course_ids()
        dont_download_course_ids = self.config.get_dont_download_course_ids()

        print('')
        Log.info(
            'To avoid downloading all Moodle courses you are enrolled in, you can select which courses you want'
            + ' to download here. You can either create a whitelist or a blacklist for this purpose.'
            + '\n\n- With a whitelist only the courses you have selected will be downloaded,'
            + ' any courses you enroll in in the future will not be downloaded automatically unless'
            + ' you add them to the list.'
            + '\n- With a blacklist all selected courses will not be downloaded, all other courses that are not'
            + ' on the list will be downloaded, but if you enroll in a new course online in the future that is not'
            + ' on your blacklist it will automatically be downloaded as well. '
        )
        print('')
        use_whitelist = len(dont_download_course_ids) == 0

        use_whitelist = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to create a whitelist or blacklist for your courses?'),
            default_is_yes=use_whitelist,
            yes_text='Whitelist',
            no_text='Blacklist',
        )

        choices = []
        defaults = []
        for i, course in enumerate(courses):
            choices.append(f'{int(course.id):5}\t{course.fullname}')

            should_download = MoodleService.should_download_course(
                course.id, download_course_ids, dont_download_course_ids
            )
            if should_download and use_whitelist:
                defaults.append(i)
            elif not should_download and not use_whitelist:
                defaults.append(i)

        if use_whitelist:
            Log.blue('Which of the courses should be downloaded?')
        else:
            Log.blue('Which of the courses should NOT be downloaded?')
        Log.info('[You can select with the space bar and confirm your selection with the enter key]')
        print('')
        selected_courses = Cutie.select_multiple(options=choices, ticked_indices=defaults)

        course_ids = []
        for i, course in enumerate(courses):
            if i in selected_courses:
                course_ids.append(course.id)

        if use_whitelist:
            self.config.set_property('download_course_ids', course_ids)
            self.config.remove_property('dont_download_course_ids')
        elif not use_whitelist:
            self.config.set_property('dont_download_course_ids', course_ids)
            self.config.remove_property('download_course_ids')

    def _select_sections_to_download(self, sections: List[Dict], excluded: List[int]) -> List[int]:
        """
        Asks the user for the sections that should be downloaded.
        @param sections: All available sections
        @param excluded sections currently excluded
        """

        choices = []
        defaults = []
        for i, section in enumerate(sections):
            section_id = section.get("id")
            choices.append(f"{int(section_id):5}\t{section.get('name')}")

            if MoodleService.should_download_section(section_id, excluded):
                defaults.append(i)

        Log.blue('Which of the sections should be downloaded?')
        Log.info('[You can select with the space bar and confirm your selection with the enter key]')
        print('')
        selected_sections = Cutie.select_multiple(options=choices, ticked_indices=defaults)

        dont_download_section_ids = []
        for i, section in enumerate(sections):
            if i not in selected_sections:
                dont_download_section_ids.append(section.get("id"))

        return dont_download_section_ids

    def _set_options_of_courses(self, courses: List[Course]):
        """
        Let the user set special options for every single course
        """
        download_course_ids = self.config.get_download_course_ids()
        dont_download_course_ids = self.config.get_dont_download_course_ids()

        self.section_seperator()
        Log.info(
            'You can set special settings for every single course.\n'
            + 'You can set these options:\n'
            + ' - A different name for the course\n'
            + ' - If a directory structure should be created for the course'
            + ' [create_directory_structure (cfs)]\n'
            + ' - Which of the sections should be downloaded (default all).'
        )
        print('')

        while True:
            choices = []
            choices_courses = []

            options_of_courses = self.config.get_options_of_courses()

            choices.append('None')

            for course in courses:
                if MoodleService.should_download_course(course.id, download_course_ids, dont_download_course_ids):
                    current_course_settings = options_of_courses.get(str(course.id), None)

                    # create default settings
                    if current_course_settings is None:
                        current_course_settings = {
                            'original_name': course.fullname,
                            'overwrite_name_with': None,
                            'create_directory_structure': True,
                            'excluded_sections': [],
                        }

                    # create list of options
                    overwrite_name_with = current_course_settings.get('overwrite_name_with', None)

                    create_directory_structure = current_course_settings.get('create_directory_structure', True)

                    if overwrite_name_with is not None and overwrite_name_with != course.fullname:
                        choices.append(
                            (
                                f'{int(course.id):5}\t{overwrite_name_with} ({course.fullname})'
                                + f' cfs={create_directory_structure}'
                            )
                        )

                    else:
                        choices.append(f'{int(course.id):5}\t{course.fullname}  cfs={create_directory_structure}')

                    choices_courses.append(course)

            print('')
            Log.blue('For which of the following course do you want to change the settings?')
            print('[Confirm your selection with the Enter key]')
            print('')

            selected_course = Cutie.select(options=choices)
            if selected_course == 0:
                break
            else:
                sel = choices_courses[selected_course - 1]
                self._change_settings_of(sel, options_of_courses)

    def _change_settings_of(self, course: Course, options_of_courses: Dict):
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
                'excluded_sections': [],
            }

        changed = False

        # Ask for new name
        overwrite_name_with = input(f'Enter a new name for this Course [leave blank for "{course.fullname}"]:   ')

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

        create_directory_structure = Cutie.prompt_yes_or_no(
            Log.blue_str('Should a directory structure be created for this course?'),
            default_is_yes=create_directory_structure,
        )

        if create_directory_structure is not current_course_settings.get('create_directory_structure', True):
            changed = True
            current_course_settings.update({'create_directory_structure': create_directory_structure})

        excluded_sections = current_course_settings.get('excluded_sections', [])

        change_excluded_sections_prompt = 'Do you want to exclude individual sections of this course from download?'
        if len(excluded_sections) > 0:
            change_excluded_sections_prompt = (
                'Do you want to change the selection of sections that should not be'
                + f' downloaded? Currently {len(excluded_sections)} sections of this course are excluded from download.'
            )

        change_excluded_sections = Cutie.prompt_yes_or_no(
            Log.blue_str(change_excluded_sections_prompt),
            default_is_yes=(len(excluded_sections) > 0),
        )

        if change_excluded_sections:
            Log.info('Please wait for a moment, the information about the course sections gets downloaded.')
            sections = self.core_handler.fetch_sections(course.id)

            dont_download_section_ids = self._select_sections_to_download(sections, excluded_sections)

            if dont_download_section_ids != current_course_settings.get('excluded_sections', []):
                changed = True
                current_course_settings.update({'excluded_sections': dont_download_section_ids})

        if changed:
            options_of_courses.update({str(course.id): current_course_settings})
            self.config.set_property('options_of_courses', options_of_courses)

    def _select_should_download_submissions(self):
        """
        Asks the user if submissions should be downloaded
        """
        download_submissions = self.config.get_download_submissions()

        self.section_seperator()
        Log.info(
            'Submissions are files that you or a teacher have uploaded'
            + ' to your assignments. Moodle does not provide an'
            + ' interface for downloading information from all'
            + ' submissions to a course at once.'
        )
        Log.warning('Therefore, it may be slow to monitor changes to submissions.')
        print('')

        download_submissions = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to download submissions of your assignments?'),
            default_is_yes=download_submissions,
        )

        self.config.set_property('download_submissions', download_submissions)

    def _select_should_download_databases(self):
        """
        Asks the user if databases should be downloaded
        """
        download_databases = self.config.get_download_databases()

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

        download_databases = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to download databases of your courses?'), default_is_yes=download_databases
        )

        self.config.set_property('download_databases', download_databases)

    def _select_should_download_forums(self):
        """
        Asks the user if forums should be downloaded
        """
        download_forums = self.config.get_download_forums()

        self.section_seperator()
        Log.info('In forums, students and teachers can discuss and exchange information together.')
        print('')

        download_forums = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to download forums of your courses?'), default_is_yes=download_forums
        )

        self.config.set_property('download_forums', download_forums)

    def _select_should_download_quizzes(self):
        """
        Asks the user if quizzes should be downloaded
        """
        download_quizzes = self.config.get_download_quizzes()

        self.section_seperator()
        Log.info(
            'Quizzes are tests that a student must complete in a course and are graded on.'
            + ' Only quizzes that are in progress or have been completed will be downloaded.'
        )
        print('')

        download_quizzes = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to download quizzes of your courses?'), default_is_yes=download_quizzes
        )

        self.config.set_property('download_quizzes', download_quizzes)

    def _select_should_download_lessons(self):
        """
        Asks the user if lessons should be downloaded
        """
        download_lessons = self.config.get_download_lessons()

        self.section_seperator()
        Log.info(
            'Lessons are a kind of self-teaching with pages of information and other pages with questions to answer.'
            + ' A student can be graded on their answers after completing a lesson. Currently, only lessons without'
            + ' the answers are downloaded. The answers are potentially also available for download,'
            + ' but this has not been implemented.'
        )
        print('')

        download_lessons = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to download lessons of your courses?'), default_is_yes=download_lessons
        )

        self.config.set_property('download_lessons', download_lessons)

    def _select_should_download_workshops(self):
        """
        Asks the user if workshops should be downloaded
        """
        download_workshops = self.config.get_download_workshops()

        self.section_seperator()
        Log.info(
            'Workshops function according to the peer review process.'
            + ' Students can make submissions and have to assess submissions of other students. '
        )
        print('')

        download_workshops = Cutie.prompt_yes_or_no(
            Log.blue_str('Do you want to download workshops of your courses?'), default_is_yes=download_workshops
        )

        self.config.set_property('download_workshops', download_workshops)

    def _select_should_download_descriptions(self):
        """
        Asks the user if descriptions should be downloaded
        """
        download_descriptions = self.config.get_download_descriptions()

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

        download_descriptions = Cutie.prompt_yes_or_no(
            Log.blue_str('Would you like to download descriptions of the courses you have selected?'),
            default_is_yes=download_descriptions,
        )

        self.config.set_property('download_descriptions', download_descriptions)

    def _select_should_download_links_in_descriptions(self):
        """
        Asks the user if links in descriptions should be downloaded
        """
        download_links_in_descriptions = self.config.get_download_links_in_descriptions()

        self.section_seperator()
        Log.info(
            'In the descriptions of files, sections, assignments or courses the teacher can add links to webpages,'
            + ' files or videos. That links can point to a internal page on moodle or to an external webpage.'
        )
        print('')

        download_links_in_descriptions = Cutie.prompt_yes_or_no(
            Log.blue_str('Would you like to download links in descriptions?'),
            default_is_yes=download_links_in_descriptions,
        )

        self.config.set_property('download_links_in_descriptions', download_links_in_descriptions)

    def _select_should_download_linked_files(self):
        """
        Asks the user if linked files should be downloaded
        """
        download_linked_files = self.config.get_download_linked_files()

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
            + ' (https://github.com/C0D3D3V/Moodle-DL/'
            + 'wiki/Download-(external)-linked-files'
            + ' for more details).'
        )
        Log.warning(
            'Please note that the size of the external files is determined during the download, so the total size'
            + ' changes during the download.'
        )
        print('')

        download_linked_files = Cutie.prompt_yes_or_no(
            Log.blue_str('Would you like to download linked files of the courses you have selected?'),
            default_is_yes=download_linked_files,
        )

        self.config.set_property('download_linked_files', download_linked_files)

    def _select_should_download_also_with_cookie(self):
        """
        Ask the user whether files for which a cookie is required should be downloaded.
        """
        download_also_with_cookie = self.config.get_download_also_with_cookie()

        self.section_seperator()
        Log.info(
            'Descriptions may contain links to files that require a browser cookie so they can be downloaded.'
            + ' There are also several Moodle plugins that cannot be displayed in the Moodle app,'
            + ' so you need a browser cookie to download these plugin files.'
        )

        Log.debug(
            'The Moodle browser cookie is created using your private token and stored in the `Configs.txt` file.'
            + ' As long as this option is activated, the file always contains a valid cookie.'
        )

        if self.config.get_privatetoken() is None:
            Log.error(
                'Currently no private token is stored in the configuration.'
                + ' Create a private token with moodle-dl --new-token (if necessary with --sso)'
            )

        print('')

        download_also_with_cookie = Cutie.prompt_yes_or_no(
            Log.blue_str('Would you like to download files for which a cookie is required?'),
            default_is_yes=download_also_with_cookie,
        )

        self.config.set_property('download_also_with_cookie', download_also_with_cookie)

    def section_seperator(self):
        """Print a seperator line."""
        print('\n' + '-' * shutil.get_terminal_size().columns + '\n')
