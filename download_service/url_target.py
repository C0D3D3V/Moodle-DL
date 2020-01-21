import os
import time
import urllib

import urllib.parse as urlparse

from utils.state_recorder import Course, File


class URLTarget(object):
    """
    URLTarget is responsible to download a special file.
    """

    def __init__(self, file: File, course: Course, destination: str,
                 token: str, thread_report: []):
        """
        Initiating an url target.
        """

        self.file = file
        self.course = course
        self.destination = destination
        self.token = token

        # Counts the downlaod attempts
        self.url_tried = 0

        # To return errors
        self.success = False
        self.error = None

        # To create live reports.
        self.thread_id = 0
        self.thread_report = thread_report

        # Total downloaded.
        self.downloaded = 0

    def add_progress(self, count: int, block_size: int, total_size: int):
        """
        Callback function for urlretrieve to
        calculate the current download progress
        """
        self.thread_report[self.thread_id]['total'] += block_size
        self.downloaded += block_size

        # if urlretrieve cannot determine the actual download size,
        # use that of moodle.
        if(total_size == -1):
            total_size = self.file.content_filesize

        percent = 100
        if(total_size != 0):
            percent = int(self.downloaded * 100 / total_size)

        self.thread_report[self.thread_id]['percentage'] = percent

    def _add_token_to_url(self, url: str) -> str:
        """
        Adds the Moodle token to a URL
        @param url: The url where the token should be added.
        @return: The url with the token.
        """
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': self.token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)

    @staticmethod
    def _create_dir(path: str):
        # Creates the folders of a path if they do not exist.
        if(not os.path.exists(os.path.dirname(path))):
            os.makedirs(os.path.dirname(path))

    @staticmethod
    def _rename_if_exists(path: str) -> str:
        """
        Rename a file name until no file with the same name exists.
        @param path: The path to the file to be renamed.
        @return: A path to a file that does not yet exist.
        """
        count = 1
        new_path = path
        content_filename = os.path.basename(path)
        destination = os.path.dirname(path)

        while os.path.exists(new_path):
            count += 1

            filename, file_extension = os.path.splitext(
                content_filename)

            new_filename = "{s}_{:02d}{s}".format(
                filename, count, file_extension)

            new_path = os.path.join(destination,
                                    new_filename)
        return new_path

    def create_shortcut(self):
        """
        Creates a Schortcut to a URL
        Because shortcuts are different under Windows and Unix,
        both cases are covered here.
        """
        self.file.saved_to = os.path.join(
            self.destination, self.file.content_filename + ".desktop")
        if os.name == "nt":
            self.file.saved_to = os.path.join(
                self.destination, self.file.content_filename + ".URL")

        self.file.saved_to = self._rename_if_exists(self.file.saved_to)

        self._create_dir(self.file.saved_to)

        with open(self.file.saved_to, 'w+') as shortcut:
            if os.name == "nt":
                shortcut.write("[InternetShortcut]" + os.linesep)
                shortcut.write("URL=" + self.file.content_fileurl + os.linesep)
            else:
                shortcut.write("[Desktop Entry]" + os.linesep)
                shortcut.write("Encoding=UTF-8" + os.linesep)
                shortcut.write("Name=" + self.file.content_filename +
                               os.linesep)
                shortcut.write("Type=Link" + os.linesep)
                shortcut.write("URL=" + self.file.content_fileurl + os.linesep)
                shortcut.write("Icon=text-html" + os.linesep)
                shortcut.write("Name[en_US]=" + self.file.content_filename +
                               os.linesep)

        self.file.time_stamp = int(time.time())

        self.success = True

    def download(self, thread_id: int):
        """
        Downloads a file
        """
        self.thread_id = thread_id
        self.url_tried += 1

        # reset download status
        self.downloaded = 0
        self.thread_report[self.thread_id]['percentage'] = 0

        try:

            # if it is a url we have to create a shortcut
            # instead of downloading it
            if (self.file.module_modname == 'url'):
                self.create_shortcut()
                return self.success

            self.file.saved_to = os.path.join(self.destination,
                                              self.file.content_filename)

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

            self._create_dir(self.file.saved_to)

            urllib.request.urlretrieve(self._add_token_to_url(
                self.file.content_fileurl),
                self.file.saved_to,
                reporthook=self.add_progress)

            self.file.time_stamp = int(time.time())

            self.success = True

        except Exception as e:
            self.error = e
            # Subtract the already downloaded content in case of an error.
            self.thread_report[self.thread_id]['total'] -= self.downloaded
            self.thread_report[self.thread_id]['percentage'] = 100

        return self.success

    def __str__(self):
        # URLTarget to string
        return 'URLTarget (%(file)s, %(success)s, %(error)s)' % {
            'file': self.file,
            'success': self.success, 'error': self.error}
