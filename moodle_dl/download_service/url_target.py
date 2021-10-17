import re
import os
import platform
import ssl
import time
import shlex
import socket
import shutil
import urllib
import logging
import posixpath
import traceback
import threading
import subprocess
import contextlib

from pathlib import Path
from http.cookiejar import MozillaCookieJar
from urllib.error import ContentTooShortError
import urllib.parse as urlparse
from email.utils import unquote

import requests
import html2text
import youtube_dl

from youtube_dl.utils import format_bytes, timeconvert
from requests.exceptions import InvalidSchema, InvalidURL, MissingSchema, RequestException

from moodle_dl.state_recorder.file import File
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.path_tools import PathTools
from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.ydl_extractors.extractors import add_additional_extractors


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
        fs_lock: threading.Lock,
        ssl_context: ssl.SSLContext,
        skip_cert_verify: bool,
        options: {},
    ):
        """
        Initiating an URL target.
        """

        self.file = file
        self.course = course
        self.destination = destination
        self.token = token
        self.fs_lock = fs_lock
        self.ssl_context = ssl_context
        self.skip_cert_verify = skip_cert_verify
        self.verify_cert = not skip_cert_verify
        self.options = options

        # get valid filename
        self.filename = PathTools.to_valid_name(self.file.content_filename)

        # To return errors
        self.success = False
        self.error = None

        # To create live reports.
        self.thread_id = 0
        self.thread_report = thread_report

        # Total downloaded.
        self.downloaded = 0

        # For Youtube-dl errors
        self.youtube_dl_failed_with_error = False

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

    def create_dir(self, path: str):
        # Creates the folders of a path if they do not exist.
        if not os.path.exists(path):
            try:
                # raise condition
                logging.debug('T%s - Create directory: "%s"', self.thread_id, path)
                os.makedirs(path)
            except FileExistsError:
                pass

    def _get_path_of_non_existent_file(self, wish_path: str) -> str:
        """Generates a path to a non existing file, based on a wish path

        Args:
            wish_path (str): the ideal path that is wished

        Returns:
            str: a path to a non existing file
        """
        new_path = wish_path

        count = 0
        content_filename = os.path.basename(wish_path)
        destination = os.path.dirname(wish_path)
        filename, file_extension = os.path.splitext(content_filename)

        while os.path.exists(new_path):
            count += 1

            new_filename = '%s_%02d%s' % (filename, count, file_extension)

            new_path = str(Path(destination) / new_filename)

        return new_path

    def _rename_if_exists(self, path: str) -> str:
        """
        Rename a file name until no file with the same name exists.
        @param path: The path to the file to be renamed.
        @return: A path to a file that does not yet exist.
        """

        # lock because of raise condition
        self.fs_lock.acquire()
        new_path = self._get_path_of_non_existent_file(path)

        logging.debug('T%s - Seting up target file: "%s"', self.thread_id, new_path)
        try:
            open(new_path, 'a').close()
        except Exception as e:
            self.fs_lock.release()
            logging.error('T%s - Failed seting up target file: "%s"', self.thread_id, new_path)
            raise e

        self.fs_lock.release()

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

        logging.debug('T%s - Renaming old file', self.thread_id)

        count = 1
        content_filename = os.path.basename(old_path)
        filename, file_extension = os.path.splitext(content_filename)
        content_filename = '%s_old%s' % (filename, file_extension)

        destination = os.path.dirname(old_path)
        new_path = str(Path(destination) / content_filename)

        # lock because of raise condition
        self.fs_lock.acquire()
        new_path = self._get_path_of_non_existent_file(new_path)

        try:
            shutil.move(old_path, new_path)
            self.file.old_file.saved_to = new_path
        except Exception:
            logging.warning('T%s - Failed to renaming old file "%s" to "%s"', self.thread_id, old_path, new_path)
            self.fs_lock.release()
            return False

        self.fs_lock.release()
        return True

    class YtLogger(object):
        """
        Just a logger for Youtube-DL
        """

        def __init__(self, url_target):
            self.url_target = url_target
            self.thread_id = url_target.thread_id

        def clean_msg(self, msg: str) -> str:
            msg = msg.replace('\n', '')
            msg = msg.replace('\r', '')
            msg = msg.replace('\033[K', '')
            msg = msg.replace('\033[0;31m', '')
            msg = msg.replace('\033[0m', '')
            msg = re.sub('token=([a-zA-Z0-9]+)', 'censored_sensitive_data', msg)

            return msg

        def debug(self, msg):
            if msg.find('ETA') >= 0:
                return
            msg = self.clean_msg(msg)
            logging.debug('T%s - youtube-dl Debug: %s', self.thread_id, msg)
            pass

        def warning(self, msg):
            msg = self.clean_msg(msg)
            if msg.find('Falling back') >= 0:
                logging.debug('T%s - youtube-dl Warning: %s', self.thread_id, msg)
                return
            if msg.find('Requested formats are incompatible for merge') >= 0:
                logging.debug('T%s - youtube-dl Warning: %s', self.thread_id, msg)
                return
            logging.warning('T%s - youtube-dl Warning: %s', self.thread_id, msg)

        def error(self, msg):
            msg = self.clean_msg(msg)
            if msg.find('Unsupported URL') >= 0:
                logging.debug('T%s - youtube-dl Error: %s', self.thread_id, msg)
                return
            if msg.find('no suitable InfoExtractor') >= 0:
                logging.debug('T%s - youtube-dl Error: %s', self.thread_id, msg)
                return
            # This is a critical error, with high probability the link can be downloaded at a later time.
            logging.error('T%s - youtube-dl Error: %s', self.thread_id, msg)
            self.url_target.youtube_dl_failed_with_error = True

    def yt_hook(self, d):
        downloaded_bytes = d.get('downloaded_bytes', 0)
        if downloaded_bytes is None:
            downloaded_bytes = 0
        total_bytes_estimate = d.get('total_bytes_estimate', 0)
        if total_bytes_estimate is None:
            total_bytes_estimate = 0
        total_bytes = d.get('total_bytes', 0)
        if total_bytes is None:
            total_bytes = 0

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

    def is_blocked_for_youtube_dl(self, url_to_download: str):
        url_parsed = urlparse.urlparse(url_to_download)
        if url_parsed.hostname.endswith('youtube.com') and url_parsed.path.startswith('/channel/'):
            # We do not want to download whole channels
            return True
        return False

    def set_utime(self, last_modified: str = None):
        """Sets the last modified and last activated time of a downloaded file

        Args:
            last_modified (str, optional): The last_modified header from the Webpage. Defaults to None.
        """

        try:
            if last_modified is not None:
                filetime = timeconvert(last_modified)
                if filetime is not None and filetime > 0:
                    os.utime(self.file.saved_to, (time.time(), filetime))
                    return

            if self.file.content_timemodified is not None and self.file.content_timemodified > 0:
                os.utime(self.file.saved_to, (time.time(), self.file.content_timemodified))

        except Exception:
            logging.debug('T%s - Could not change utime', self.thread_id)

    def try_download_link(
        self, add_token: bool = False, delete_if_successful: bool = False, use_cookies: bool = False
    ) -> bool:
        """This function should only be used for shortcut/URL files.
        It tests whether a URL refers to a file, that is not an HTML web page.
        Then downloads it. Otherwise an attempt will be made to download an HTML video
        from the website.

        Args:
            add_token (bool, optional): Adds the ws-token to the url. Defaults to False.
            delete_if_successful (bool, optional): Deletes the tmp file if download was successful. Defaults to False.
            use_cookies (bool, optional): Adds the cookies to the requests. Defaults to False.

        Returns:
            bool: If it was successful.
        """

        url_to_download = self.file.content_fileurl
        logging.debug('T%s - Try to download linked file %s', self.thread_id, url_to_download)

        if add_token:
            url_to_download = self._add_token_to_url(self.file.content_fileurl)

        cookies_path = self.options.get('cookies_path', None)
        if use_cookies:
            if cookies_path is None or not os.path.isfile(cookies_path):
                self.success = False
                raise ValueError(
                    'Moodle Cookies are missing. Run `moodle-dl -nt` to set a privatetoken for cookie generation (If necessary additionally `-sso`)'
                )

        if delete_if_successful:
            # if temporary file is not needed delete it as soon as possible
            try:
                os.remove(self.file.saved_to)
            except Exception as e:
                logging.warning(
                    'T%s - Could not delete %s before download is started. Error: %s',
                    self.thread_id,
                    self.file.saved_to,
                    e,
                )

        isHTML = False
        new_filename = ""
        total_bytes_estimate = -1
        session = requests.Session()

        if cookies_path is not None:
            session.cookies = MozillaCookieJar(cookies_path)
            if os.path.isfile(cookies_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)

        try:
            response = session.head(
                url_to_download,
                headers=RequestHelper.stdHeader,
                verify=self.verify_cert,
                allow_redirects=True,
                timeout=60,
            )
        except (InvalidSchema, InvalidURL, MissingSchema):
            # don't download urls like 'mailto:name@provider.com'
            logging.debug('T%s - Attempt is aborted because the URL has no correct format', self.thread_id)
            self.success = True
            return False
        except RequestException as error:
            raise ConnectionError("Connection error: %s" % str(error)) from None

        if not response.ok:
            # The URL reports an HTTP error, so we give up trying to download the URL.
            logging.warning(
                'T%s - Stopping the attemp to download %s because of the HTTP ERROR %s',
                self.thread_id,
                self.file.content_fileurl,
                response.status_code,
            )
            self.success = True
            return True

        content_type = response.headers.get('Content-Type', 'text/html').split(';')[0]
        if content_type == 'text/html' or content_type == 'text/plain':
            isHTML = True

        total_bytes_estimate = int(response.headers.get('Content-Length', -1))
        last_modified = response.headers.get('Last-Modified', None)

        if response.url != url_to_download:
            if response.history and len(response.history) > 0:
                logging.debug('T%s - URL was %s time(s) redirected', self.thread_id, len(response.history))
            else:
                logging.debug('T%s - URL has changed after information retrieval', self.thread_id)
            url_to_download = response.url

        url_parsed = urlparse.urlparse(url_to_download)
        new_filename = posixpath.basename(url_parsed.path)

        if "Content-Disposition" in response.headers.keys():
            found_names = re.findall("filename=(.+)", response.headers["Content-Disposition"])
            if len(found_names) > 0:
                new_filename = unquote(found_names[0])

        external_file_downloaders = self.options.get('external_file_downloaders', {})
        external_file_downloader = external_file_downloaders.get(url_parsed.netloc, "")
        if isHTML and external_file_downloader != "":
            # This link is to be downloaded from an external program.
            cmd = external_file_downloader.replace('%U', url_to_download)
            logging.debug(
                'T%s - Run external downloader using the following command: `%s`',
                self.thread_id,
                cmd,
            )
            external_dl_failed_with_error = False

            try:
                p = subprocess.Popen(
                    shlex.split(cmd),
                    cwd=str(self.destination),
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                )

                for line in p.stdout:
                    # line = line.decode('utf-8', 'replace')
                    self.thread_report[self.thread_id]['external_dl'] = line.replace('\n', '').replace('\r', '')

                _, stderr = p.communicate()

                if p.returncode != 0:
                    external_dl_failed_with_error = True
            except Exception as e:
                stderr = str(e)
                external_dl_failed_with_error = True

            if external_dl_failed_with_error:
                logging.error('T%s - External Downloader Error: %s', self.thread_id, stderr)
                if not delete_if_successful:
                    # cleanup the url-link file
                    try:
                        os.remove(self.file.saved_to)
                    except Exception as e:
                        logging.warning(
                            'T%s - Could not delete %s after external downloader failed. Error: %s',
                            self.thread_id,
                            self.file.saved_to,
                            e,
                        )
                self.success = False
                raise RuntimeError(
                    'The external downloader could not download the URL.'
                    + ' For details, see the error messages in the log file.'
                )
            else:
                self.file.saved_to = str(Path(self.destination) / self.filename)
                self.file.time_stamp = int(time.time())
                self.success = True
                return True

        elif isHTML and not self.is_blocked_for_youtube_dl(url_to_download):

            filename_tmpl = self.filename + ' - %(title)s (%(id)s).%(ext)s'
            if self.file.content_type == 'description-url':
                filename_tmpl = '%(title)s (%(id)s).%(ext)s'
            outtmpl = str(Path(self.destination) / filename_tmpl)

            ydl_opts = {
                'logger': self.YtLogger(self),
                'progress_hooks': [self.yt_hook],
                'outtmpl': outtmpl,
                'nocheckcertificate': self.skip_cert_verify,
                'retries': 10,
                'fragment_retries': 10,
                'ignoreerrors': True,
                'addmetadata': True,
            }

            youtube_dl_options = self.options.get('youtube_dl_options', {})
            ydl_opts.update(youtube_dl_options)

            if cookies_path is not None and os.path.isfile(cookies_path):
                ydl_opts.update({'cookiefile': cookies_path})

            ydl = youtube_dl.YoutubeDL(ydl_opts)
            add_additional_extractors(ydl)

            videopasswords = self.options.get('videopasswords', {})
            password_list = videopasswords.get(url_parsed.netloc, [])
            if not type(password_list) is list:
                password_list = [password_list]

            idx_pw = 0
            while True:
                if idx_pw + 1 <= len(password_list):
                    ydl.params['videopassword'] = password_list[idx_pw]

                self.youtube_dl_failed_with_error = False
                # we restart youtube-dl, so we need to reset the return code
                ydl._download_retcode = 0
                try:
                    ydl_results = ydl.download([url_to_download])
                    if ydl_results == 1:
                        pass
                    elif self.file.module_name != 'index_mod-page':
                        self.file.saved_to = str(Path(self.destination) / self.filename)
                        self.file.time_stamp = int(time.time())

                        self.success = True
                        return True
                    else:
                        break
                except Exception as e:
                    logging.error(
                        'T%s - Youtube-dl failed! Error: %s',
                        self.thread_id,
                        e,
                    )
                    self.youtube_dl_failed_with_error = True
                idx_pw += 1
                if idx_pw + 1 > len(password_list):
                    break

            # if we want we could save ydl.cookiejar (Also the cookiejar of moodle-dl)

            if self.youtube_dl_failed_with_error is True and not self.options.get('ignore_ytdl_errors', False):
                if not delete_if_successful:
                    # cleanup the url-link file
                    try:
                        os.remove(self.file.saved_to)
                    except Exception as e:
                        logging.warning(
                            'T%s - Could not delete %s after youtube-dl failed. Error: %s',
                            self.thread_id,
                            self.file.saved_to,
                            e,
                        )
                self.success = False
                raise RuntimeError(
                    'Youtube-dl could not download the URL. For details see youtube-dl error messages in the log file. '
                    + 'You can ignore this error by running `moodle-dl --ignore-ytdl-errors` once.'
                )

        logging.debug('T%s - Downloading file directly', self.thread_id)

        # generate file extension for modules names
        new_name, new_extension = os.path.splitext(new_filename)
        if new_extension == '' and isHTML:
            new_extension = '.html'

        if self.file.content_type == 'description-url' and new_name != '':
            self.filename = new_name + new_extension

        old_name, old_extension = os.path.splitext(self.filename)

        if old_extension != new_extension:
            self.filename = self.filename + new_extension

        self.set_path(True)

        if total_bytes_estimate != -1:
            self.thread_report[self.thread_id]['extra_totalsize'] = total_bytes_estimate

        self.urlretrieve(
            url_to_download,
            self.file.saved_to,
            context=self.ssl_context,
            reporthook=self.add_progress,
            cookies_path=cookies_path,
        )

        self.set_utime(last_modified)
        self.file.time_stamp = int(time.time())

        self.success = True
        return True

    def is_filtered_external_domain(self):
        """
        This function is used for external linked files.
        It checks if the domain of the download link is on the blacklist
        or is not on the whitelist.

        Returns True if the domain is filtered.
        """

        url_parsed = urlparse.urlparse(self.file.content_fileurl)
        domain = url_parsed.hostname

        blacklist = self.options.get('download_domains_blacklist', [])
        whitelist = self.options.get('download_domains_whitelist', [])

        in_blacklist = False

        for entry in blacklist:
            if domain == entry or domain.endswith('.' + entry):
                in_blacklist = True
                break

        in_whitelist = len(whitelist) == 0

        for entry in whitelist:
            if domain == entry or domain.endswith('.' + entry):
                in_whitelist = True
                break

        return not in_whitelist or in_blacklist

    def create_shortcut(self):
        """
        Creates a Shortcut to a URL
        Because shortcuts are different under Windows and Unix,
        both cases are covered here.
        """

        logging.debug('T%s - Creating a shortcut', self.thread_id)
        with open(self.file.saved_to, 'w+', encoding='utf-8') as shortcut:
            if os.name == 'nt' or platform.system() == "Darwin":
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

    def set_path(self, ignore_attributes: bool = False):
        """Sets the path where a file should be created.
        It takes into account which file type is involved.
        An empty temporary file is created which may need to be cleaned up.

        Args:
            ignore_attributes (bool, optional): If the file attributes should be ignored. Defaults to False.
        """

        if self.file.content_type == 'description' and not ignore_attributes:
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.md'))

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

        elif self.file.module_modname.startswith('url') and not ignore_attributes:
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.desktop'))
            if os.name == 'nt' or platform.system() == "Darwin":
                self.file.saved_to = str(Path(self.destination) / (self.filename + '.URL'))

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

        else:  # normal path
            self.file.saved_to = str(Path(self.destination) / self.filename)

            self.file.saved_to = self._rename_if_exists(self.file.saved_to)

    def create_description(self):
        """
        Creates a Description file
        """
        logging.debug('T%s - Creating a description file', self.thread_id)
        description = open(self.file.saved_to, 'w+', encoding='utf-8')
        to_save = ""
        if self.file.text_content is not None:
            h2t_handler = html2text.HTML2Text()
            to_save = h2t_handler.handle(self.file.text_content).strip()
            # to_save could also be html.unescape(),
            # but this could destroy the md file
            if to_save != '':
                description.write(to_save)

        description.close()

        if to_save == '':
            logging.debug('T%s - Remove target file because description file would be empty', self.thread_id)
            os.remove(self.file.saved_to)

            self.file.time_stamp = int(time.time())

            self.success = True
        else:
            self.set_utime()
            self.file.time_stamp = int(time.time())

            self.success = True

    def create_html_file(self):
        """
        Creates a HTML file
        """
        logging.debug('T%s - Creating a html file', self.thread_id)
        html_file = open(self.file.saved_to, 'w+', encoding='utf-8')
        to_save = ""
        if self.file.html_content is not None:
            to_save = self.file.html_content

            if to_save != '':
                html_file.write(to_save)

        html_file.close()

        if to_save == '':
            logging.debug('T%s - Remove target file because html file would be empty', self.thread_id)
            os.remove(self.file.saved_to)

            self.file.time_stamp = int(time.time())

            self.success = True
        else:
            self.set_utime()
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

        logging.debug('T%s - Moving old file "%s" to new target location', self.thread_id, old_path)
        try:
            shutil.move(old_path, self.file.saved_to)
            self.file.time_stamp = int(time.time())
            self.success = True
            return True
        except FileExistsError:
            # On Windows, the temporary file must be deleted first.
            # lock because of raise condition
            self.fs_lock.acquire()

            try:
                os.remove(self.file.saved_to)
                shutil.move(old_path, self.file.saved_to)
                self.file.time_stamp = int(time.time())
                self.success = True

                self.fs_lock.release()
                return True
            except Exception as e:
                logging.warning('T%s - Moving the old file %s failed!  Error: %s', self.thread_id, old_path, e)

            self.fs_lock.release()
        except Exception as e:
            logging.warning('T%s - Moving the old file %s failed unexpectedly!  Error: %s', self.thread_id, old_path, e)

        return False

    def store_data_url(self):
        url_to_download = self.file.content_fileurl
        logging.debug('T%s - Data-URL detected', self.thread_id)
        try:
            os.remove(self.file.saved_to)
        except Exception as e:
            logging.warning(
                'T%s - Could not delete %s before storing data url. Error: %s',
                self.thread_id,
                self.file.saved_to,
                e,
            )
        self.set_path(True)
        with urllib.request.urlopen(url_to_download) as response:
            data = response.read()

        with open(self.file.saved_to, "wb") as target_file:
            target_file.write(data)

        self.set_utime()
        self.file.time_stamp = int(time.time())
        self.success = True

    def download(self, thread_id: int):
        """
        Downloads a file
        """
        self.thread_id = thread_id

        # reset download status
        self.downloaded = 0
        self.thread_report[self.thread_id]['percentage'] = 0
        self.thread_report[self.thread_id]['extra_totalsize'] = None
        self.thread_report[self.thread_id]['current_url'] = self.file.content_fileurl
        self.thread_report[self.thread_id]['external_dl'] = None
        self.youtube_dl_failed_with_error = False

        try:
            logging.debug('T%s - Starting downloading of: %s', self.thread_id, self)
            self.create_dir(self.destination)

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

            # if it is a Description we have to create a description file
            # instead of downloading it
            if self.file.content_type == 'description':
                self.create_description()
                return self.success

            # if it is a HTML-File we have to create a HTML file
            # instead of downloading it
            if self.file.content_type == 'html':
                self.create_html_file()
                return self.success

            add_token = True
            if self.file.module_modname.startswith('index_mod'):
                add_token = True
                self.try_download_link(add_token, delete_if_successful=True, use_cookies=False)
                return self.success

            if self.file.module_modname.startswith('cookie_mod'):
                add_token = False
                self.try_download_link(add_token, delete_if_successful=True, use_cookies=True)
                return self.success

            # if it is a URL we have to create a shortcut
            # instead of downloading it
            if self.file.module_modname.startswith('url') and not self.file.content_fileurl.startswith('data:'):
                self.create_shortcut()
                add_token = False
                if self.options.get('download_linked_files', False) and not self.is_filtered_external_domain():
                    self.try_download_link(add_token, False, False)
                return self.success

            if self.file.content_fileurl.startswith('data:'):
                self.store_data_url()
                return self.success

            url_to_download = self.file.content_fileurl
            logging.debug('T%s - Downloading %s', self.thread_id, url_to_download)

            if add_token:
                url_to_download = self._add_token_to_url(self.file.content_fileurl)

            cookies_path = self.options.get('cookies_path', None)

            self.urlretrieve(
                url_to_download,
                self.file.saved_to,
                context=self.ssl_context,
                reporthook=self.add_progress,
                cookies_path=cookies_path,
            )

            self.set_utime()
            self.file.time_stamp = int(time.time())

            self.success = True

        except Exception as e:
            self.error = e
            filesize = 0
            try:
                filesize = os.path.getsize(self.file.saved_to)
            except Exception:
                pass

            logging.error('T%s - Error while trying to download file: %s', self.thread_id, self)
            logging.error('T%s - Traceback:\n%s', self.thread_id, traceback.format_exc())

            if self.downloaded == 0 and filesize == 0:
                try:
                    # remove touched file
                    if os.path.exists(self.file.saved_to):
                        os.remove(self.file.saved_to)
                except Exception as e:
                    logging.warning(
                        'T%s - Could not delete %s after thread failed. Error: %s',
                        self.thread_id,
                        self.file.saved_to,
                        e,
                    )
            else:
                # Subtract the already downloaded content in case of an error.
                self.thread_report[self.thread_id]['total'] -= self.downloaded
                self.thread_report[self.thread_id]['percentage'] = 100

        return self.success

    def urlretrieve(self, url: str, filename: str, context: ssl.SSLContext, reporthook=None, cookies_path=None):
        """
        original source:
        https://github.com/python/cpython/blob/
        21bee0bd71e1ad270274499f9f58194ebb52e236/Lib/urllib/request.py#L229

        Because urlopen also supports context,
        I decided to adapt the download function.
        """
        start = time.time()
        url_parsed = urlparse.urlparse(url)

        request = urllib.request.Request(url=url, headers=RequestHelper.stdHeader)
        if cookies_path is not None:
            cookie_jar = MozillaCookieJar(cookies_path)
            if os.path.isfile(cookies_path):
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                cookie_jar.add_cookie_header(request)

        with contextlib.closing(urllib.request.urlopen(request, context=context, timeout=60)) as fp:
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
                    try:
                        block = fp.read(bs)
                    except (socket.timeout, socket.error) as error:
                        raise ConnectionError("Connection error: %s" % str(error)) from None

                    if not block:
                        break
                    read += len(block)
                    tfp.write(block)
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, bs, size)

        if size >= 0 and read < size:
            raise ContentTooShortError('retrieval incomplete: got only %i out of %i bytes' % (read, size), result)

        end = time.time()
        logging.debug(
            'T%s - Download of %s finished in %s', self.thread_id, format_bytes(read), self.format_seconds(end - start)
        )

        return result

    @staticmethod
    def format_seconds(seconds):
        (mins, secs) = divmod(seconds, 60)
        (hours, mins) = divmod(mins, 60)
        if hours > 99:
            return '--:--:--'
        if hours == 0:
            return '%02d:%02d' % (mins, secs)
        else:
            return '%02d:%02d:%02d' % (hours, mins, secs)

    def __str__(self):
        # URLTarget to string
        return 'URLTarget (%(file)s, %(course)s, %(success)s, Error: %(error)s)' % {
            'file': self.file,
            'course': self.course,
            'success': self.success,
            'error': self.error,
        }
