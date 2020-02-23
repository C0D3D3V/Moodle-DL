import os
import sys
import time
import shutil
import logging
import threading

from queue import Queue

from utils.logger import Log
from state_recorder.course import Course
from utils.string_tools import StringTools
from download_service.url_target import URLTarget
from download_service.downloader import Downloader
from moodle_connector.moodle_service import MoodleService


class DownloadService:
    """
    DownloadService manages the queue of files to be downloaded and starts
    the Downloader threads which download all URLTargets.
    Furthermore DownloadService is responsible for logging live information
    and errors.
    """

    def __init__(self, courses: [Course], moodle_service: MoodleService,
                 storage_path: str):
        """
        Initiates the DownloadService with all files that
        need to be downloaded. A URLTarget is created for each file.
        @param courses: A list of courses that contains all modified files.
        @param moodle_service: A reference to the moodle_service, currently
                               only to get to the state_recorder and the token.
        @param storage_path: The location where the files will be saved.
        """

        # How much threads should be created
        DownloadService.thread_count = 5
        # How often should the downloader try to download
        # a file again if an error occurs.
        DownloadService.url_tries = 3

        self.courses = courses
        self.state_recorder = moodle_service.recorder
        self.token = moodle_service.get_token()
        self.storage_path = storage_path

        # The wait queue for all URL targets to be downloaded.
        self.queue = Queue(0)
        # A list of the created threads
        self.threads = []
        # A lock to stabilize thread insecure resources.
        # writing in DB
        self.lock = threading.Lock()
        # reading file system
        self.lock2 = threading.Lock()

        # report is used to collect successful and failed downloads
        self.report = {'success': [], 'failure': []}
        # thread_report is used to get live reports from the threads
        self.thread_report = [{'total': 0, 'percentage': 0}
                              for i in range(self.thread_count)]
        # Collects the total size of the files that needs to be downloaded.
        self.total_to_download = 0

        # delete files, that should be deleted
        self.state_recorder.batch_delete_files(self.courses)

        # Prepopulate queue with any files that were given
        for course in self.courses:
            for file in course.files:
                if(file.deleted is False):
                    self.total_to_download += file.content_filesize

                    save_destination = StringTools.path_of_file(
                        self.storage_path, course.fullname,
                        file.section_name,
                        file.content_filepath
                    )

                    # If the file is located in a folder or in an assignment,
                    # it should be saved in a subfolder
                    # (with the name of the module).
                    if (file.module_modname == "assign" or
                            file.module_modname == "folder"):
                        file_path = file.content_filepath
                        if (file.content_type == "submission_file"):
                            file_path = os.path.join('/submissions/',
                                                     file_path.strip('/'))

                        save_destination = StringTools.path_of_file_in_module(
                            self.storage_path, course.fullname,
                            file.section_name, file.module_name,
                            file_path
                        )

                    self.queue.put(URLTarget(
                        file, course, save_destination, self.token,
                        self.thread_report, self.lock2))

    def run(self):
        """
        Starts all threads to download the files and
        issues status messages at regular intervals.
        """
        self._create_downloader_threads()

        while (not self._downloader_complete()):
            time.sleep(0.1)

            sys.stdout.write(self._get_status_message())
            sys.stdout.flush()

        self._log_failures()

    def _create_downloader_threads(self):
        """
        Creates all downloader threads, initiates them
        with the queue and starts them.
        """
        for i in range(self.thread_count):
            thread = Downloader(self.queue, self.report,
                                self.state_recorder, i,
                                self.lock, self.url_tries)
            thread.start()
            self.threads.append(thread)

    def _downloader_complete(self) -> bool:
        """
        Checks if a thread is still running, if so then the downloaders
        are not finished yet.
        @return: status of the downloaders
        """
        fininshed_downlaoding = True
        for thread in self.threads:
            if thread.is_alive():
                fininshed_downlaoding = False
                break
        return fininshed_downlaoding

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
        progressmessage = "\r"

        threads_status_message = ""
        threads_total_downloaded = 0
        for i in range(self.thread_count):
            # A thread status contains it id and the progress
            # of the current file
            threads_status_message += " T%i: %3i%%" % (
                i, self.thread_report[i]['percentage'])
            threads_total_downloaded += self.thread_report[i]['total']

        percentage = 100
        if (self.total_to_download != 0):
            percentage = int(threads_total_downloaded *
                             100 / self.total_to_download)

        # The overall progress also includes the total size that needs to be
        # downloaded and the size that has already been downloaded.
        progressmessage += "Total: %3s%% %12s/%12skb" % (
            percentage, int(threads_total_downloaded / 1000.0),
            int(self.total_to_download / 1000.0))

        progressmessage += threads_status_message

        if (len(progressmessage) > limits.columns):
            progressmessage = progressmessage[0:limits.columns]

        return progressmessage

    def _log_failures(self):
        """
        Logs errors if any have occurred.
        """
        print('')
        if (len(self.report['failure']) > 0):
            Log.warning(
                'Error while trying to download files,' +
                ' look at the log for more details.')

        for url_target in self.report['failure']:
            logging.error('Error while trying to download file:' +
                          ' %s' % (url_target))
