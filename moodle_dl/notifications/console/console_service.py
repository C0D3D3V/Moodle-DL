from typing import List

from moodle_dl.downloader.task import Task
from moodle_dl.notifications.notification_service import NotificationService
from moodle_dl.types import Course
from moodle_dl.utils import Log, PathTools as PT


class ConsoleService(NotificationService):
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
            Log.success(f'{diff_count} changes found for the configured Moodle-Account.')

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

    def notify_about_failed_downloads(self, failed_downloads: List[Task]):
        if len(failed_downloads) > 0:
            print('')
            Log.warning(
                'Error while trying to download files, look at the log for more details. List of failed downloads:'
            )
            print('')

        for task in failed_downloads:
            Log.cyan(PT.to_valid_name(task.file.content_filename, is_file=True))
            Log.error(f'\t{task.status.get_error_text()}')

        print('')
