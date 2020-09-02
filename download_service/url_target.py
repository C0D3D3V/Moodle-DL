import os
import ssl
import time
import shutil
import urllib
import random
import string
import posixpath
import traceback
import threading
import html2text
import contextlib
import youtube_dl

from pathlib import Path
import urllib.parse as urlparse

from state_recorder.file import File
from state_recorder.course import Course
from download_service.path_tools import PathTools
from moodle_connector.request_helper import RequestHelper


class URLTarget(object):
    """
    URLTarget is responsible to download a special file.
    """

    def __init__(
        self,
        file: File,
        course: Course,
        destination: str,
        token: str,
        thread_report: [],
        lock: threading.Lock,
        ssl_context: ssl.SSLContext,
        options: {},
    ):
        """
        Initiating an URL target.
        """

        self.file = file
        self.course = course
        self.destination = destination
        self.token = token
        self.lock = lock
        self.ssl_context = ssl_context
        self.options = options

        # get valid filename
        self.filename = PathTools.to_valid_name(self.file.content_filename)

        # Counts the download attempts
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
        if total_size == -1:
            total_size = self.file.content_filesize

        percent = 100
        if total_size != 0:
            percent = int(self.downloaded * 100 / total_size)

        self.thread_report[self.thread_id]['percentage'] = percent

    def _add_token_to_url(self, url: str) -> str:
        """
        Adds the Moodle token to a URL
        @param url: The URL where the token should be added.
        @return: The URL with the token.
        """
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': self.token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)

    @staticmethod
    def _create_dir(path: str):
        # Creates the folders of a path if they do not exist.
        if not os.path.exists(path):
            try:
                # raise condition
                os.makedirs(path)
            except FileExistsError:
                pass

    def _rename_if_exists(self, path: str) -> str:
        """
        Rename a file name until no file with the same name exists.
        @param path: The path to the file to be renamed.
        @return: A path to a file that does not yet exist.
        """
        count = 1
        new_path = path
        content_filename = os.path.basename(path)
        destination = os.path.dirname(path)

        # this is some kind of raise condition
        # Even though it should hardly ever happen,
        # it is possible that threads try to create the same file
        self.lock.acquire()
        while os.path.exists(new_path):
            count += 1

            filename, file_extension = os.path.splitext(content_filename)

            new_filename = '%s_%02d%s' % (filename, count, file_extension)

            new_path = str(Path(destination) / new_filename)

        Path(new_path).touch()
        self.lock.release()

        return new_path

    def try_rename_old_file(self) -> bool:
        """
        This tries to rename an existing modified file.
        It will add the file name extension '_old' if possible.
        On success it returns True
        """
        if self.file.old_file is None:
            return False

        old_path = self.file.old_file.saved_to
        if not os.path.exists(old_path):
            return False

        count = 1
        content_filename = os.path.basename(old_path)
        filename, file_extension = os.path.splitext(content_filename)
        content_filename = '%s_old%s' % (filename, file_extension)

        destination = os.path.dirname(old_path)
        new_path = str(Path(destination) / content_filename)

        # this is some kind of raise condition
        # Even though it should hardly ever happen,
        # it is possible that threads try to create the same file
        self.lock.acquire()
        while os.path.exists(new_path):
            count += 1

            filename, file_extension = os.path.splitext(content_filename)

            new_filename = '%s_%02d%s' % (filename, count, file_extension)

            new_path = str(Path(destination) / new_filename)

        try:
            shutil.move(old_path, new_path)
            self.file.old_file.saved_to = new_path
        except Exception:
            self.lock.release()
            return False

        self.lock.release()
        return True

    class YtLogger(object):
        """
        Just a logger for Youtube-DL
        """

        def debug(self, msg):
            pass

        def warning(self, msg):
            if msg.find('Falling back') >= 0:
                return
            if msg.find('Requested formats are incompatible for merge') >= 0:
                return

            print('\nyoutube-dl: ' + msg + '\n')

        def error(self, msg):
            if msg.find('Unsupported URL') >= 0:
                return
            print('\nyoutube-dl: ' + msg + '\n')

    def yt_hook(self, d):
        downloaded_bytes = d.get('downloaded_bytes', 0)
        total_bytes_estimate = d.get('total_bytes_estimate', 0)
        total_bytes = d.get('total_bytes', 0)

        difference = downloaded_bytes - self.downloaded
        self.thread_report[self.thread_id]['total'] += difference
        self.downloaded += difference

        if total_bytes_estimate <= 0:
            total_bytes_estimate = total_bytes

        if total_bytes_estimate <= 0:
            total_bytes_estimate = self.file.content_filesize

        # Update status information
        if self.thread_report[self.thread_id]['extra_totalsize'] is None and total_bytes_estimate > 0:
            self.thread_report[self.thread_id]['extra_totalsize'] = total_bytes_estimate
            self.thread_report[self.thread_id]['old_extra_totalsize'] = total_bytes_estimate

        if (
            self.thread_report[self.thread_id]['extra_totalsize'] == -1
            and total_bytes_estimate > self.thread_report[self.thread_id]['old_extra_totalsize']
        ):

            self.thread_report[self.thread_id]['extra_totalsize'] = (
                total_bytes_estimate - self.thread_report[self.thread_id]['old_extra_totalsize']
            )

            self.thread_report[self.thread_id]['old_extra_totalsize'] = total_bytes_estimate

        percent = 100
        if total_bytes_estimate != 0:
            percent = int(100 * downloaded_bytes / total_bytes_estimate)

        self.thread_report[self.thread_id]['percentage'] = percent

        if d['status'] == 'finished':
            self.downloaded = 0
            self.thread_report[self.thread_id]['percentage'] = 100
            self.thread_report[self.thread_id]['extra_totalsize'] = None

    def move_tmp_file(self, tmp_file: str):
        """
        Moves temporary files to there correct locations.
        This tries to move every file that beginns with the tmp_file string
        to its new locations.
        @params tmp_file: Is a path + the basename
                          (without the extension) of the tmp_file
        """
        destination = os.path.dirname(tmp_file)
        content_filename = os.path.basename(tmp_file)

        for filename in os.listdir(destination):
            if filename.startswith(content_filename + '.'):
                one_tmp_file = os.path.join(destination, filename)

                content_filename = os.path.basename(one_tmp_file)
                filename, file_extension = os.path.splitext(content_filename)

                new_path = str(Path(self.destination) / self.filename) + file_extension

                count = 1
                content_filename = os.path.basename(new_path)
                destination = os.path.dirname(new_path)

                self.lock.acquire()
                while os.path.exists(new_path):
                    count += 1

                    filename, file_extension = os.path.splitext(content_filename)

                    new_filename = '%s_%02d%s' % (filename, count, file_extension)

                    new_path = str(Path(destination) / new_filename)

                self.file.saved_to = new_path
                try:
                    shutil.move(one_tmp_file, self.file.saved_to)
                except Exception:
                    pass
                self.lock.release()

                self.file.time_stamp = int(time.time())

    def try_download_link(self) -> bool:
        """
        This function should only be used for shortcut/URL files.
        It tests whether a URL refers to a file, that is not an HTML web page.
        Then downloads it.
        Otherwise an attempt will be made to download an HTML video
        from the website.
        When a file is downloaded True is returned.
        """

        isHTML = False
        new_filename = ""
        total_bytes_estimate = -1
        request = urllib.request.Request(url=self.file.content_fileurl, headers=RequestHelper.stdHeader)
        with contextlib.closing(urllib.request.urlopen(request, context=self.ssl_context)) as fp:
            headers = fp.info()

            content_type = headers.get_content_type()
            if content_type == 'text/html' or content_type == 'text/plain':
                isHTML = True
            else:
                url_parsed = urlparse.urlsplit(self.file.content_fileurl)
                new_filename = posixpath.basename(url_parsed.path)
                new_filename = headers.get_filename(new_filename)
                total_bytes_estimate = int(headers.get('Content-Length', -1))

        if not isHTML:
            if self.filename != new_filename:
                self.filename = new_filename
                self.set_path()

            if total_bytes_estimate != -1:
                self.thread_report[self.thread_id]['extra_totalsize'] = total_bytes_estimate

            self.urlretrieve(
                self.file.content_fileurl, self.file.saved_to, context=self.ssl_context, reporthook=self.add_progress
            )

            self.file.time_stamp = int(time.time())

            self.success = True
            return True

        else:

            tmp_filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            tmp_file = str(Path(self.destination) / tmp_filename)
            ydl_opts = {
                'logger': self.YtLogger(),
                'progress_hooks': [self.yt_hook],
                'outtmpl': (tmp_file + '.%(ext)s'),
                'nocheckcertificate': True,
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl_results = ydl.download([self.file.content_fileurl])
                    if ydl_results == 1:
                        return False
                    else:
                        self.move_tmp_file(tmp_file)
                        self.success = True
                        return True
                except Exception:
                    return False

    def is_filtered_external_domain(self):
        """
        This function is used for external linked files.
        It checks if the domain of the download link is on the blacklist
        or is not on the whitelist.

        Returns True if the domain is filtered.
        """

        url_parsed = urlparse.urlparse(self.file.content_fileurl)
        domain = url_parsed.netloc.split(':')[0]

        blacklist = self.options.get('download_domains_blacklist', [])
        whitelist = self.options.get('download_domains_whitelist', [])

        inBlacklist = False

        for entry in blacklist:
            if domain == entry or domain.endswith('.' + entry):
                inBlacklist = True
                break

        inWhitelist = len(whitelist) == 0

        for entry in whitelist:
            if domain == entry or domain.endswith('.' + entry):
                inWhitelist = True
                break

        return not inWhitelist or inBlacklist

    def create_shortcut(self):
        """
        Creates a Shortcut to a URL
        Because shortcuts are different under Windows and Unix,
        both cases are covered here.
        """

        with open(self.file.saved_to, 'w+', encoding='utf-8') as shortcut:
            if os.name == 'nt':
                shortcut.write('[InternetShortcut]' + os.linesep)
                shortcut.write('URL=' + self.file.content_fileurl + os.linesep)
            else:
                shortcut.write('[Desktop Entry]' + os.linesep)
                shortcut.write('Encoding=UTF-8' + os.linesep)
                shortcut.write('Name=' + self.filename + os.linesep)
                shortcut.write('Type=Link' + os.linesep)
                shortcut.write('URL=' + self.file.content_fileurl + os.linesep)
                shortcut.write('Icon=text-html' + os.linesep)
                shortcut.write('Name[en_US]=' + self.filename + os.linesep)

        self.file.time_stamp = int(time.time())

        self.success = True

    def set_path(self):
        """
        Sets the path where a file should be created.
        It takes into account which file type is involved.
        An empty temporary file is created which may need to be cleaned up.
        """

        if self.file.content_type == 'description':
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.md'))

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

        elif self.file.module_modname == 'url':
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.desktop'))
            if os.name == 'nt':
                self.file.saved_to = str(Path(self.destination) / (self.filename + '.URL'))

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

        else:  # normal path
            self.file.saved_to = str(Path(self.destination) / self.filename)

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

    def create_description(self):
        """
        Creates a Description file
        """
        description = open(self.file.saved_to, 'w+', encoding='utf-8')
        to_save = ""
        if self.file.text_content is not None:
            to_save = html2text.html2text(self.file.text_content).strip()
            # to_save could also be html.unescape(),
            # but this could destroy the md file
            if to_save != '':
                description.write(to_save)

        description.close()

        if to_save == '':
            try:
                os.remove(self.file.saved_to)

                self.file.time_stamp = int(time.time())

                self.success = True
            except Exception as e:
                self.error = traceback.format_exc() + '\nError:' + str(e)
        else:
            self.file.time_stamp = int(time.time())

            self.success = True

    def try_move_file(self) -> bool:
        """
        It will try to move the old file to the new location.
        If it worked it returns True. Else the file needs to be redownloaded.
        """

        if self.file.old_file is None:
            return False

        old_path = self.file.old_file.saved_to
        if not os.path.exists(old_path):
            return False

        try:
            shutil.move(old_path, self.file.saved_to)
            self.file.time_stamp = int(time.time())
            self.success = True
            return True
        except FileExistsError:
            # On Windows, the temporary file must be deleted first.
            self.lock.acquire()

            try:
                os.remove(self.file.saved_to)
                shutil.move(old_path, self.file.saved_to)
                self.file.time_stamp = int(time.time())
                self.success = True

                self.lock.release()
                return True
            except Exception:
                pass

            self.lock.release()
        except Exception:
            pass

        return False

    def download(self, thread_id: int):
        """
        Downloads a file
        """
        self.thread_id = thread_id
        self.url_tried += 1

        # reset download status
        self.downloaded = 0
        self.thread_report[self.thread_id]['percentage'] = 0
        self.thread_report[self.thread_id]['extra_totalsize'] = None

        try:
            self._create_dir(self.destination)

            # if file was modified try rename the old file,
            # before create new one
            if self.file.modified:
                self.try_rename_old_file()

            # create a empty destination file
            self.set_path()

            # Try to move the old file if it still exists
            if self.file.moved:
                if self.try_move_file():
                    return self.success

            # if it is a Description we have to create a descripton file
            # instead of downloading it
            if self.file.content_type == 'description':
                self.create_description()
                return self.success

            # if it is a URL we have to create a shortcut
            # instead of downloading it
            if self.file.module_modname == 'url':
                self.create_shortcut()
                if self.options.get('download_linked_files', False) and not self.is_filtered_external_domain():
                    self.try_download_link()
                    # Warning: try_download_link overwrites saved_to and
                    # time_stamp in move_tmp_file
                return self.success

            self.urlretrieve(
                self._add_token_to_url(self.file.content_fileurl),
                self.file.saved_to,
                context=self.ssl_context,
                reporthook=self.add_progress,
            )

            self.file.time_stamp = int(time.time())

            self.success = True

        except Exception as e:
            self.error = traceback.format_exc() + '\nError:' + str(e)
            filesize = 0
            try:
                filesize = os.path.getsize(self.file.saved_to)
            except Exception:
                pass

            if self.downloaded == 0 and filesize == 0:
                try:
                    # remove touched file
                    os.remove(self.file.saved_to)
                except Exception:
                    pass
            else:
                # Subtract the already downloaded content in case of an error.
                self.thread_report[self.thread_id]['total'] -= self.downloaded
                self.thread_report[self.thread_id]['percentage'] = 100

        return self.success

    @staticmethod
    def urlretrieve(url: str, filename: str, context: ssl.SSLContext, reporthook=None):
        """
        original source:
        https://github.com/python/cpython/blob/
        21bee0bd71e1ad270274499f9f58194ebb52e236/Lib/urllib/request.py#L229

        Because urlopen also supports context,
        I decided to adapt the download function.
        """
        url_parsed = urlparse.urlparse(url)

        request = urllib.request.Request(url=url, headers=RequestHelper.stdHeader)
        with contextlib.closing(urllib.request.urlopen(request, context=context)) as fp:
            headers = fp.info()

            # Just return the local path and the 'headers' for file://
            # URLs. No sense in performing a copy unless requested.
            if url_parsed.scheme == 'file' and not filename:
                return os.path.normpath(url_parsed.path), headers

            if not filename:
                raise RuntimeError('No filename specified!')

            tfp = open(filename, 'wb')

            with tfp:
                result = filename, headers

                # read overall
                read = 0

                # 4kb at once
                bs = 1024 * 8
                blocknum = 0

                # guess size
                size = int(headers.get('Content-Length', -1))

                if reporthook:
                    reporthook(blocknum, bs, size)

                while True:
                    block = fp.read(bs)
                    if not block:
                        break
                    read += len(block)
                    tfp.write(block)
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, bs, size)

        if size >= 0 and read < size:
            raise urllib.ContentTooShortError(
                'retrieval incomplete: got only %i out of %i bytes' % (read, size), result
            )

        return result

    def __str__(self):
        # URLTarget to string
        return 'URLTarget (%(file)s, %(success)s, %(error)s)' % {
            'file': self.file,
            'success': self.success,
            'error': self.error,
        }

