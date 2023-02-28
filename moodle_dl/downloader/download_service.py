import asyncio
import logging
import time

from concurrent.futures import ThreadPoolExecutor
from typing import List

from moodle_dl.config import ConfigHelper
from moodle_dl.database import StateRecorder
from moodle_dl.downloader.task import Task
from moodle_dl.types import Course, MoodleDlOpts, DlEvent, DownloadStatus, TaskState
from moodle_dl.utils import format_bytes, calc_speed, format_speed


class DownloadService:
    "Manages jobs to download, delete or create files of courses"

    def __init__(self, courses: List[Course], config: ConfigHelper, opts: MoodleDlOpts, database: StateRecorder):
        self.courses = courses
        self.config = config
        self.opts = opts
        self.database = database

        self.status = DownloadStatus()
        self.all_tasks = self.gen_all_tasks()

    def gen_all_tasks(self) -> List:
        # Set custom chunk size
        Task.CHUNK_SIZE = self.opts.download_chunk_size
        dl_options = self.config.get_download_options(self.opts)
        thread_pool = ThreadPoolExecutor(max_workers=self.opts.max_parallel_yt_dlp)
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
                            thread_pool=thread_pool,
                            callback=self.status_callback,
                        )
                    )
                    self.status.bytes_to_download += course_file.content_filesize
                    self.status.files_to_download += 1
        if self.status.files_to_download > 0:
            logging.info('Download queue contains %d tasks', self.status.files_to_download)
        else:
            logging.debug('Download queue is empty')
        return all_tasks

    def status_callback(self, event: DlEvent, task: Task, **extra_args):
        self.status.lock.acquire()
        if event == DlEvent.RECEIVED:
            self.status.bytes_downloaded += extra_args['bytes_received']
        elif event == DlEvent.FAILED:
            self.status.files_failed += 1
        elif event == DlEvent.FINISHED:
            self.database.save_file(task.file, task.course.id, task.course.fullname)
            self.status.files_downloaded += 1
        elif event == DlEvent.TOTAL_SIZE:
            self.status.bytes_to_download += extra_args['content_length']
        elif event == DlEvent.TOTAL_SIZE_UPDATE:
            self.status.bytes_to_download += extra_args['content_length_diff']
        self.status.lock.release()

    def run(self):
        asyncio.run(self.real_run())

    async def real_run(self):
        "Starts all tasks and issues status messages at regular intervals"

        # delete files, that should be deleted
        self.database.batch_delete_files(self.courses)

        if len(self.all_tasks) <= 0:
            return

        # run all other tasks
        status_logger_task = asyncio.create_task(self.log_download_status())

        dl_tasks = set()
        for task in self.all_tasks:
            if len(dl_tasks) >= self.opts.max_parallel_downloads:
                # Wait for some download to finish before adding a new one
                _done, dl_tasks = await asyncio.wait(dl_tasks, return_when=asyncio.FIRST_COMPLETED)
            dl_tasks.add(asyncio.create_task(task.run()))

        # Wait for the remaining downloads to finish
        await asyncio.wait(dl_tasks)
        status_logger_task.cancel()

    async def log_download_status(self):
        last_bytes_downloaded = 0
        last_status_timestamp = time.time()
        while True:
            # Print every 2 sec the current status
            await asyncio.sleep(2)

            percentage = None
            if self.status.bytes_to_download != 0:
                percentage = int(self.status.bytes_downloaded * 100 / self.status.bytes_to_download)
                if percentage > 100 or percentage < 0:
                    percentage = None
            if percentage is None:
                percentage = ' NA%'
            else:
                percentage = f'{percentage:3}%'

            speed = calc_speed(last_status_timestamp, time.time(), self.status.bytes_downloaded - last_bytes_downloaded)
            last_status_timestamp = time.time()
            last_bytes_downloaded = self.status.bytes_downloaded

            message_line = (
                f'Total: {percentage}'
                + f' {format_bytes(self.status.bytes_downloaded):>5} / {format_bytes(self.status.bytes_to_download):<5}'
                + f' | Done: {(self.status.files_downloaded + self.status.files_failed):>5}'
                + f' / {self.status.files_to_download:<5}'
                + f' | Speed: {format_speed(speed)}'
            )
            if self.status.files_failed > 0:
                message_line += f' | Failed: {self.status.files_failed}'

            logging.info(message_line)

    def get_failed_tasks(self) -> List[Task]:
        "Return a list of failed downloads."
        result = []
        for task in self.all_tasks:
            if task.status.state == TaskState.FAILED:
                result.append(task)
        return result
