import os
import sys
import time
import html
import urllib
import threading

import urllib.parse as urlparse

from moodle_connector.moodle_service import MoodleService
from utils.state_recorder import Course, File, StateRecorder
from queue import Queue


class DownloadService:
    class Downloader(threading.Thread):
        def __init__(self, queue: Queue, report: [],
                     state_recorder: StateRecorder,
                     thread_id: int,
                     lock: threading.Lock):
            threading.Thread.__init__(self)
            self.queue = queue
            self.report = report
            self.thread_id = thread_id
            self.lock = lock
            self.state_recorder = state_recorder

        def run(self):
            while self.queue.empty() is False:
                try:
                    url_target = self.queue.get(False)
                except Queue.Empty:
                    break

                response = url_target.download(self.thread_id)

                # information is still saved in url_target
                if (response is False and
                        url_target.url_tried < url_target.url_tries):
                    self.queue.put(url_target)
                elif (response is False and
                      url_target.url_tried == url_target.url_tries):
                    self.report['failure'].append(url_target)
                elif (response):
                    self.lock.acquire()
                    self.state_recorder.save_file(
                        url_target.file, url_target.course.id,
                        url_target.course.fullname)
                    self.lock.release()
                    self.report['success'].append(url_target)

                self.queue.task_done()

    class URLTarget(object):
        def __init__(self, file: File, course: Course, destination: str,
                     token: str, url_tries: int, thread_report: []):
            self.file = file
            self.course = course
            self.destination = destination
            self.url_tries = url_tries
            self.url_tried = 0
            self.success = False
            self.error = None
            self.downloaded = 0
            self.token = token
            self.thread_report = thread_report
            self.thread_id = 0

        def add_progress(self, count: int, block_size: int, total_size: int):
            self.thread_report[self.thread_id]['total'] += block_size
            self.downloaded += block_size
            if(total_size == -1):
                total_size = self.file.content_filesize
            percent = int(self.downloaded * 100 / total_size)
            self.thread_report[self.thread_id]['percentage'] = percent

        def add_token_to_url(self, url: str):
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update({'token': self.token})
            url_parts[4] = urlparse.urlencode(query)
            return urlparse.urlunparse(url_parts)

        def download(self, thread_id: int):
            self.thread_id = thread_id
            self.downloaded = 0
            self.thread_report[self.thread_id]['percentage'] = 0
            self.url_tried = self.url_tried + 1

            try:
                self.file.saved_to = os.path.join(self.destination,
                                                  self.file.content_filename)
                # This file has already been downloaded
                if os.path.exists(self.file.saved_to):
                    # TODO renmae path
                    self.success = True
                    return self.success

                if(not os.path.exists(os.path.dirname(self.file.saved_to))):
                    os.makedirs(os.path.dirname(self.file.saved_to))

                urllib.request.urlretrieve(self.add_token_to_url(
                    self.file.content_fileurl),
                    self.file.saved_to,
                    reporthook=self.add_progress)

                self.file.time_stamp = int(time.time())

                self.success = True

            except Exception as e:
                self.error = e
                self.thread_report[self.thread_id]['total'] -= self.downloaded
                self.thread_report[self.thread_id]['percentage'] = 100

            return self.success

        def __str__(self):
            return 'URLTarget (%(file)s, %(success)s, %(error)s)' % {
                'file': self.file,
                'success': self.success, 'error': self.error}

    def __init__(self, courses: [Course], moodle_service: MoodleService,
                 storage_path: str):
        self.thread_count = 5
        self.url_tries = 3

        self.courses = courses
        self.moodle_service = moodle_service
        self.state_recorder = moodle_service.recorder
        self.token = moodle_service.get_token()
        self.storage_path = storage_path

        self.queue = Queue(0)  # Infinite sized queue
        self.report = {'success': [], 'failure': []}
        self.thread_report = [{'total': 0, 'percentage': 0}
                              for i in range(self.thread_count)]
        self.threads = []
        self.lock = threading.Lock()
        self.total_to_download = 0

        # Prepopulate queue with any values we were given
        for course in self.courses:
            for file in course.files:
                if(file.deleted is False):
                    self.total_to_download += file.content_filesize
                    self.queue.put(DownloadService.URLTarget(
                        file, course, os.path.join(
                            self.storage_path,
                            self.to_valid_name(course.fullname),
                            self.to_valid_name(file.section_name),
                            file.content_filepath.strip('/')), self.token,
                        self.url_tries, self.thread_report))
                else:
                    self.state_recorder.save_file(
                        file, course.id, course.fullname)

    def run(self):
        for i in range(self.thread_count):
            thread = DownloadService.Downloader(self.queue, self.report,
                                                self.state_recorder, i,
                                                self.lock)
            thread.start()
            self.threads.append(thread)

        fininshed_downlaoding = False

        while (not fininshed_downlaoding and self.queue.qsize() > 0 and
               self.total_to_download > 0):
            fininshed_downlaoding = True
            for thread in self.threads:
                if thread.is_alive():
                    fininshed_downlaoding = False
                    break
            time.sleep(0.1)
            progressmessage = "\r"

            threads_status_message = ""
            threads_total_downloaded = 0
            for i in range(self.thread_count):
                threads_status_message += " T%i: %3i%%" % (
                    i, self.thread_report[i]['percentage'])
                threads_total_downloaded += self.thread_report[i]['total']

            percentage = int(threads_total_downloaded *
                             100 / self.total_to_download)
            progressmessage += "Total: %3s%% %12s/%12skb" % (
                percentage, int(threads_total_downloaded / 1000.0),
                int(self.total_to_download / 1000.0))
            progressmessage += threads_status_message
            sys.stdout.write(progressmessage)
            sys.stdout.flush()

        print('')

        # if self.queue.qsize() > 0:
        #    self.queue.join()

    def to_valid_name(self, name: str):
        if ("&" in name):
            name = html.unescape(name)
        name = name.replace('/', '|')
        name = name.replace('\\', '|')
        return name
