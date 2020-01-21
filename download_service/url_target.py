import os
import time
import urllib

import urllib.parse as urlparse

from utils.state_recorder import Course, File


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
        percent = 100
        if(total_size != 0):
            percent = int(self.downloaded * 100 / total_size)
        self.thread_report[self.thread_id]['percentage'] = percent

    def add_token_to_url(self, url: str):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': self.token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)

    def create_shortcut(self):
        self.file.saved_to = os.path.join(
            self.destination, self.file.content_filename + ".desktop")
        if os.name == "nt":
            self.file.saved_to = os.path.join(
                self.destination, self.file.content_filename + ".URL")

        count = 2
        while os.path.exists(self.file.saved_to):
            # This file has already been downloaded
            new_filename = "{s}_{:02d}{s}".format(
                self.file.content_filename, count, ".desktop")
            if os.name == "nt":
                new_filename = "{s}_{:02d}{s}".format(
                    self.file.content_filename, count, ".URL")

            self.file.saved_to = os.path.join(self.destination,
                                              new_filename)
            count += 1

        if(not os.path.exists(os.path.dirname(self.file.saved_to))):
            os.makedirs(os.path.dirname(self.file.saved_to))

        with open(self.file.saved_to, 'a') as shortcut:
            if os.name == "nt":
                shortcut.write("[InternetShortcut]" + os.linesep)
                shortcut.write(
                    "URL=" + self.file.content_fileurl + os.linesep)
            else:
                shortcut.write("[Desktop Entry]" + os.linesep)
                shortcut.write("Encoding=UTF-8" + os.linesep)
                shortcut.write(
                    "Name=" + self.file.content_filename + os.linesep)
                shortcut.write("Type=Link" + os.linesep)
                shortcut.write(
                    "URL=" + self.file.content_fileurl + os.linesep)
                shortcut.write("Icon=text-html" + os.linesep)
                shortcut.write(
                    "Name[en_US]=" + self.file.content_filename + os.linesep)

        self.file.time_stamp = int(time.time())

        self.success = True

    def download(self, thread_id: int):
        self.thread_id = thread_id
        self.downloaded = 0
        self.thread_report[self.thread_id]['percentage'] = 0
        self.url_tried = self.url_tried + 1

        try:
            # if it is a url we have to create a shortcut
            # instead of downloading it
            if (self.file.module_modname == 'url'):
                self.create_shortcut()
                return self.success

            self.file.saved_to = os.path.join(self.destination,
                                              self.file.content_filename)

            count = 2
            while os.path.exists(self.file.saved_to):
                # This file has already been downloaded
                filename, file_extension = os.path.splitext(
                    self.file.content_filename)
                new_filename = "{s}_{:02d}{s}".format(
                    filename, count, file_extension)

                self.file.saved_to = os.path.join(self.destination,
                                                  new_filename)
                count += 1

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
