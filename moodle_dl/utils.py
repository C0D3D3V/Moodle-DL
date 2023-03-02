import collections
import contextlib
import email.utils
import getpass
import html
import http
import io
import itertools
import logging
import math
import os
import re
import shutil
import ssl
import sys
import time
import unicodedata

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict
from aiohttp.cookiejar import CookieJar

import readchar
import requests
import urllib3

from requests.utils import DEFAULT_CA_BUNDLE_PATH, extract_zipped_paths


def check_verbose() -> bool:
    """Return if the verbose mode is active"""
    return '-v' in sys.argv or '--verbose' in sys.argv


def check_debug() -> bool:
    """Return if the debugger is currently active"""
    return 'pydevd' in sys.modules or (hasattr(sys, 'gettrace') and sys.gettrace() is not None)


def format_seconds(seconds):
    (mins, secs) = divmod(seconds, 60)
    (hours, mins) = divmod(mins, 60)
    if hours > 99:
        return '--:--:--'
    if hours == 0:
        return f'{int(mins):02d}:{int(secs):02d}'
    return f'{int(hours):02d}:{int(mins):02d}:{int(secs):02d}'


def calc_speed(start, now, byte_count):
    dif = now - start
    if byte_count <= 0 or dif < 0.001:  # One millisecond
        return None
    return float(byte_count) / dif


def format_speed(speed):
    if speed is None:
        return f"{'---b/s':10}"
    speed_text = format_bytes(speed) + '/s'
    return f'{speed_text:10}'


async def run_with_final_message(load_function, entry: Dict, message: str, *format_args):
    result = await load_function(entry)
    logging.info(message, *format_args)
    return result


def get_nested(from_dict: Dict, key: str, default=None):
    keys = key.split('.')
    try:
        result = from_dict
        for key in keys:
            result = result[key]
        return result
    except KeyError:
        return default


KNOWN_EXTENSIONS = (
    ['avi', 'flv', 'mkv', 'mov', 'mp4', 'webm', '3g2', '3gp', 'f4v', 'mk3d', 'divx', 'mpg', 'ogv', 'm4v']
    + ['wmv', 'aiff', 'alac', 'flac', 'm4a', 'mka', 'mp3', 'ogg', 'opus', 'wav', 'aac', 'ape', 'asf', 'f4a', 'f4b']
    + ['m4b', 'm4p', 'm4r', 'oga', 'ogx', 'spx', 'vorbis', 'wma', 'weba', 'jpg', 'png', 'webp']
    + ['mhtml', 'srt', 'vtt', 'ass', 'lrc', 'f4f', 'f4m', 'm3u8', 'smil', 'mpd', 'pdf', 'doc', 'docx', 'excl']
    + ['aac', 'abw', 'arc', 'avif', 'avi', 'azw', 'bin', 'bmp', 'bz', 'bz2', 'cda', 'csh']
    + ['css', 'csv', 'doc', 'docx', 'eot', 'epub', 'gz', 'gif', 'htm', 'html', 'ico']
    + ['ics', 'jar', 'jpeg', 'jpg', 'js', 'json', 'jsonld', 'mid', 'midi', 'mjs', 'mp3']
    + ['mp4', 'mpeg', 'mpkg', 'odp', 'ods', 'odt', 'oga', 'ogv', 'ogx', 'opus', 'otf']
    + ['png', 'pdf', 'php', 'ppt', 'pptx', 'rar', 'rtf', 'sh', 'svg', 'tar', 'tif']
    + ['tiff', 'ts', 'ttf', 'txt', 'vsd', 'wav', 'weba', 'webm', 'webp', 'woff', 'woff2']
    + ['xhtml', 'xls', 'xlsx', 'xml', 'xml', 'xul', 'zip', '3gp', '3g2', '7z']
)


def determine_ext(url, default_ext='unknown_file'):
    if url is None or '.' not in url:
        return default_ext
    guess = url.partition('?')[0].rpartition('.')[2]
    if re.match(r'^[A-Za-z0-9]+$', guess):
        return guess
    # Try extract ext from URLs like http://example.com/foo/bar.mp4/?download
    elif guess.rstrip('/') in KNOWN_EXTENSIONS:
        return guess.rstrip('/')
    else:
        return default_ext


def timeconvert(timestr):
    """Convert RFC 2822 defined time string into system timestamp"""
    timestamp = None
    timetuple = email.utils.parsedate_tz(timestr)
    if timetuple is not None:
        timestamp = email.utils.mktime_tz(timetuple)
    return timestamp


def float_or_none(v, scale=1, invscale=1, default=None):
    if v is None:
        return default
    try:
        return float(v) * invscale / scale
    except (ValueError, TypeError):
        return default


def format_decimal_suffix(num, fmt='%d%s', *, factor=1000):
    """Formats numbers with decimal sufixes like K, M, etc"""
    num, factor = float_or_none(num), float(factor)
    if num is None or num < 0:
        return None
    POSSIBLE_SUFFIXES = 'kMGTPEZY'
    exponent = 0 if num == 0 else min(int(math.log(num, factor)), len(POSSIBLE_SUFFIXES))
    suffix = ['', *POSSIBLE_SUFFIXES][exponent]
    if factor == 1024:
        suffix = {'k': 'Ki', '': ''}.get(suffix, f'{suffix}i')
    converted = num / (factor**exponent)
    return fmt % (converted, suffix)


def format_bytes(bytes_to_format):
    return format_decimal_suffix(bytes_to_format, '%.2f%sB', factor=1024) or 'N/A'


# needed for sanitizing filenames in restricted mode
ACCENT_CHARS = dict(
    zip(
        'ÂÃÄÀÁÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŐØŒÙÚÛÜŰÝÞßàáâãäåæçèéêëìíîïðñòóôõöőøœùúûüűýþÿ',
        itertools.chain(
            'AAAAAA',
            ['AE'],
            'CEEEEIIIIDNOOOOOOO',
            ['OE'],
            'UUUUUY',
            ['TH', 'ss'],
            'aaaaaa',
            ['ae'],
            'ceeeeiiiionooooooo',
            ['oe'],
            'uuuuuy',
            ['th'],
            'y',
        ),
    )
)

NO_DEFAULT = object()


def is_path_like(f):
    return isinstance(f, (str, bytes, os.PathLike))


def str_or_none(v, default=None):
    return default if v is None else str(v)


def convert_to_aiohttp_cookie_jar(mozilla_cookie_jar: http.cookiejar.MozillaCookieJar):
    """
    Convert an http.cookiejar.MozillaCookieJar that uses a Netscape HTTP Cookie File to an aiohttp.cookiejar.CookieJar
    Tested with aiohttp v3.8.4
    """
    aiohttp_cookie_jar = CookieJar(unsafe=True)  # unsafe = Allow also cookies for IPs

    # pylint: disable=protected-access
    for cookie_domain, domain_cookies in mozilla_cookie_jar._cookies.items():
        for cookie_path, path_cookies in domain_cookies.items():
            for cookie_name, cookie in path_cookies.items():
                # cookie_name is cookie.name; cookie_path is cookie.path; cookie_domain is cookie.domain
                morsel = http.cookies.Morsel()
                morsel.update(
                    {
                        "expires": cookie.expires,
                        "path": cookie.path,
                        "comment": cookie.comment,
                        "domain": cookie.domain,
                        # "max-age"  : "Max-Age",
                        "secure": cookie.secure,
                        # "httponly": "HttpOnly",
                        "version": cookie.version,
                        # "samesite": "SameSite",
                    }
                )
                # pylint: disable=protected-access
                morsel.set(cookie.name, cookie.value, http.cookies._quote(cookie.value))
                aiohttp_cookie_jar._cookies[(cookie_domain, cookie_path)][cookie_name] = morsel

    return aiohttp_cookie_jar


class MoodleDLCookieJar(http.cookiejar.MozillaCookieJar):
    """
    Taken from yt-dlp: Last update 9. Sep. 2022
    See [1] for cookie file format.

    1. https://curl.haxx.se/docs/http-cookies.html
    """

    _HTTPONLY_PREFIX = '#HttpOnly_'
    _ENTRY_LEN = 7
    _HEADER = '''# Netscape HTTP Cookie File
# This file is generated by moodle-dl.  Do not edit.

'''
    _CookieFileEntry = collections.namedtuple(
        'CookieFileEntry', ('domain_name', 'include_subdomains', 'path', 'https_only', 'expires_at', 'name', 'value')
    )

    def __init__(self, filename=None, *args, **kwargs):
        super().__init__(None, *args, **kwargs)
        if is_path_like(filename):
            filename = os.fspath(filename)
        self.filename = filename

    @staticmethod
    def _true_or_false(cndn):
        return 'TRUE' if cndn else 'FALSE'

    @contextlib.contextmanager
    def open(self, file, *, write=False):
        if is_path_like(file):
            with open(file, 'w' if write else 'r', encoding='utf-8') as f:
                yield f
        else:
            if write:
                file.truncate(0)
            yield file

    def _really_save(self, f, ignore_discard=False, ignore_expires=False):
        now = time.time()
        for cookie in self:
            if not ignore_discard and cookie.discard or not ignore_expires and cookie.is_expired(now):
                continue
            name, value = cookie.name, cookie.value
            if value is None:
                # cookies.txt regards 'Set-Cookie: foo' as a cookie
                # with no name, whereas http.cookiejar regards it as a
                # cookie with no value.
                name, value = '', name
            f.write(
                '%s\n'
                % '\t'.join(
                    (
                        cookie.domain,
                        self._true_or_false(cookie.domain.startswith('.')),
                        cookie.path,
                        self._true_or_false(cookie.secure),
                        str_or_none(cookie.expires, default=''),
                        name,
                        value,
                    )
                )
            )

    def save(self, filename=None, *args, **kwargs):
        """
        Save cookies to a file.
        Code is taken from CPython 3.6
        https://github.com/python/cpython/blob/8d999cbf4adea053be6dbb612b9844635c4dfb8e/Lib/http/cookiejar.py#L2091-L2117
        """

        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(http.cookiejar.MISSING_FILENAME_TEXT)

        # Store session cookies with `expires` set to 0 instead of an empty string
        for cookie in self:
            if cookie.expires is None:
                cookie.expires = 0

        with self.open(filename, write=True) as f:
            f.write(self._HEADER)
            self._really_save(f, *args, **kwargs)

    def load(self, filename=None, ignore_discard=False, ignore_expires=False):
        """Load cookies from a file."""
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(http.cookiejar.MISSING_FILENAME_TEXT)

        def prepare_line(line):
            if line.startswith(self._HTTPONLY_PREFIX):
                line = line[len(self._HTTPONLY_PREFIX) :]
            # comments and empty lines are fine
            if line.startswith('#') or not line.strip():
                return line
            cookie_list = line.split('\t')
            if len(cookie_list) != self._ENTRY_LEN:
                raise http.cookiejar.LoadError('invalid length %d' % len(cookie_list))
            cookie = self._CookieFileEntry(*cookie_list)
            if cookie.expires_at and not cookie.expires_at.isdigit():
                raise http.cookiejar.LoadError('invalid expires at %s' % cookie.expires_at)
            return line

        cf = io.StringIO()
        with self.open(filename) as input_file:
            for line in input_file:
                try:
                    cf.write(prepare_line(line))
                except http.cookiejar.LoadError as cookie_err:
                    if f'{line.strip()} '[0] in '[{"':
                        raise http.cookiejar.LoadError(
                            'Cookies file must be Netscape formatted, not JSON. See  '
                            'https://github.com/C0D3D3V/Moodle-DL/wiki/Use-cookies-when-downloading'
                        )
                    logging.info('WARNING: Skipping cookie file entry due to %s: %r', cookie_err, line)
                    continue
        cf.seek(0)
        self._really_load(cf, filename, ignore_discard, ignore_expires)
        # Session cookies are denoted by either `expires` field set to
        # an empty string or 0. MozillaCookieJar only recognizes the former
        # (see [1]). So we need force the latter to be recognized as session
        # cookies on our own.
        # Session cookies may be important for cookies-based authentication,
        # e.g. usually, when user does not check 'Remember me' check box while
        # logging in on a site, some important cookies are stored as session
        # cookies so that not recognizing them will result in failed login.
        # 1. https://bugs.python.org/issue17164
        for cookie in self:
            # Treat `expires=0` cookies as session cookies
            if cookie.expires == 0:
                cookie.expires = None
                cookie.discard = True


class Timer:
    '''
    Timing Context Manager
    Can be used for future speed comparisons, like this:

    with Timer() as t:
        Do.stuff()
    print(f'Do.stuff() took:\t {t.duration:.3f} \tseconds.')
    '''

    def __init__(self, nanoseconds=False):
        self.start = 0.0
        self.duration = 0.0
        self.nanoseconds = nanoseconds

    def __enter__(self):
        if self.nanoseconds:
            self.start = time.perf_counter_ns()
        else:
            self.start = time.time()
        return self

    def __exit__(self, *args):
        if self.nanoseconds:
            end = time.perf_counter_ns()
            self.duration = (end - self.start) * 10**-9  # 1 nano-sec = 10^-9 sec
        else:
            end = time.time()
            self.duration = end - self.start


PathParts = collections.namedtuple('PathParts', ('dir_name', 'file_name', 'file_extension'))


class PathTools:
    """A set of methods to create correct paths."""

    restricted_filenames = False

    @staticmethod
    def to_valid_name(name: str, is_file: bool, max_length: int = 200) -> str:
        """
        Filtering invalid characters in filenames and paths.

        @param name: The string that will go through the filtering
        @param is_file: If true, it is tried to keep the extension of the file name
        @param max_length: Most filesystems allow a max filename length of 255 chars,
                            we default use a shorter name to allow long extensions
        @return: The filtered string, that can be used as a filename.
        """

        if name is None:
            return None

        # Moodle saves the title of a section in HTML-Format,
        # so we need to unescape the string
        name = html.unescape(name)

        name = name.replace('\n', ' ')
        name = name.replace('\r', ' ')
        name = name.replace('\t', ' ')
        name = name.replace('\xad', '')
        while '  ' in name:
            name = name.replace('  ', ' ')
        name = PathTools.sanitize_filename(name, PathTools.restricted_filenames)
        name = name.strip('. ')
        name = name.strip()
        name = PathTools.truncate_filename(name, is_file, max_length)

        return name

    @staticmethod
    def truncate_filename(name: str, is_file: bool, max_length: int):
        if len(name) > max_length:
            if not is_file:
                name = PathTools.truncate_name(name, max_length)
            else:
                stem, ext = PathTools.get_file_stem_and_ext(name)
                ext_len = len(ext)
                if ext is None or ext_len == 0 or ext_len > 20:
                    # extensions longer then 20 characters are probably no extensions
                    name = PathTools.truncate_name(name, max_length)
                else:
                    stem = PathTools.truncate_name(stem, max_length - ext_len - 1)
                    name = f'{stem}.{ext}'
        return name

    @staticmethod
    def truncate_name(name: str, max_length: int):
        if PathTools.restricted_filenames:
            name = name[: max_length - 3] + '...'
        else:
            name = name[: max_length - 1] + '…'
        return name

    @staticmethod
    def remove_start(s, start):
        return s[len(start) :] if s is not None and s.startswith(start) else s

    @staticmethod
    def sanitize_filename(s, restricted=False, is_id=NO_DEFAULT):
        """Sanitizes a string so it could be used as part of a filename.
        @param restricted   Use a stricter subset of allowed characters
        @param is_id        Whether this is an ID that should be kept unchanged if possible.
                            If unset, yt-dlp's new sanitization rules are in effect
        """
        if s == '':
            return ''

        def replace_insane(char):
            if restricted and char in ACCENT_CHARS:
                return ACCENT_CHARS[char]
            elif not restricted and char == '\n':
                return '\0 '
            elif is_id is NO_DEFAULT and not restricted and char in '"*:<>?|/\\':
                # Replace with their full-width unicode counterparts
                return {'/': '\u29F8', '\\': '\u29f9'}.get(char, chr(ord(char) + 0xFEE0))
            elif char == '?' or ord(char) < 32 or ord(char) == 127:
                return ''
            elif char == '"':
                return '' if restricted else '\''
            elif char == ':':
                return '\0_\0-' if restricted else '\0 \0-'
            elif char in '\\/|*<>':
                return '\0_'
            if restricted and (char in '!&\'()[]{}$;`^,#' or char.isspace() or ord(char) > 127):
                return '\0_'
            return char

        if restricted and is_id is NO_DEFAULT:
            s = unicodedata.normalize('NFKC', s)
        s = re.sub(r'[0-9]+(?::[0-9]+)+', lambda m: m.group(0).replace(':', '_'), s)  # Handle timestamps
        result = ''.join(map(replace_insane, s))
        if is_id is NO_DEFAULT:
            result = re.sub(r'(\0.)(?:(?=\1)..)+', r'\1', result)  # Remove repeated substitute chars
            STRIP_RE = r'(?:\0.|[ _-])*'
            result = re.sub(f'^\0.{STRIP_RE}|{STRIP_RE}\0.$', '', result)  # Remove substitute chars from start/end
        result = result.replace('\0', '') or '_'

        if not is_id:
            while '__' in result:
                result = result.replace('__', '_')
            result = result.strip('_')
            # Common case of "Foreign band name - English song title"
            if restricted and result.startswith('-_'):
                result = result[2:]
            if result.startswith('-'):
                result = '_' + result[len('-') :]
            result = result.lstrip('.')
            if not result:
                result = '_'
        return result

    @staticmethod
    def sanitize_path(path: str):
        """
        @param path: A path to sanitize.
        @return: A path where every part was sanitized using to_valid_name.
        """
        drive_or_unc, _ = os.path.splitdrive(path)
        norm_path = os.path.normpath(PathTools.remove_start(path, drive_or_unc)).split(os.path.sep)
        if drive_or_unc:
            norm_path.pop(0)

        sanitized_path = [
            path_part if path_part in ['.', '..'] else PathTools.to_valid_name(path_part, is_file=False)
            for path_part in norm_path
        ]

        if drive_or_unc:
            sanitized_path.insert(0, drive_or_unc + os.path.sep)
        return os.path.join(*sanitized_path)

    @staticmethod
    def path_of_file_in_module(
        storage_path: str, course_fullname: str, file_section_name: str, file_module_name: str, file_path: str
    ):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_section_name: The name of the section where the file
                                  is located.
        @param file_module_name: The name of the module where the file
                                 is located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = str(
            Path(storage_path)
            / PathTools.to_valid_name(course_fullname, is_file=False)
            / PathTools.to_valid_name(file_section_name, is_file=False)
            / PathTools.to_valid_name(file_module_name, is_file=False)
            / PathTools.sanitize_path(file_path).strip('/')
        )
        return path

    @staticmethod
    def path_of_file(storage_path: str, course_fullname: str, file_section_name: str, file_path: str):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_section_name: The name of the section where the file
                                  is located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = str(
            Path(storage_path)
            / PathTools.to_valid_name(course_fullname, is_file=False)
            / PathTools.to_valid_name(file_section_name, is_file=False)
            / PathTools.sanitize_path(file_path).strip('/')
        )
        return path

    @staticmethod
    def flat_path_of_file(storage_path: str, course_fullname: str, file_path: str):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = str(
            Path(storage_path)
            / PathTools.to_valid_name(course_fullname, is_file=False)
            / PathTools.sanitize_path(file_path).strip('/')
        )
        return path

    @staticmethod
    def remove_file(file_path: str):
        if os.path.exists(file_path):
            os.unlink(file_path)

    @staticmethod
    def get_abs_path(path: str):
        return str(Path(path).resolve())

    @staticmethod
    def make_path(path: str, *filenames: str):
        result_path = Path(path)
        for filename in filenames:
            result_path = result_path / filename
        return str(result_path)

    @staticmethod
    def make_base_dir(path_to_file: str):
        Path(path_to_file).parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def make_dirs(path_to_dir: str):
        Path(path_to_dir).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_user_config_directory():
        """Returns a platform-specific root directory for user config settings."""
        # On Windows, prefer %LOCALAPPDATA%, then %APPDATA%, since we can expect the
        # AppData directories to be ACLed to be visible only to the user and admin
        # users (https://stackoverflow.com/a/7617601/1179226). If neither is set,
        # return None instead of falling back to something that may be world-readable.
        if os.name == "nt":
            appdata = os.getenv("LOCALAPPDATA")
            if appdata:
                return appdata
            appdata = os.getenv("APPDATA")
            if appdata:
                return appdata
            return None
        # On non-windows, use XDG_CONFIG_HOME if set, else default to ~/.config.
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            return xdg_config_home
        return os.path.join(os.path.expanduser("~"), ".config")

    @staticmethod
    def get_user_data_directory():
        """Returns a platform-specific root directory for user application data."""
        if os.name == "nt":
            appdata = os.getenv("LOCALAPPDATA")
            if appdata:
                return appdata
            appdata = os.getenv("APPDATA")
            if appdata:
                return appdata
            return None
        # On non-windows, use XDG_DATA_HOME if set, else default to ~/.config.
        xdg_config_home = os.getenv("XDG_DATA_HOME")
        if xdg_config_home:
            return xdg_config_home
        return os.path.join(os.path.expanduser("~"), ".local/share")

    @staticmethod
    def get_project_data_directory():
        """
        Returns an Path object to the project config directory
        """
        data_dir = Path(PathTools.get_user_data_directory()) / "moodle-dl"
        if not data_dir.is_dir():
            data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir)

    @staticmethod
    def get_project_config_directory():
        """
        Returns an Path object to the project config directory
        """
        config_dir = Path(PathTools.get_user_config_directory()) / "moodle-dl"
        if not config_dir.is_dir():
            config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir)

    @staticmethod
    def get_unused_filename(destination: str, filename: str, file_extension: str, start_clear=True):
        count = 0
        if start_clear:
            new_file_path = str(Path(destination) / f'{filename}.{file_extension}')
        else:
            new_file_path = str(Path(destination) / f'{filename}_{count:02d}.{file_extension}')
        while os.path.exists(new_file_path):
            count += 1
            new_file_path = str(Path(destination) / f'{filename}_{count:02d}.{file_extension}')

        return new_file_path

    @staticmethod
    def get_path_parts(file_path: str) -> PathParts:
        destination = os.path.dirname(file_path)
        filename, file_extension = os.path.splitext(os.path.basename(file_path))
        if file_extension.startswith('.'):
            file_extension = file_extension[1:]
        return PathParts(destination, filename, file_extension)

    @classmethod
    def get_unused_file_path(cls, file_path: str, start_clear=True):
        destination, filename, file_extension = cls.get_path_parts(file_path)
        return cls.get_unused_filename(destination, filename, file_extension, start_clear)

    @classmethod
    def touch_file(cls, file_path: str):
        open(file_path, 'a', encoding='utf-8').close()

    @staticmethod
    def get_file_exts(filename: str) -> (str, str):
        file_splits = filename.rsplit('.', 2)
        if len(file_splits) == 2:
            return None, file_splits[-1].lower()
        if len(file_splits) == 3:
            return file_splits[-2].lower(), file_splits[-1].lower()
        return None, None

    @staticmethod
    def get_file_ext(filename: str) -> str:
        file_splits = filename.rsplit('.', 1)
        if len(file_splits) == 2:
            return file_splits[-1].lower()
        return None

    @staticmethod
    def get_file_stem_and_ext(filename: str) -> (str, str):
        file_splits = filename.rsplit('.', 1)
        if len(file_splits) == 2:
            return file_splits[0], file_splits[1]
        return file_splits[0], None

    @staticmethod
    def get_cookies_path(storage_path: str) -> str:
        return str(Path(storage_path) / 'Cookies.txt')


class SslHelper:
    warned_about_certifi = False

    @classmethod
    def load_default_certs(cls, ssl_context: ssl.SSLContext):
        cert_loc = extract_zipped_paths(DEFAULT_CA_BUNDLE_PATH)

        if not cert_loc or not os.path.exists(cert_loc):
            if not cls.warned_about_certifi:
                Log.warning(f"Certifi could not find a suitable TLS CA certificate bundle, invalid path: {cert_loc}")
                cls.warned_about_certifi = True
            ssl_context.load_default_certs()
        else:
            if not os.path.isdir(cert_loc):
                ssl_context.load_verify_locations(cafile=cert_loc)
            else:
                ssl_context.load_verify_locations(capath=cert_loc)

    @classmethod
    @lru_cache(maxsize=4)
    def get_ssl_context(cls, skip_cert_verify: bool, allow_insecure_ssl: bool):
        if not skip_cert_verify:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            cls.load_default_certs(ssl_context)
        else:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.options |= ssl.OP_NO_SSLv2
            ssl_context.options |= ssl.OP_NO_SSLv3
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            try:
                ssl_context.options |= ssl.OP_NO_COMPRESSION
            except AttributeError as attr_err:
                Log.warning(
                    f"{attr_err!s}: The Python interpreter is compiled "
                    "against OpenSSL < 1.0.0. Ref: "
                    "https://docs.python.org/3/library/ssl.html"
                    "#ssl.OP_NO_COMPRESSION",
                )
            ssl_context.load_default_certs()

        if allow_insecure_ssl:
            # This allows connections to legacy insecure servers
            # https://www.openssl.org/docs/manmaster/man3/SSL_CTX_set_options.html#SECURE-RENEGOTIATION
            # Be warned the insecure renegotiation allows an attack, see:
            # https://nvd.nist.gov/vuln/detail/CVE-2009-3555
            ssl_context.options |= 0x4  # set ssl.OP_LEGACY_SERVER_CONNECT bit

        return ssl_context

    class CustomHttpAdapter(requests.adapters.HTTPAdapter):
        '''
        Transport adapter that allows us to use custom ssl_context.
        See https://stackoverflow.com/a/71646353 for more details.
        '''

        def __init__(self, ssl_context=None, **kwargs):
            self.ssl_context = ssl_context
            super().__init__(**kwargs)

        def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
            self.poolmanager = urllib3.poolmanager.PoolManager(
                num_pools=connections, maxsize=maxsize, block=block, ssl_context=self.ssl_context, **pool_kwargs
            )

    @classmethod
    def custom_requests_session(cls, skip_cert_verify: bool, allow_insecure_ssl: bool):
        """
        Return a new requests session with custom SSL context
        """
        session = requests.Session()
        ssl_context = cls.get_ssl_context(skip_cert_verify, allow_insecure_ssl)
        session.mount('https://', cls.CustomHttpAdapter(ssl_context))
        return session


class ProcessLock:
    """
    A very simple lock mechanism to prevent multiple downloader being started for the same Moodle.

    The functions are not resistant to high frequency calls.
    Raise conditions will occur!
    """

    class LockError(Exception):
        """An Exception which gets thrown if a Downloader is already running."""

        pass

    @staticmethod
    def lock(dir_path: str):
        """
        Test if a lock is already set in a directory, if not it creates the lock.
        """
        path = Path(dir_path) / 'running.lock'
        if Path(path).exists():
            raise ProcessLock.LockError(
                f'A downloader is already running. Delete {str(path)} if you think this is wrong.'
            )
        Path(path).touch()

    @staticmethod
    def unlock(dir_path: str):
        """Remove a lock in a directory."""
        path = Path(dir_path) / 'running.lock'
        try:
            Path(path).unlink()
        except OSError:
            pass


RESET_SEQ = '\033[0m'
COLOR_SEQ = '\033[1;%dm'

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)


class Log:
    """
    Logs a given string to output with colors
    :param logString: the string that should be logged

    The string functions returns the strings that would be logged.

    The idea is to use this Log class only for the CLI configuration wizard,
    and for all other logging we use the normal python logging module
    """

    @staticmethod
    def info_str(logString: str):
        return COLOR_SEQ % WHITE + logString + RESET_SEQ

    @staticmethod
    def success_str(logString: str):
        return COLOR_SEQ % GREEN + logString + RESET_SEQ

    @staticmethod
    def green_str(logString: str):
        return COLOR_SEQ % GREEN + logString + RESET_SEQ

    @staticmethod
    def warning_str(logString: str):
        return COLOR_SEQ % YELLOW + logString + RESET_SEQ

    @staticmethod
    def yellow_str(logString: str):
        return COLOR_SEQ % YELLOW + logString + RESET_SEQ

    @staticmethod
    def error_str(logString: str):
        return COLOR_SEQ % RED + logString + RESET_SEQ

    @staticmethod
    def debug_str(logString: str):
        return COLOR_SEQ % CYAN + logString + RESET_SEQ

    @staticmethod
    def cyan_str(logString: str):
        return COLOR_SEQ % CYAN + logString + RESET_SEQ

    @staticmethod
    def blue_str(logString: str):
        return COLOR_SEQ % BLUE + logString + RESET_SEQ

    @staticmethod
    def magenta_str(logString: str):
        return COLOR_SEQ % MAGENTA + logString + RESET_SEQ

    @staticmethod
    def info(logString: str):
        print(Log.info_str(logString))

    @staticmethod
    def success(logString: str):
        print(Log.success_str(logString))

    @staticmethod
    def warning(logString: str):
        print(Log.warning_str(logString))

    @staticmethod
    def yellow(logString: str):
        print(Log.yellow_str(logString))

    @staticmethod
    def error(logString: str):
        print(Log.error_str(logString))

    @staticmethod
    def debug(logString: str):
        print(Log.debug_str(logString))

    @staticmethod
    def blue(logString: str):
        print(Log.blue_str(logString))

    @staticmethod
    def magenta(logString: str):
        print(Log.magenta_str(logString))

    @staticmethod
    def cyan(logString: str):
        print(Log.cyan_str(logString))


class Cutie:
    """
    Command-line User Tools for simpler Input

    Source: https://github.com/Kamik423/cutie/blob/master/cutie.py

    Authors: Hans and Kamik423
    License: MIT (https://github.com/Kamik423/cutie/blob/master/license.md)
    """

    class DefaultKeys:
        """List of default keybindings.
        Attributes:
            interrupt(List[str]): Keys that cause a keyboard interrupt.
            select(List[str]): Keys that trigger list element selection.
            select_all(List[str]): Keys that trigger selection of all list elements.
            confirm(List[str]): Keys that trigger list confirmation.
            delete(List[str]): Keys that trigger character deletion.
            down(List[str]): Keys that select the element below.
            up(List[str]): Keys that select the element above.
        """

        interrupt: List[str] = [readchar.key.CTRL_C, readchar.key.CTRL_D]
        select: List[str] = [readchar.key.SPACE]
        select_all: List[str] = [readchar.key.CTRL_A]
        confirm: List[str] = [readchar.key.ENTER, readchar.key.CR, readchar.key.LF]
        delete: List[str] = [readchar.key.BACKSPACE]
        down: List[str] = [readchar.key.DOWN, 'j']
        up: List[str] = [readchar.key.UP, 'k']
        tab: List[str] = ['\t']

    @staticmethod
    def get_number(
        prompt: str, min_value: Optional[float] = None, max_value: Optional[float] = None, allow_float: bool = True
    ) -> float:
        """Get a number from user input.
        If an invalid number is entered the user will be prompted again.
        Args:
            prompt (str): The prompt asking the user to input.
            min_value (float, optional): The [inclusive] minimum value.
            max_value (float, optional): The [inclusive] maximum value.
            allow_float (bool, optional): Allow floats or force integers.
        Returns:
            float: The number input by the user.
        """
        return_value: Optional[float] = None
        while return_value is None:
            input_value = input(prompt + ' ')
            try:
                return_value = float(input_value)
            except ValueError:
                print('Not a valid number.\033[K\033[1A\r\033[K', end='')
            if not allow_float and return_value is not None:
                if return_value != int(return_value):
                    print('Has to be an integer.\033[K\033[1A\r\033[K', end='')
                    return_value = None
            if min_value is not None and return_value is not None:
                if return_value < min_value:
                    print(f'Has to be at least {min_value}.\033[K\033[1A\r\033[K', end='')
                    return_value = None
            if max_value is not None and return_value is not None:
                if return_value > max_value:
                    print(f'Has to be at most {max_value}.\033[1A\r\033[K', end='')
                    return_value = None
            if return_value is not None:
                break
        print('\033[K', end='')
        if allow_float:
            return return_value
        return int(return_value)

    @staticmethod
    def secure_input(prompt: str) -> str:
        """Get secure input without showing it in the command line.
        Args:
            prompt (str): The prompt asking the user to input.
        Returns:
            str: The secure input.
        """
        return getpass.getpass(prompt + ' ')

    @staticmethod
    def select(
        options: List[str],
        caption_indices: Optional[List[int]] = None,
        deselected_prefix: str = '\033[1m[ ]\033[0m ',
        selected_prefix: str = '\033[1m[\033[32;1mx\033[0;1m]\033[0m ',
        caption_prefix: str = '',
        selected_index: int = 0,
        confirm_on_select: bool = True,
        reserved_lines: int = 3,
    ) -> int:
        """Select an option from a list.
        Args:
            options (List[str]): The options to select from.
            caption_indices (List[int], optional): Non-selectable indices.
            deselected_prefix (str, optional): Prefix for deselected option ([ ]).
            selected_prefix (str, optional): Prefix for selected option ([x]).
            caption_prefix (str, optional): Prefix for captions ().
            selected_index (int, optional): The index to be selected at first.
            confirm_on_select (bool, optional): Select keys also confirm.
            reserved_lines (int, optional): How many lines of the terminal are
                reserved and should not be used.
        Returns:
            int: The index that has been selected.
        """
        if caption_indices is None:
            caption_indices = []

        max_index = len(options)
        max_lines = len(options) + 1  # Last line is for empty line

        # Lines that were output in the previous interation
        lines_printed = 0
        # By how many entries is the list shifted
        shift = 0

        while True:
            print(f'\033[{lines_printed}A')

            console_lines = shutil.get_terminal_size().lines
            # Extra empty line for correct terminal behavior
            view_hight = max(0, min(console_lines - reserved_lines, max_lines))
            # View consists of
            # (top-indicator)
            # entries
            # (bottom-indicator)
            # empty line

            #  Darstellbaren Einträge =  view_hight - top-indicator
            if shift > (max_lines - 1) - (view_hight - 2):
                shift = (max_lines - 1) - (view_hight - 2)

            # Darstellbaren Einträge normal =  view_hight - top-indicator - bottom-indicator - empty line
            data_bottom = shift + (view_hight - 3)
            if shift == 0:
                # we do not need to print "x more lines above...", so we have one more entry line
                data_bottom += 1
            else:
                print(f'\033[K{shift} more lines above...')

            if data_bottom + 1 >= len(options):
                data_bottom = len(options)

            for i in range(shift, data_bottom):
                option = options[i]
                console_columns = shutil.get_terminal_size().columns - 5
                printable_option = option.expandtabs().replace('\n', ' ').replace('\r', ' ')
                if len(printable_option) > console_columns:
                    printable_option = printable_option[: (console_columns - 2)] + '..'

                if i not in caption_indices:
                    print(f'\033[K{selected_prefix if i == selected_index else deselected_prefix}{printable_option}')
                elif i in caption_indices:
                    print(f'\033[K{caption_prefix}{printable_option}')

            if data_bottom != len(options):
                print(f'{len(options) - data_bottom} more lines below...\033[K')

            lines_printed = view_hight

            keypress = readchar.readkey()
            if keypress in Cutie.DefaultKeys.up:
                new_index = selected_index
                while new_index > 0:
                    new_index -= 1
                    if new_index not in caption_indices:
                        selected_index = new_index
                        if selected_index < shift:
                            if shift == 2:
                                shift = 0
                            else:
                                shift = selected_index
                        break
            elif keypress in Cutie.DefaultKeys.down:
                new_index = selected_index
                while new_index < max_index - 1:
                    new_index += 1
                    if new_index not in caption_indices:
                        selected_index = new_index
                        if selected_index >= data_bottom and data_bottom != max_index:
                            shift = selected_index - (view_hight - 4)
                        break
            elif keypress in Cutie.DefaultKeys.confirm or confirm_on_select and keypress in Cutie.DefaultKeys.select:
                break
            elif keypress in Cutie.DefaultKeys.interrupt:
                raise KeyboardInterrupt
        return selected_index

    @staticmethod
    def select_multiple(
        options: List[str],
        caption_indices: Optional[List[int]] = None,
        deselected_unticked_prefix: str = '\033[1m( )\033[0m ',
        deselected_ticked_prefix: str = '\033[1m(\033[32mx\033[0;1m)\033[0m ',
        selected_unticked_prefix: str = '\033[32;1m{ }\033[0m ',
        selected_ticked_prefix: str = '\033[32;1m{x}\033[0m ',
        caption_prefix: str = '',
        ticked_indices: Optional[List[int]] = None,
        cursor_index: int = 0,
        minimal_count: int = 0,
        maximal_count: Optional[int] = None,
        hide_confirm: bool = False,
        deselected_confirm_label: str = '\033[1m(( confirm ))\033[0m',
        selected_confirm_label: str = '\033[1;32m{{ confirm }}\033[0m',
        reserved_lines: int = 3,
    ) -> List[int]:
        """Select multiple options from a list.
        Args:
            options (List[str]): The options to select from.
            caption_indices (List[int], optional): Non-selectable indices.
            deselected_unticked_prefix (str, optional): Prefix for lines that are
                not selected and not ticked (( )).
            deselected_ticked_prefix (str, optional): Prefix for lines that are
                not selected but ticked ((x)).
            selected_unticked_prefix (str, optional): Prefix for lines that are
                selected but not ticked ({ }).
            selected_ticked_prefix (str, optional): Prefix for lines that are
                selected and ticked ({x}).
            caption_prefix (str, optional): Prefix for captions ().
            ticked_indices (List[int], optional): Indices that are
                ticked initially.
            cursor_index (int, optional): The index the cursor starts at.
            minimal_count (int, optional): The minimal amount of lines
                that have to be ticked.
            maximal_count (int, optional): The maximal amount of lines
                that have to be ticked.
            hide_confirm (bool, optional): Hide the confirm button.
                This causes <ENTER> to confirm the entire selection and not just
                tick the line.
            deselected_confirm_label (str, optional): The confirm label
                if not selected ((( confirm ))).
            selected_confirm_label (str, optional): The confirm label
                if selected ({{ confirm }}).
            reserved_lines (int, optional): How many lines of the terminal are
                reserved and should not be used.
        Returns:
            List[int]: The indices that have been selected
        """
        if caption_indices is None:
            caption_indices = []
        if ticked_indices is None:
            ticked_indices = []
        max_index = len(options) - (1 if hide_confirm else 0)
        max_lines = len(options) + 2  # Last two line are for confirm / error / bottom-indicator + empty line
        error_message = ''

        # Lines that were output in the previous interation
        lines_printed = 0
        # By how many entries is the list shifted
        shift = 0

        while True:
            print(f'\033[{lines_printed}A')

            console_lines = shutil.get_terminal_size().lines
            # Extra empty line for correct terminal behavior
            view_hight = max(0, min(console_lines - reserved_lines, max_lines))
            # View consists of
            # (top-indicator)
            # entries
            # (bottom-indicator / error / confirm)
            # empty line

            #  Darstellbaren Einträge =  view_hight - bottom-indicator/confirm/error - top-indicator
            if shift > (max_lines - 1) - (view_hight - 2):
                shift = (max_lines - 1) - (view_hight - 2)

            # Darstellbaren Einträge normal =  view_hight - top-indicator - bottom-indicator/confirm/error - empty line
            data_bottom = shift + (view_hight - 3)
            if shift == 0:
                # we do not need to print "x more lines above...", so we have one more entry line
                data_bottom += 1
            else:
                print(f'\033[K{shift} more lines above...')

            if data_bottom > len(options):
                data_bottom = len(options)

            for i in range(shift, data_bottom):
                option = options[i]
                console_columns = shutil.get_terminal_size().columns - 5
                printable_option = option.expandtabs().replace('\n', ' ').replace('\r', ' ')
                if len(printable_option) > console_columns:
                    printable_option = printable_option[: (console_columns - 2)] + '..'

                prefix = ''
                if i in caption_indices:
                    prefix = caption_prefix
                elif i == cursor_index:
                    if i in ticked_indices:
                        prefix = selected_ticked_prefix
                    else:
                        prefix = selected_unticked_prefix
                else:
                    if i in ticked_indices:
                        prefix = deselected_ticked_prefix
                    else:
                        prefix = deselected_unticked_prefix
                print(f'\033[K{prefix}{printable_option}')

            if data_bottom == len(options):
                # we do not need to print "x more lines below...", instead we print the confirm label or an error
                if hide_confirm:
                    print(f'{error_message}\033[K')
                else:
                    if cursor_index == max_index:
                        print(f'{selected_confirm_label} {error_message}\033[K')
                    else:
                        print(f'{deselected_confirm_label} {error_message}\033[K')
            else:
                print(f'{len(options) - data_bottom} more lines below... {error_message}\033[K')

            lines_printed = view_hight

            error_message = ''
            keypress = readchar.readkey()
            if keypress in Cutie.DefaultKeys.up:
                new_index = cursor_index
                while new_index > 0:
                    new_index -= 1
                    if new_index not in caption_indices:
                        cursor_index = new_index
                        if cursor_index < shift:
                            if shift == 2:
                                shift = 0
                            else:
                                shift = cursor_index
                        break
            elif keypress in Cutie.DefaultKeys.down:
                new_index = cursor_index
                while new_index + 1 <= max_index:
                    new_index += 1
                    if new_index not in caption_indices:
                        cursor_index = new_index
                        if cursor_index >= data_bottom and data_bottom != len(options):
                            shift = cursor_index - (view_hight - 4)
                        break
            elif keypress in Cutie.DefaultKeys.select:
                if cursor_index in ticked_indices:
                    if len(ticked_indices) - 1 >= minimal_count:
                        ticked_indices.remove(cursor_index)
                elif maximal_count is not None:
                    if len(ticked_indices) + 1 <= maximal_count:
                        ticked_indices.append(cursor_index)
                else:
                    ticked_indices.append(cursor_index)
            elif keypress in Cutie.DefaultKeys.confirm:
                if minimal_count > len(ticked_indices):
                    error_message = f'Must select at least {minimal_count} options'
                elif maximal_count is not None and maximal_count < len(ticked_indices):
                    error_message = f'Must select at most {maximal_count} options'
                else:
                    break
            elif keypress in Cutie.DefaultKeys.select_all:
                for i in range(0, len(options)):
                    if i not in ticked_indices:
                        ticked_indices.append(i)
            elif keypress in Cutie.DefaultKeys.interrupt:
                raise KeyboardInterrupt
        print('\033[1A\033[K', end='', flush=True)
        return ticked_indices

    @staticmethod
    def prompt_yes_or_no(
        question: str,
        yes_text: str = 'Yes',
        no_text: str = 'No',
        has_to_match_case: bool = False,
        enter_empty_confirms: bool = True,
        default_is_yes: bool = False,
        deselected_prefix: str = '  ',
        selected_prefix: str = '\033[31m>\033[0m ',
        char_prompt: bool = True,
    ) -> Optional[bool]:
        """Prompt the user to input yes or no.
        Args:
            question (str): The prompt asking the user to input.
            yes_text (str, optional): The text corresponding to 'yes'.
            no_text (str, optional): The text corresponding to 'no'.
            has_to_match_case (bool, optional): Does the case have to match.
            enter_empty_confirms (bool, optional): Does enter on empty string work.
            default_is_yes (bool, optional): Is yes selected by default (no).
            deselected_prefix (str, optional): Prefix if something is deselected.
            selected_prefix (str, optional): Prefix if something is selected (> )
            char_prompt (bool, optional): Add a [Y/N] to the prompt.
        Returns:
            Optional[bool]: The bool what has been selected.
        """
        is_yes = default_is_yes
        is_selected = enter_empty_confirms
        current_message = ''
        if char_prompt:
            if default_is_yes:
                yn_prompt = f' ({yes_text[0]}/{no_text[0].lower()}) '
            else:
                yn_prompt = f' ({yes_text[0].lower()}/{no_text[0]}) '
        else:
            yn_prompt = ': '
        print()
        while True:
            yes = is_yes and is_selected
            no = not is_yes and is_selected
            print('\033[K' f'{selected_prefix if yes else deselected_prefix}{yes_text}')
            print('\033[K' f'{selected_prefix if no else deselected_prefix}{no_text}')
            print('\033[3A\r\033[K' f'{question}{yn_prompt}{current_message}', end='', flush=True)
            keypress = readchar.readkey()
            if keypress in Cutie.DefaultKeys.down or keypress in Cutie.DefaultKeys.up:
                is_yes = not is_yes
                is_selected = True
                current_message = yes_text if is_yes else no_text
            elif keypress in Cutie.DefaultKeys.interrupt:
                raise KeyboardInterrupt
            elif keypress in Cutie.DefaultKeys.confirm:
                if is_selected:
                    break
            elif keypress is not None:
                if keypress in Cutie.DefaultKeys.tab:
                    pass
                elif keypress in Cutie.DefaultKeys.delete:
                    if current_message:
                        current_message = current_message[:-1]
                else:
                    current_message += keypress

                match_yes = yes_text
                match_no = no_text
                match_text = current_message
                if not has_to_match_case:
                    match_yes = match_yes.upper()
                    match_no = match_no.upper()
                    match_text = match_text.upper()
                if match_no.startswith(match_text):
                    is_selected = True
                    is_yes = False
                elif match_yes.startswith(match_text):
                    is_selected = True
                    is_yes = True
                else:
                    is_selected = False

                if keypress in Cutie.DefaultKeys.tab and is_selected:
                    current_message = yes_text if is_yes else no_text
            print()
        print('\033[K\n\033[K\n\033[K\n\033[3A')
        return is_selected and is_yes
