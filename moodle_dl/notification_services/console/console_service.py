import logging

from moodle_dl.utils.logger import Log
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget
from moodle_dl.notification_services.notification_service import NotificationService


class ConsoleService(NotificationService):
    def interactively_configure(self) -> None:
        raise RuntimeError('Not yet implemendet!')

    def notify_about_changes_in_moodle(self, changes: [Course]) -> None:
        """
        Creates a terminal output about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        RESET_SEQ = '\033[0m'
        COLOR_SEQ = '\033[1;%dm'

        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)
        print('\n')

        diff_count = 0
        for course in changes:
            diff_count += len(course.files)

        if diff_count > 0:
            msg_changes = '%s changes found for the configured Moodle-Account.'
            logging.info(msg_changes, diff_count)
            Log.success(msg_changes % (diff_count))

        for course in changes:
            if len(course.files) == 0:
                continue

            print(COLOR_SEQ % BLUE + course.fullname + RESET_SEQ)

            for file in course.files:
                if file.modified:
                    print(COLOR_SEQ % YELLOW + '≠\t' + file.saved_to + RESET_SEQ)

                elif file.moved:
                    if file.new_file is not None:
                        print(
                            COLOR_SEQ % CYAN
                            + '<->\t'
                            + (
                                file.saved_to
                                + RESET_SEQ
                                + COLOR_SEQ % GREEN
                                + ' ==> '
                                + file.new_file.saved_to
                                + RESET_SEQ
                            )
                        )
                    else:
                        print(COLOR_SEQ % CYAN + '<->\t' + file.saved_to + RESET_SEQ)

                elif file.deleted:
                    print(COLOR_SEQ % MAGENTA + '-\t' + file.saved_to + RESET_SEQ)

                else:
                    print(COLOR_SEQ % GREEN + '+\t' + file.saved_to + RESET_SEQ)
            print('\n')

    def notify_about_error(self, error_description: str):
        Log.error('The following error occurred during execution:\n%s' % (error_description))

    def notify_about_failed_downloads(self, failed_downloads: [URLTarget]):
        if len(failed_downloads) > 0:
            print('')
            Log.warning(
                'Error while trying to download files, look at the log for more details. List of failed downloads:'
            )
            print('')

        RESET_SEQ = '\033[0m'
        COLOR_SEQ = '\033[1;%dm'

        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

        for url_target in failed_downloads:
            print(
                (COLOR_SEQ % CYAN)
                + url_target.file.content_filename
                + RESET_SEQ
                + (COLOR_SEQ % RED)
                + '\n\t'
                + str(url_target.error)
                + RESET_SEQ
            )

        print('')
