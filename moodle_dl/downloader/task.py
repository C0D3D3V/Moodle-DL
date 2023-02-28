import asyncio
import functools
import logging
import os
import platform
import posixpath
import re
import shlex
import shutil
import subprocess
import time
import traceback
import urllib
import urllib.parse as urlparse

from concurrent.futures import ThreadPoolExecutor
from email.utils import unquote
from io import StringIO
from pathlib import Path
from typing import Callable, Dict
from urllib.error import ContentTooShortError

import aiofiles
import aiohttp
import html2text
import yt_dlp

from moodle_dl.downloader.extractors import add_additional_extractors
from moodle_dl.types import Course, File, DownloadOptions, TaskStatus, DlEvent, TaskState, HeadInfo
from moodle_dl.utils import (
    format_bytes,
    timeconvert,
    SslHelper,
    PathTools as PT,
    MoodleDLCookieJar,
    format_seconds,
    Timer,
    convert_to_aiohttp_cookie_jar,
)


class Task:
    "Task is responsible to download or create a file"
    CHUNK_SIZE = 102400  # default: 1024 * 100 = 100kb; will be overwritten with download_chunk_size
    MAX_DL_RETRIES = 3

    RQ_HEADER = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 7.1.1; Moto G Play Build/NPIS26.48-43-2; wv) AppleWebKit/537.36'
            + ' (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 MoodleMobile'
        ),
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(
        self,
        task_id: int,
        file: File,
        course: Course,
        options: DownloadOptions,
        thread_pool: ThreadPoolExecutor,
        callback: Callable[[], None],
    ):
        self.task_id = task_id
        self.file = file
        self.course = course
        self.opts = options
        self.thread_pool = thread_pool
        self.callback = callback

        self.destination = self.gen_path(options.global_opts.path, course, file)
        self.filename = PT.to_valid_name(self.file.content_filename, is_file=True)
        self.status = TaskStatus()

    @staticmethod
    def gen_path(storage_path: str, course: Course, file: File):
        "Generate the directory path where a file should be stored"
        course_name = course.fullname
        if course.overwrite_name_with is not None:
            course_name = course.overwrite_name_with

        # TODO: Move this out of the downloader
        # if a flat path is requested
        if not course.create_directory_structure:
            return PT.flat_path_of_file(storage_path, course_name, file.content_filepath)

        # TODO: Get mod names automated; all mods should be in a sub-folder
        # If the file is located in a folder or in an assignment,
        # it should be saved in a sub-folder (with the name of the module).
        if file.module_modname.endswith(('assign', 'data', 'folder', 'forum', 'lesson', 'page', 'quiz', 'workshop')):
            file_path = file.content_filepath
            if file.content_type == 'submission_file':
                file_path = os.path.join('/submissions/', file_path.strip('/'))

            return PT.path_of_file_in_module(storage_path, course_name, file.section_name, file.module_name, file_path)
        return PT.path_of_file(storage_path, course_name, file.section_name, file.content_filepath)

    def add_token_to_url(self, url: str) -> str:
        """
        Adds the Moodle token to a URL
        @param url: The URL to that the token should be added.
        @return: The URL with the token.
        """
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': self.opts.token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)

    def create_target_file(self, target_path: str) -> str:
        """
        Rename target_path if necessary to a unused filename and touch the target_path
        @return: Path to the touched target file
        """
        target_path = PT.get_unused_file_path(target_path)
        PT.touch_file(target_path)
        return target_path

    def rename_old_file(self) -> bool:
        """
        Try to rename an existing modified file. Add the extension '_old' to the filename if possible.
        @return: True on success
        """
        if self.file.old_file is None:
            return False

        old_path = self.file.old_file.saved_to
        if not os.path.exists(old_path):
            return False

        logging.debug('[%d] Renaming old file', self.task_id)

        destination, filename, file_extension = PT.get_path_parts(old_path)
        new_filename = f'{filename}_old{file_extension}'
        new_path = PT.get_unused_file_path(PT.make_path(destination, new_filename))

        try:
            shutil.move(old_path, new_path)
            self.file.old_file.saved_to = new_path
        except OSError:
            logging.warning('[%d] Failed to renaming old file %r to %r', self.task_id, old_path, new_path)
            return False

        return True

    class YtLogger:
        "logger for yt-dlp"

        def __init__(self, task):
            self.task = task
            self.task_id = task.task_id

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
            logging.debug('[%d] yt-dlp Debug: %s', self.task_id, msg)

        def warning(self, msg):
            msg = self.clean_msg(msg)
            if (msg.find('Falling back on generic information extractor')) >= 0 or (
                msg.find('Forcing generic information extractor') >= 0
            ):
                self.task.status.yt_dlp_used_generic_extractor = True
                logging.debug('[%d] yt-dlp Warning: %s', self.task_id, msg)
                return
            if msg.find('Requested formats are incompatible for merge') >= 0:
                logging.debug('[%d] yt-dlp Warning: %s', self.task_id, msg)
                return
            logging.warning('[%d] yt-dlp Warning: %s', self.task_id, msg)

        def error(self, msg):
            msg = self.clean_msg(msg)
            if msg.find('Unsupported URL') >= 0:
                logging.debug('[%d] yt-dlp Error: %s', self.task_id, msg)
                return
            if msg.find('no suitable InfoExtractor') >= 0:
                logging.debug('[%d] yt-dlp Error: %s', self.task_id, msg)
                return
            # This is a critical error, with high probability the link can be downloaded at a later time.
            logging.error('[%d] yt-dlp Error: %s', self.task_id, msg)
            self.task.status.yt_dlp_failed_with_error = True

    def yt_hook(self, data: Dict):
        """
        @param data: a dictionary with the entries
            * status: One of "downloading", "error", or "finished". Check this first and ignore unknown values.
            * info_dict: The extracted info_dict

            If status is one of "downloading", or "finished", the following properties may also be present:
            * filename: The final filename (always present)
            * tmpfilename: The filename we're currently writing to
            * downloaded_bytes: Bytes on disk
            * total_bytes: Size of the whole file, None if unknown
            * total_bytes_estimate: Guess of the eventual file size, None if unavailable.
            * elapsed: The number of seconds since download started.
            * eta: The estimated time in seconds, None if unknown
            * speed: The download speed in bytes/second, None if unknown
            * fragment_index: The counter of the currently downloaded video fragment.
            * fragment_count: The number of fragments (= individual files that will be merged)

            Progress hooks are guaranteed to be called at least once
            (with status "finished") if the download is successful.
        """
        if data['status'] == 'error':
            return

        tmp_file_name = data.get('tmpfilename')
        if tmp_file_name is None or tmp_file_name == '':
            # for some unknown reason sometimes the filename is missing
            return
        content_length = data.get('total_bytes', 0) or 0
        if content_length <= 0:
            total_bytes_estimate = data.get('total_bytes_estimate', 0) or 0
            content_length = total_bytes_estimate
        bytes_received_total = data.get('downloaded_bytes', 0) or 0

        self.status.yt_dlp_current_file = tmp_file_name
        self.report_yt_dlp_content_length(content_length, tmp_file_name)
        self.report_yt_dlp_received_bytes(bytes_received_total, tmp_file_name)

    def report_yt_dlp_content_length(self, content_length: int, file_name: str):
        if file_name not in self.status.yt_dlp_total_size_per_file:
            self.status.yt_dlp_total_size_per_file[file_name] = content_length
            self.status.external_total_size += content_length
            self.callback(DlEvent.TOTAL_SIZE, self, content_length=content_length)
            return
        old_content_length = self.status.yt_dlp_total_size_per_file[file_name]
        if old_content_length != content_length:
            content_length_diff = content_length - old_content_length
            self.status.external_total_size += content_length_diff
            self.callback(DlEvent.TOTAL_SIZE_UPDATE, self, content_length_diff=content_length_diff)
            self.status.yt_dlp_total_size_per_file[file_name] = content_length

    def report_yt_dlp_received_bytes(self, bytes_received_total: int, file_name: str):
        if file_name not in self.status.yt_dlp_bytes_downloaded_per_file:
            self.status.yt_dlp_bytes_downloaded_per_file[file_name] = bytes_received_total
            self.status.bytes_downloaded += bytes_received_total
            self.callback(DlEvent.RECEIVED, self, bytes_received=bytes_received_total)
            return
        old_bytes_downloaded = self.status.yt_dlp_bytes_downloaded_per_file[file_name]
        bytes_received = bytes_received_total - old_bytes_downloaded
        if bytes_received > 0:
            self.status.yt_dlp_bytes_downloaded_per_file[file_name] = bytes_received_total
            self.status.bytes_downloaded += bytes_received
            self.callback(DlEvent.RECEIVED, self, bytes_received=bytes_received)
        elif bytes_received < 0:
            logging.debug('Calculation error in report_yt_dlp_received_bytes')

    def yt_hook_after_move(self, final_filename: str):
        """
        Get called as the final step for each video file, after all postprocessors have been called.
        @param final_filename: The filename will be passed as the only argument.
        """
        rel_pos = final_filename.find(self.destination)
        if rel_pos >= 0:
            final_filename = final_filename[rel_pos:]
        self.file.saved_to = final_filename

    def is_blocked_for_yt_dlp(self, url: str):
        url_parsed = urlparse.urlparse(url)
        # Do not download whole YT channels
        if url_parsed.hostname.endswith('youtube.com') and url_parsed.path.startswith('/channel/'):
            return True
        return False

    def set_utime(self, last_modified_header: str = None):
        """
        Sets the last modified time of the downloaded file
        Modified time will be set based on the given last_modified value or the moodle file attribute timemodified
        Access time will always be set to now

        @param last_modified_header: The last_modified header from the Webpage. Defaults to None.
        """
        if not os.path.isfile(self.file.saved_to):
            return
        try:
            if last_modified_header is not None:
                server_modified_time = timeconvert(last_modified_header)
                if server_modified_time is not None and server_modified_time > 0:
                    os.utime(self.file.saved_to, (time.time(), server_modified_time))
                    return

            if self.file.content_timemodified is not None and self.file.content_timemodified > 0:
                os.utime(self.file.saved_to, (time.time(), self.file.content_timemodified))

        except OSError:
            logging.debug(
                '[%d] Access time and modification time of the downloaded file could not be set', self.task_id
            )

    async def get_head_infos(self, dl_url: str) -> HeadInfo:
        """
        Do a Head request to collect some information about the URL
        @return: If download should be aborted then None; else HeadInfo
        """
        ssl_context = SslHelper.get_ssl_context(
            self.opts.global_opts.skip_cert_verify, self.opts.global_opts.allow_insecure_ssl
        )
        async with aiohttp.ClientSession(cookie_jar=self.get_cookie_jar(), raise_for_status=True) as session:
            try:
                async with session.request("HEAD", dl_url, headers=self.RQ_HEADER, ssl=ssl_context, timeout=20) as resp:
                    if resp.url != dl_url:
                        if resp.history and len(resp.history) > 0:
                            logging.debug('[%d] URL was %s time(s) redirected', self.task_id, len(resp.history))
                        else:
                            logging.debug('[%d] URL has changed after information retrieval', self.task_id)

                    guessed_file_name = posixpath.basename(resp.url.path)
                    if "Content-Disposition" in resp.headers.keys():
                        # Exp: Content-Disposition: attachment; filename="filename.jpg"
                        found_names = re.findall("filename=(.+)", resp.headers["Content-Disposition"])
                        if len(found_names) > 0:
                            guessed_file_name = unquote(found_names[0])

                    return HeadInfo(
                        # Exp: Content-Type: text/html; charset=utf-8
                        content_type=resp.headers.get('Content-Type', 'text/html').split(';')[0],
                        content_length=int(resp.headers.get('Content-Length', -1)),
                        # Exp: Last-Modified: Wed, 21 Oct 2015 07:28:00 GMT
                        last_modified=resp.headers.get('Last-Modified', None),
                        final_url=str(resp.url),
                        guessed_file_name=guessed_file_name,
                        host=resp.url.host,
                    )

            except aiohttp.InvalidURL:
                # don't download urls like 'mailto:name@provider.com'
                logging.debug(
                    '[%d] Download of the external file was canceled because the URL has an invalid format',
                    self.task_id,
                )
                return None
            except aiohttp.ClientResponseError as head_err:
                if head_err.status in [408, 409, 429]:
                    # 408 (timeout) or 409 (conflict) and 429 (too many requests)
                    logging.warning(
                        '[%d] Head request failed with status: %s %s', self.task_id, head_err.status, head_err.message
                    )
                    raise head_err from None

                logging.warning(
                    '[%d] Download of the external file was canceled because of HTTP error: %s %s',
                    self.task_id,
                    head_err.status,
                    head_err.message,
                )
                return None

            except (aiohttp.ClientError, OSError, ValueError, ContentRangeError) as head_err:
                logging.warning('[%d] Head request for external file failed with unexpected error', self.task_id)
                raise head_err from None

    async def download_using_yt_dlp(self, dl_url: str, infos: HeadInfo, delete_if_successful: bool, use_cookies: bool):
        """
        @param delete_if_successful: Deletes the tmp file if download was successful
        @param use_cookies:  Adds the cookies to the requests
        @return: False if the page should be downloaded anyway; True if yt-dlp has processed the URL and we are done
        """
        # We try to limit the filename to < 250 chars
        if self.file.content_type == 'description-url':
            filename_template = '%(title).180B (%(id).32B).%(ext)s'
        else:
            filename_template = (
                PT.truncate_filename(self.filename, is_file=True, max_length=90) + ' - %(title).90B (%(id).32B).%(ext)s'
            )
        output_template = str(Path(self.destination) / filename_template)

        ydl_opts = {
            'logger': self.YtLogger(self),
            'progress_hooks': [self.yt_hook],
            'post_hooks': [self.yt_hook_after_move],
            'outtmpl': output_template,
            'nocheckcertificate': self.opts.global_opts.skip_cert_verify,
            'retries': 10,
            'fragment_retries': 10,
            'ignoreerrors': True,
            'addmetadata': True,
            'restrictfilenames': self.opts.restricted_filenames,
        }

        ydl_opts.update(self.opts.yt_dlp_options)

        if use_cookies and self.opts.cookies_text is not None:
            ydl_opts.update({'cookiefile': StringIO(self.opts.cookies_text)})

        ydl = yt_dlp.YoutubeDL(ydl_opts)
        add_additional_extractors(ydl)

        password_list = self.opts.video_passwords.get(infos.host, [None])
        if not isinstance(password_list, list):
            password_list = [password_list]
        if len(password_list) == 0:
            # Try at least once with no password
            password_list = [None]

        for password in password_list:
            if password is not None:
                # We allow to set videopassword via yt_dlp_options, so do not overwrite it with None
                ydl.params['videopassword'] = password

            # We restart yt-dlp, so we need to reset the return code
            self.status.yt_dlp_failed_with_error = False
            self.status.yt_dlp_used_generic_extractor = False
            ydl._download_retcode = 0  # pylint: disable=protected-access
            try:
                loop = asyncio.get_running_loop()
                ydl_result = await loop.run_in_executor(self.thread_pool, functools.partial(ydl.download, dl_url))
                # We set the saved_to path in yt_hook_after_move
                if ydl_result == 0:
                    if self.file.module_name == 'index_mod-page':
                        # We want to download legacy moodle pages
                        return False
                    # yt-dlp has an extractor for this URL so we do not want to download the URL extra
                    # only if yt-dlp used a generic extractor
                    return not self.status.yt_dlp_used_generic_extractor
            except Exception as yt_err:
                logging.error('[%d] yt-dlp failed! Error: %s', self.task_id, yt_err)
                self.status.yt_dlp_failed_with_error = True

        # If we want we could save ydl.cookiejar (Also the cookiejar of moodle-dl)

        if self.status.yt_dlp_failed_with_error and not self.opts.global_opts.ignore_ytdl_errors:
            if not delete_if_successful:
                PT.remove_file(self.file.saved_to)
            raise RuntimeError(
                'yt-dlp could not download the URL.'
                + ' You can ignore this error by running `moodle-dl --ignore-ytdl-errors` once.'
            )

        # We want to download the URL because yt-dlp has no extractor for it
        return False

    async def download_using_external_downloader(self, dl_url: str, external_dl_cmd: str, delete_if_successful: bool):
        cmd = external_dl_cmd.replace('%U', dl_url)
        logging.debug(
            '[%d] Run external downloader using the following command: `%s`',
            self.task_id,
            cmd,
        )
        external_dl_failed_with_error = False
        try:
            proc = await asyncio.create_subprocess_exec(
                shlex.split(cmd),
                cwd=str(self.destination),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )

            for lines in await proc.stdout.readline():
                # line = line.decode('utf-8', 'replace')
                logging.debug('[%d] Ext-Dl: %s', self.task_id, lines.splitlines()[-1])

            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                external_dl_failed_with_error = True
        except (subprocess.SubprocessError, ValueError, TypeError) as e:
            stderr = str(e)
            external_dl_failed_with_error = True

        if external_dl_failed_with_error:
            logging.error('[%d] External downloader error: %s', self.task_id, stderr)
            if not delete_if_successful:
                # cleanup the url-link file
                PT.remove_file(self.file.saved_to)
            raise RuntimeError('The external downloader could not download the URL')

        self.file.saved_to = str(Path(self.destination) / self.filename)

    async def external_download_url(self, add_token: bool, delete_if_successful: bool, use_cookies: bool):
        """
        Use only for "external" shortcut/URL files.
        It tests whether a URL refers to a file, that is not an HTML web page then downloads it.
        Otherwise an attempt will be made to download it using yt-dlp.

        @param add_token: Adds the ws-token to the url
        @param delete_if_successful: Deletes the tmp file if download was successful
        @param use_cookies:  Adds the cookies to the requests
        In case of an failure an exception will be raised
        """
        url_to_download = self.file.content_fileurl
        logging.debug('[%d] Try to download external file %s', self.task_id, url_to_download)

        if add_token:
            url_to_download = self.add_token_to_url(url_to_download)

        if delete_if_successful:
            # If temporary file is not needed delete it as soon as possible
            PT.remove_file(self.file.saved_to)

        if use_cookies and self.opts.cookies_text is None:
            # Without cookies we can not proceed
            raise ValueError(
                'Moodle cookies are missing. Set a private token so that moodle-dl can obtain moodle cookies'
            )

        infos = await self.get_head_infos(url_to_download)
        if infos is None:
            # Head request failed but we declare it as success (because URL is broken)
            return
        url_to_download = infos.final_url

        external_dl_cmd = self.opts.external_file_downloaders.get(infos.host, "")
        if infos.is_html and external_dl_cmd != "":
            await self.download_using_external_downloader(
                dl_url=url_to_download,
                external_dl_cmd=external_dl_cmd,
                delete_if_successful=delete_if_successful,
            )
            return
        if infos.is_html and not self.is_blocked_for_yt_dlp(url_to_download):
            yt_dlp_processed = await self.download_using_yt_dlp(
                dl_url=url_to_download,
                infos=infos,
                delete_if_successful=delete_if_successful,
                use_cookies=use_cookies,
            )
            if yt_dlp_processed:
                return

        logging.debug('[%d] Downloading URL directly', self.task_id)

        # Generate file name for external file
        new_name, new_extension = os.path.splitext(infos.guessed_file_name)
        if new_extension == '' or infos.is_html:
            new_extension = '.html'

        if self.file.content_type == 'description-url' and new_name != '':
            self.filename = new_name + new_extension

        _old_name, old_extension = os.path.splitext(self.filename)
        if old_extension != new_extension:
            self.filename = self.filename + new_extension

        self.set_path(True)

        await self.download_url(url_to_download, self.file.saved_to)

    def is_filtered_external_domain(self):
        """
        Filter external linked files.
        Check if the domain of the download link is on the blacklist or is not on the whitelist.

        @return: True if the domain is filtered.
        """

        domain = urlparse.urlparse(self.file.content_fileurl).hostname

        in_blacklist = False
        for entry in self.opts.download_domains_blacklist:
            if domain == entry or domain.endswith('.' + entry):
                in_blacklist = True
                break

        in_whitelist = len(self.opts.download_domains_whitelist) == 0
        for entry in self.opts.download_domains_whitelist:
            if domain == entry or domain.endswith('.' + entry):
                in_whitelist = True
                break

        return not in_whitelist or in_blacklist

    async def create_shortcut(self):
        "Create a Shortcut to a URL"
        logging.debug('[%d] Creating a shortcut', self.task_id)
        async with aiofiles.open(self.file.saved_to, 'w+', encoding='utf-8') as shortcut:
            if os.name == 'nt' or platform.system() == "Darwin":
                await shortcut.write('[InternetShortcut]' + os.linesep)
                await shortcut.write('URL=' + self.file.content_fileurl + os.linesep)
            else:
                await shortcut.write('[Desktop Entry]' + os.linesep)
                await shortcut.write('Encoding=UTF-8' + os.linesep)
                await shortcut.write('Name=' + self.filename + os.linesep)
                await shortcut.write('Type=Link' + os.linesep)
                await shortcut.write('URL=' + self.file.content_fileurl + os.linesep)
                await shortcut.write('Icon=text-html' + os.linesep)
                await shortcut.write('Name[en_US]=' + self.filename + os.linesep)

    def set_path(self, ignore_attributes: bool = False):
        """Set the path where a file should be created. The file type is used to set the needed file extension.
        An empty target file is created which may need to be cleaned up.

        @param ignore_attributes: If the file attributes should be ignored.
        """

        if self.file.content_type == 'description' and not ignore_attributes:
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.md'))

        elif self.file.content_type == 'html' and not ignore_attributes:
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.html'))

        elif self.file.module_modname.startswith('url') and not ignore_attributes:
            self.file.saved_to = str(Path(self.destination) / (self.filename + '.desktop'))
            if os.name == 'nt' or platform.system() == "Darwin":
                self.file.saved_to = str(Path(self.destination) / (self.filename + '.URL'))

        else:  # normal path
            self.file.saved_to = str(Path(self.destination) / self.filename)

        self.file.saved_to = self.create_target_file(self.file.saved_to)

    async def create_description(self):
        "Create a description file"
        logging.debug('[%d] Creating a description file', self.task_id)

        md_content = ''
        if self.file.text_content is not None:
            h2t_handler = html2text.HTML2Text()
            md_content = h2t_handler.handle(self.file.text_content).strip()
            # we could run html.unescape() over to_save, but this could destroy the md file

        if md_content == '':
            logging.debug('[%d] Remove target file because description file would be empty', self.task_id)
            os.remove(self.file.saved_to)
            return

        async with aiofiles.open(self.file.saved_to, 'w+', encoding='utf-8') as md_file:
            await md_file.write(md_content)

    async def create_html_file(self):
        "Create a HTML file"
        logging.debug('[%d] Creating a html file', self.task_id)

        html_content = ''
        if self.file.html_content is not None:
            html_content = self.file.html_content

        if html_content == '':
            logging.debug('[%d] Remove target file because html file would be empty', self.task_id)
            os.remove(self.file.saved_to)
            return

        async with aiofiles.open(self.file.saved_to, 'w+', encoding='utf-8') as html_file:
            await html_file.write(html_content)

    def move_old_file(self) -> bool:
        """
        Try to move the old file to the new location.
        @return: True if successful. Else the file needs to be re-downloaded.
        """

        if self.file.old_file is None:
            return False

        old_path = self.file.old_file.saved_to
        if not os.path.exists(old_path):
            return False

        logging.debug('[%d] Moving old file "%s" to new target location', self.task_id, old_path)
        try:
            # On Windows, the temporary file must be deleted first.
            os.remove(self.file.saved_to)
            shutil.move(old_path, self.file.saved_to)
            return True
        except OSError as e:
            logging.warning('[%d] Moving the old file %s failed unexpectedly!  Error: %s', self.task_id, old_path, e)
        return False

    async def create_data_url_file(self):
        url_to_download = self.file.content_fileurl
        logging.debug('[%d] Creating a Data-URL file', self.task_id)
        PT.remove_file(self.file.saved_to)
        self.set_path(True)
        with urllib.request.urlopen(url_to_download) as response:
            data = response.read()

        async with aiofiles.open(self.file.saved_to, "wb") as target_file:
            await target_file.write(data)

    async def run(self):
        if self.status.state != TaskState.INIT:
            logging.debug('[%d] Task was already started', self.task_id)
            return
        self.status.state = TaskState.STARTED

        success = await self.real_run()

        if success:
            self.set_utime()
            self.file.time_stamp = int(time.time())

    async def real_run(self) -> bool:
        try:
            logging.debug('[%d] Starting Task: %s', self.task_id, self)
            PT.make_dirs(self.destination)

            # If file was modified try rename the old file, before create new one
            if self.file.modified:
                self.rename_old_file()

            # Create an empty destination file
            self.set_path()
            logging.debug('[%d] Starting downloading of: %s', self.task_id, self.file.saved_to)

            # Try to move the old file if it still exists
            if self.file.moved:
                if self.move_old_file():
                    return True

            if self.file.content_type == 'description':
                # Create a description file instead of downloading it
                await self.create_description()

            elif self.file.content_type == 'html':
                # Create a HTML file instead of downloading it
                await self.create_html_file()

            elif self.file.module_modname.startswith('index_mod'):
                await self.external_download_url(add_token=True, delete_if_successful=True, use_cookies=False)

            elif self.file.module_modname.startswith('cookie_mod'):
                await self.external_download_url(add_token=False, delete_if_successful=True, use_cookies=True)

            elif self.file.module_modname.startswith('url') and not self.file.content_fileurl.startswith('data:'):
                # Create a shortcut and maybe downloading it
                await self.create_shortcut()
                if self.opts.download_linked_files and not self.is_filtered_external_domain():
                    await self.external_download_url(add_token=False, delete_if_successful=False, use_cookies=False)

            elif self.file.content_fileurl.startswith('data:'):
                await self.create_data_url_file()

            else:
                url_to_download = self.file.content_fileurl
                logging.debug('[%d] Downloading %s', self.task_id, url_to_download)
                url_to_download = self.add_token_to_url(self.file.content_fileurl)
                await self.download_url(url_to_download, self.file.saved_to)

            logging.debug('[%d] Download finished', self.task_id)
            self.report_success()
            return True
        except Exception as dl_err:
            self.status.error = dl_err

            logging.error('[%d] %r', self.task_id, dl_err)
            logging.error('[%d] Error while trying to download file: %s', self.task_id, dl_err)

            if os.path.isfile(self.file.saved_to):
                file_size = 0
                try:
                    file_size = os.path.getsize(self.file.saved_to)
                except OSError:
                    pass
                logging.debug(
                    '[%d] file size: %d; downloaded: %d',
                    self.task_id,
                    file_size,
                    self.status.bytes_downloaded,
                )

            logging.debug('[%d] Traceback:\n%s', self.task_id, traceback.format_exc())

            # TODO: Do this in the error handlers of download functions
            # TODO: See download_url; remove only if not recoverable
            PT.remove_file(self.file.saved_to)
            self.report_received_bytes(-self.status.bytes_downloaded)
            self.report_failure()

        return False

    def get_cookie_jar(self) -> aiohttp.CookieJar:
        # TODO: Since we currently do not modify the cookieJar we could just use a deep copied instance.
        if self.opts.cookies_text is not None:
            cookie_jar = MoodleDLCookieJar(StringIO(self.opts.cookies_text))
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            return convert_to_aiohttp_cookie_jar(cookie_jar)
        return None

    async def check_range_download_opt(self, url, session):
        try:
            headers = self.RQ_HEADER.copy()
            headers['Range'] = 'bytes=0-4'
            resp = await session.request("GET", url, headers=headers)
            return resp.headers.get('Content-Range') is not None and resp.status == 206
        except Exception as err:
            logging.debug("Failed to check if download can be continued on fail: %s", err)
        return False

    def report_success(self):
        self.status.state = TaskState.FINISHED
        self.callback(DlEvent.FINISHED, self)

    def report_failure(self):
        self.status.state = TaskState.FAILED
        self.callback(DlEvent.FAILED, self)

    def report_received_bytes(self, bytes_received: int):
        self.status.bytes_downloaded += bytes_received
        self.callback(DlEvent.RECEIVED, self, bytes_received=bytes_received)

    def report_content_length(self, content_length: int, save_in_status: bool = True):
        if content_length is not None and content_length != 0:
            if self.file.content_filesize is None or self.file.content_filesize <= 0:
                if save_in_status:
                    self.status.external_total_size = content_length
                self.callback(DlEvent.TOTAL_SIZE, self, content_length=content_length)

    async def download_url(self, dl_url: str, dest_path: str, timeout: int = None):
        total_bytes_received = 0
        done_tries = 0
        can_continue_on_fail = False
        file_obj = None
        headers = self.RQ_HEADER.copy()
        ssl_context = SslHelper.get_ssl_context(
            self.opts.global_opts.skip_cert_verify, self.opts.global_opts.allow_insecure_ssl
        )
        with Timer() as watch:
            async with aiohttp.ClientSession(cookie_jar=self.get_cookie_jar(), raise_for_status=True) as session:
                while done_tries < self.MAX_DL_RETRIES:
                    try:
                        if done_tries > 0:
                            logging.debug(
                                '[%d] Start downloading (Try %d of %d)',
                                self.task_id,
                                done_tries + 1,
                                self.MAX_DL_RETRIES,
                            )

                        if done_tries > 0 and can_continue_on_fail:
                            headers['Range'] = f'bytes={total_bytes_received}-'
                        elif not can_continue_on_fail and 'Range' in headers:
                            del headers['Range']

                        async with session.request(
                            "GET", dl_url, headers=headers, ssl=ssl_context, timeout=timeout
                        ) as resp:
                            content_length = int(resp.headers.get("Content-Length", 0))
                            self.report_content_length(content_length)
                            content_range = resp.headers.get("Content-Range")  # Exp: bytes 200-1000/67589

                            if resp.status not in [200, 206]:
                                logging.debug('[%d] Warning got status %s', self.task_id, resp.status)

                            if done_tries > 0 and can_continue_on_fail and not content_range and resp.status != 206:
                                raise ContentRangeError(
                                    f"[{self.task_id}] Server did not response with requested range data"
                                )

                            file_obj = file_obj or await aiofiles.open(dest_path, "wb")
                            async for chunk in resp.content.iter_chunked(self.CHUNK_SIZE):
                                bytes_received = len(chunk)
                                total_bytes_received += bytes_received
                                self.report_received_bytes(bytes_received)
                                await file_obj.write(chunk)

                        if file_obj is not None and not file_obj.closed:
                            await file_obj.close()

                        if content_length >= 0 and total_bytes_received < content_length:
                            raise ContentTooShortError(
                                f'[{self.task_id}] Download incomplete: Got only {format_bytes(total_bytes_received)}'
                                + f' out of {format_bytes(content_length)} bytes',
                                dest_path,
                            )

                        logging.debug('[%d] Successfully downloaded %s', self.task_id, dest_path)
                        break

                    except (aiohttp.ClientError, OSError, ValueError, ContentRangeError) as err:
                        if done_tries == 0:
                            can_continue_on_fail = await self.check_range_download_opt(dl_url, session)

                        done_tries += 1
                        if (
                            (not can_continue_on_fail and total_bytes_received > 0)
                            or isinstance(err, ContentRangeError)
                            or (done_tries >= self.MAX_DL_RETRIES)
                        ):
                            can_continue_on_fail = False
                            # Clean up failed file because we can not recover
                            if file_obj is not None and not file_obj.closed:
                                await file_obj.close()
                            file_obj = None

                            # TODO: If download can be continued and size > 0,
                            #  remember that the file started downloading, and continue downloading
                            #  on next run instead of deleting it.
                            PT.remove_file(dest_path)
                            self.report_received_bytes(-total_bytes_received)
                            total_bytes_received = 0

                        if isinstance(err, aiohttp.ClientResponseError):
                            if err.status not in [408, 409, 429]:  # pylint: disable=no-member
                                # 408 (timeout) or 409 (conflict) and 429 (too many requests)
                                logging.warning(
                                    '[%d] Download failed with status: %s %s', self.task_id, err.status, err.message
                                )
                                raise err from None

                        if done_tries < self.MAX_DL_RETRIES:
                            logging.debug('[%d] Download error occurred: %s', self.task_id, err)
                            await asyncio.sleep(1)
                            continue

                        # No more tries
                        raise err from None
        logging.debug(
            '[%d] Download of %s finished in %s',
            self.task_id,
            format_bytes(total_bytes_received),
            format_seconds(watch.duration),
        )

    def __str__(self):
        return 'Task (%(task_id)s, %(file)s, %(course)s, %(status)s)' % {
            'task_id': self.task_id,
            'file': self.file,
            'course': self.course,
            'status': self.status,
        }


class ContentRangeError(ConnectionError):
    pass
