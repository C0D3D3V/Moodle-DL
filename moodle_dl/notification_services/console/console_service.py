import logging

from typing import List

from moodle_dl.download_service.url_target import URLTarget
from moodle_dl.notification_services.notification_service import NotificationService
from moodle_dl.state_recorder import Course
from moodle_dl.utils import Log


class ConsoleService(NotificationService):
    def interactively_configure(self) -> None:
        raise RuntimeError('Not yet implemendet!')

    def notify_about_changes_in_moodle(self, changes: List[Course]) -> None:
        """
        Creates a terminal output about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
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

            Log.blue(course.fullname)

            for file in course.files:
                saved_to_path = file.saved_to
                if file.new_file is not None:
                    saved_to_path = file.new_file.saved_to
                if file.modified:
                    Log.yellow('≠\t' + saved_to_path)
                elif file.moved:
                    if file.new_file is not None:
                        print(Log.cyan_str('<->\t' + file.saved_to) + Log.green_str(' ==> ' + saved_to_path))

                    else:
                        print(Log.cyan_str('<->\t' + saved_to_path))

                elif file.deleted:
                    print(Log.magenta_str('-\t' + saved_to_path))

                else:
                    print(Log.green_str('+\t' + saved_to_path))
            print('\n')

    def notify_about_error(self, error_description: str):
        Log.error(f'The following error occurred during execution:\n{error_description}')

    def notify_about_failed_downloads(self, failed_downloads: List[URLTarget]):
        if len(failed_downloads) > 0:
            print('')
            Log.warning(
                'Error while trying to download files, look at the log for more details. List of failed downloads:'
            )
            print('')

        for url_target in failed_downloads:
            Log.cyan(url_target.file.content_filename)
            Log.error('\t' + str(url_target.error))

        print('')
