import logging
import shutil
import time

from typing import List

from moodle_dl.config import ConfigHelper
from moodle_dl.database import StateRecorder
from moodle_dl.downloader.task import Task
from moodle_dl.types import Course, MoodleDlOpts, DlEvent, DownloadStatus
from moodle_dl.utils import format_bytes, calc_speed, format_speed


class DownloadService:
    "Manages jobs to download, delete or create files of courses"

    def __init__(self, courses: List[Course], config: ConfigHelper, opts: MoodleDlOpts, database: StateRecorder):
        self.courses = courses
        self.config = config
        self.opts = opts
        self.database = database

        self.status = DownloadStatus()

    def gen_all_tasks(self) -> List:
        # Set custom chunk size
        Task.CHUNK_SIZE = self.opts.download_chunk_size
        dl_options = self.config.get_download_options(self.opts)
        all_tasks = []
        for course in self.courses:
            for course_file in course.files:
                if course_file.deleted is False:
                    all_tasks.append(
                        Task(
                            task_id=self.status.files_to_download,
                            file=course_file,
                            course=course,
                            options=dl_options,
                            callback=self.status_callback,
                        )
                    )
                    self.status.bytes_to_download += course_file.content_filesize
                    self.status.files_to_download += 1
        logging.info('Download queue contains %d tasks', self.status.files_to_download)
        return all_tasks

    def status_callback(self, event: DlEvent, task: Task, **extra_args):
        if event == DlEvent.RECEIVED:
            self.status.bytes_downloaded += extra_args['bytes_received']
        elif event == DlEvent.FAILED:
            self.status.files_failed += 1
        elif event == DlEvent.FINISHED:
            self.database.save_file(task.file, task.course.id, task.course.fullname)
            self.status.files_downloaded += 1
        elif event == DlEvent.TOTAL_SIZE:
            self.status.bytes_to_download += extra_args['content_length']

    def run(self):
        "Starts all tasks and issues status messages at regular intervals"

        # delete files, that should be deleted
        self.database.batch_delete_files(self.courses)

        # run all other tasks
        all_tasks = self.gen_all_tasks()

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
