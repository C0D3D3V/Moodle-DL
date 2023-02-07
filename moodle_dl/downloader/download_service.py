import logging
import os
import shutil
import time

from typing import List

from moodle_dl.config import ConfigHelper
from moodle_dl.database.state_recorder import StateRecorder
from moodle_dl.downloader.task import Task
from moodle_dl.types import Course, File
from moodle_dl.utils import format_bytes, SslHelper, PathTools as PT, calc_speed, format_speed


class DownloadService:
    """
    Manages jobs to download, delete or create files of courses
    """

    def __init__(self, courses: List[Course], config: ConfigHelper, opts):
        """
        @param courses: A list of courses that contains all files that needs to be handled
        @param config: Config helper
        @param opts: Moodle-dl options
        """
        self.courses = courses
        self.config = config
        self.opts = opts

        self.state_recorder = StateRecorder(opts)
        self.token = config.get_token()

        # Sets the download options
        self.options = config.get_download_options()
        self.options.update({'ignore_ytdl_errors': opts.ignore_ytdl_errors})

        # Collects the total size of the files that needs to be downloaded.
        self.total_to_download = 0
        self.last_threads_total_downloaded = 0
        self.last_status_timestamp = time.time()
        self.total_files = 0

        # delete files, that should be deleted
        self.state_recorder.batch_delete_files(self.courses)
        self.ssl_context = SslHelper.get_ssl_context(not skip_cert_verify, False)
        self.skip_cert_verify = skip_cert_verify

        # Pre populate queue with any files that were given
        for course in self.courses:
            for file in course.files:
                if file.deleted is False:
                    self.total_to_download += file.content_filesize

                    save_destination = self.gen_path(opts.path, course, file)

                    self.queue.put(
                        Task(
                            file,
                            course,
                            save_destination,
                            self.token,
                            self.thread_report,
                            self.fs_lock,
                            self.ssl_context,
                            self.skip_cert_verify,
                            self.options,
                        )
                    )

                    self.total_files += 1

        logging.debug('Queue contains %s Tasks', self.total_files)

    @staticmethod
    def gen_path(storage_path: str, course: Course, file: File):
        """
        Generates the directory path where a file should be stored
        """
        course_name = course.fullname
        if course.overwrite_name_with is not None:
            course_name = course.overwrite_name_with

        # if a flat path is requested
        if not course.create_directory_structure:
            return PT.flat_path_of_file(storage_path, course_name, file.content_filepath)

        # If the file is located in a folder or in an assignment,
        # it should be saved in a sub-folder
        # (with the name of the module).
        if file.module_modname.endswith(('assign', 'folder', 'data', 'forum', 'quiz', 'lesson', 'workshop', 'page')):
            file_path = file.content_filepath
            if file.content_type == 'submission_file':
                file_path = os.path.join('/submissions/', file_path.strip('/'))

            return PT.path_of_file_in_module(storage_path, course_name, file.section_name, file.module_name, file_path)
        return PT.path_of_file(storage_path, course_name, file.section_name, file.content_filepath)

    def run(self):
        """
        Starts all threads to download the files and
        issues status messages at regular intervals.
        """
        if self.total_files == 0:
            return

        self._create_downloader_threads()

        print('\n' * (len(self.threads)), end='')
        old_status_message = ''
        while not self._downloader_complete():
            new_status_message = self._get_status_message()
            if old_status_message != new_status_message:
                print(new_status_message, end='')
                old_status_message = new_status_message
            time.sleep(0.5)

        self._clear_status_message()

    def _get_status_message(self) -> str:
        """
        Creates a string that combines the status messages of all threads.
        The current download progress of a file is displayed in percent
        per Thread.
        A total display is also created, showing the total amount downloaded
        in relation to what still needs to be downloaded.
        @return: A status message string
        """

        # to limit the output to one line
        limits = shutil.get_terminal_size()

        # Starting with a carriage return to overwrite the last message
        progressmessage = f'\033[{len(self.threads)}A\r'

        threads_status_message = ''
        threads_total_downloaded = 0
        for thread in self.threads:
            i = thread.thread_id
            # A thread status contains it id and the progress
            # of the current file
            thread_percentage = self.thread_report[i]['percentage']
            thread_current_url = self.thread_report[i]['current_url']
            if self.thread_report[i]['external_dl'] is not None:
                thread_current_url = 'ExtDL: ' + self.thread_report[i]['external_dl']

            if not thread.is_alive():
                thread_percentage = 100
                thread_current_url = 'Finished!'

            if len(thread_current_url) + 13 > limits.columns:
                thread_current_url = thread_current_url[0 : limits.columns - 15] + '..'

            threads_status_message += f'\033[KT{int(i):2}: {int(thread_percentage):3}% - {thread_current_url}\n'

            threads_total_downloaded += self.thread_report[i]['total']

            extra_totalsize = self.thread_report[i]['extra_totalsize']
            if extra_totalsize is not None and extra_totalsize != -1:
                self.total_to_download += extra_totalsize
                self.thread_report[i]['extra_totalsize'] = -1

        progressmessage += threads_status_message

        percentage = 100
        if self.total_to_download != 0:
            percentage = int(threads_total_downloaded * 100 / self.total_to_download)

        # The overall progress also includes the total size that needs to be
        # downloaded and the size that has already been downloaded.
        progressmessage_line = (
            f'Total: {percentage:3}%'
            + f' {format_bytes(threads_total_downloaded):>12} / {format_bytes(self.total_to_download):<12}'
        )

        progressmessage_line += f" | Files: {len(self.report['success']):>5} / {self.total_files:<5}"

        diff_to_last_status = threads_total_downloaded - self.last_threads_total_downloaded

        speed = calc_speed(self.last_status_timestamp, time.time(), diff_to_last_status)
        progressmessage_line += ' | ' + format_speed(speed)

        if len(progressmessage_line) > limits.columns:
            progressmessage_line = progressmessage_line[0 : limits.columns]
        progressmessage_line = '\033[K' + progressmessage_line

        progressmessage += progressmessage_line

        self.last_status_timestamp = time.time()
        self.last_threads_total_downloaded = threads_total_downloaded

        return progressmessage

    def get_failed_tasks(self):
        """
        Return a list of failed downloads.
        """
        return []
