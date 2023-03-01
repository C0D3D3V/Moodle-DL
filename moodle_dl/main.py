import argparse
import asyncio
import logging
import os
import sys
import traceback

from logging.handlers import RotatingFileHandler
from shutil import which

import colorlog
import requests  # noqa: F401 pylint: disable=unused-import
import sentry_sdk
import urllib3

try:
    # In unix readline needs to be loaded so that arrow keys work in input
    import readline  # pylint: disable=unused-import # noqa: F401
except ImportError:
    pass

from colorama import just_fix_windows_console

from moodle_dl.cli import ConfigWizard, DatabaseManager, MoodleWizard, NotificationsWizard, init_config
from moodle_dl.config import ConfigHelper
from moodle_dl.database import StateRecorder
from moodle_dl.downloader.download_service import DownloadService
from moodle_dl.downloader.fake_download_service import FakeDownloadService
from moodle_dl.moodle.moodle_service import MoodleService
from moodle_dl.notifications import get_all_notify_services
from moodle_dl.types import MoodleDlOpts
from moodle_dl.utils import ProcessLock, check_debug, PathTools as PT
from moodle_dl.version import __version__


class ReRaiseOnError(logging.StreamHandler):
    "A logging-handler class which allows the exception-catcher of i.e. PyCharm to intervene"

    def emit(self, record):
        if hasattr(record, 'exception'):
            raise record.exception


def choose_task(config: ConfigHelper, opts: MoodleDlOpts):
    if opts.add_all_visible_courses:
        ConfigWizard(config, opts).interactively_add_all_visible_courses()
    elif opts.change_notification_mail:
        NotificationsWizard(config, opts).interactively_configure_mail()
    elif opts.change_notification_telegram:
        NotificationsWizard(config, opts).interactively_configure_telegram()
    elif opts.change_notification_xmpp:
        NotificationsWizard(config, opts).interactively_configure_xmpp()
    elif opts.config:
        ConfigWizard(config, opts).interactively_acquire_config()
    elif opts.delete_old_files:
        DatabaseManager(config, opts).delete_old_files()
    elif opts.manage_database:
        DatabaseManager(config, opts).interactively_manage_database()
    elif opts.new_token:
        MoodleWizard(config, opts).interactively_acquire_token(use_stored_url=True)
    else:
        run_main(config, opts)


def connect_sentry(config: ConfigHelper) -> bool:
    "Return True if connected"
    try:
        sentry_dsn = config.get_property('sentry_dsn')
        if sentry_dsn:
            sentry_sdk.init(sentry_dsn)
            return True
    except (ValueError, sentry_sdk.utils.BadDsn, sentry_sdk.utils.ServerlessTimeoutWarning):
        pass
    return False


def run_main(config: ConfigHelper, opts: MoodleDlOpts):
    sentry_connected = connect_sentry(config)
    notify_services = get_all_notify_services(config)

    # TODO: Change this
    PT.restricted_filenames = config.get_restricted_filenames()

    try:
        moodle = MoodleService(config, opts)

        logging.debug('Checking for changes for the configured Moodle-Account....')
        database = StateRecorder(opts)
        changed_courses = asyncio.run(moodle.fetch_state(database))

        if opts.log_responses:
            logging.info("All JSON-responses from Moodle have been written to the responses.log file.")
            return

        logging.debug('Start downloading changed files...')

        if opts.without_downloading_files:
            downloader = FakeDownloadService(changed_courses, config, opts, database)
        else:
            downloader = DownloadService(changed_courses, config, opts, database)
        downloader.run()
        failed_downloads = downloader.get_failed_tasks()

        changed_courses_to_notify = database.changes_to_notify()

        if len(changed_courses_to_notify) > 0:
            for service in notify_services:
                service.notify_about_changes_in_moodle(changed_courses_to_notify)

            database.notified(changed_courses_to_notify)

        else:
            logging.info('No changes found for the configured Moodle-Account.')

        if len(failed_downloads) > 0:
            for service in notify_services:
                service.notify_about_failed_downloads(failed_downloads)

    except BaseException as base_err:
        if sentry_connected:
            sentry_sdk.capture_exception(base_err)

        short_error = str(base_err)
        if not short_error or short_error.isspace():
            short_error = traceback.format_exc(limit=1)

        for service in notify_services:
            service.notify_about_error(short_error)

        raise base_err


def setup_logger(opts: MoodleDlOpts):
    file_log_handler = RotatingFileHandler(
        PT.make_path(opts.path, 'MoodleDL.log'),
        mode='a',
        maxBytes=1 * 1024 * 1024,
        backupCount=2,
        encoding='utf-8',
        delay=0,
    )
    file_log_handler.setFormatter(
        logging.Formatter('%(asctime)s  %(levelname)s  {%(module)s}  %(message)s', '%Y-%m-%d %H:%M:%S')
    )
    stdout_log_handler = colorlog.StreamHandler()
    if sys.stdout.isatty() and not opts.verbose:
        stdout_log_handler.setFormatter(colorlog.ColoredFormatter('%(log_color)s%(asctime)s %(message)s', '%H:%M:%S'))
    else:
        stdout_log_handler.setFormatter(
            colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s  %(levelname)s  {%(module)s}  %(message)s', '%Y-%m-%d %H:%M:%S'
            )
        )

    app_log = logging.getLogger()
    if opts.quiet:
        file_log_handler.setLevel(logging.ERROR)
        app_log.setLevel(logging.ERROR)
        stdout_log_handler.setLevel(logging.ERROR)
    elif opts.verbose:
        file_log_handler.setLevel(logging.DEBUG)
        app_log.setLevel(logging.DEBUG)
        stdout_log_handler.setLevel(logging.DEBUG)
    else:
        file_log_handler.setLevel(logging.INFO)
        app_log.setLevel(logging.INFO)
        stdout_log_handler.setLevel(logging.INFO)

    app_log.addHandler(stdout_log_handler)
    if opts.log_to_file:
        app_log.addHandler(file_log_handler)

    if opts.verbose:
        logging.debug('moodle-dl version: %s', __version__)
        logging.debug('python version: %s', ".".join(map(str, sys.version_info[:3])))
        ffmpeg_available = which('ffmpeg') is not None
        logging.debug('Is ffmpeg available: %s', ffmpeg_available)

    if check_debug():
        logging.info('Debug-Mode detected. Errors will be re-risen.')
        app_log.addHandler(ReRaiseOnError())

    if not opts.verbose:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        urllib3.disable_warnings()


def _dir_path(path):
    if os.path.isdir(path):
        return path
    raise argparse.ArgumentTypeError(f'"{str(path)}" is not a valid path. Make sure the directory exists.')


def win_max_path_length_workaround(path):
    # Working around MAX_PATH limitation on Windows (see
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx)
    if os.name == 'nt':
        abs_file_path = PT.get_abs_path(path)
        path = '\\\\?\\' + abs_file_path
        logging.debug("Using windows max path length workaround")
    else:
        logging.info("You are not on Windows, you don't need to use this workaround")
    return path


def get_parser():
    """
    Creates a new argument parser.
    """
    parser = argparse.ArgumentParser(
        description=('Moodle-DL helps you download all the course files from your Moodle account.')
    )
    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '-i',
        '--init',
        dest='init',
        default=False,
        action='store_true',
        help=(
            'Create an initial configuration. A CLI configuration wizard will lead you through'
            + ' the initial configuration.'
        ),
    )

    group.add_argument(
        '-c',
        '--config',
        dest='config',
        default=False,
        action='store_true',
        help=(
            'Start the configuration utility. It allows you to make almost all available moodle-dl settings'
            + ' conveniently via the CLI configuration wizard.'
        ),
    )

    group.add_argument(
        '-nt',
        '--new-token',
        dest='new_token',
        default=False,
        action='store_true',
        help=('Obtain a new login token. Use it if the saved token gets rejected by your Moodle.'),
    )

    group.add_argument(
        '-cm',
        '--change-notification-mail',
        dest='change_notification_mail',
        default=False,
        action='store_true',
        help=('Activate / deactivate / change the settings for receiving notifications via e-mail.'),
    )

    group.add_argument(
        '-ct',
        '--change-notification-telegram',
        dest='change_notification_telegram',
        default=False,
        action='store_true',
        help=('Activate / deactivate / change the settings for receiving notifications via Telegram.'),
    )

    group.add_argument(
        '-cx',
        '--change-notification-xmpp',
        dest='change_notification_xmpp',
        default=False,
        action='store_true',
        help=('Activate / deactivate / change the settings for receiving notifications via XMPP.'),
    )

    group.add_argument(
        '-md',
        '--manage-database',
        dest='manage_database',
        default=False,
        action='store_true',
        help=(
            'Manage the offline database. It allows you to delete entries from the database'
            + ' that are no longer available locally so that they can be downloaded again.'
        ),
    )

    group.add_argument(
        '-dof',
        '--delete-old-files',
        dest='delete_old_files',
        default=False,
        action='store_true',
        help=(
            'Delete old copies of files. It allows you to delete entries from the database'
            + ' and from local file system.'
        ),
    )

    group.add_argument(
        '--log-responses',
        dest='log_responses',
        default=False,
        action='store_true',
        help=(
            'Generate a responses.log file in which all JSON responses from your Moodle are logged'
            + ' along with the requested URLs.'
        ),
    )

    group.add_argument(
        '--add-all-visible-courses',
        dest='add_all_visible_courses',
        default=False,
        action='store_true',
        help='Add all courses visible to the user to the configuration file.',
    )

    group.add_argument(
        '--version',
        action='version',
        version='moodle-dl ' + __version__,
        help='Print program version and exit',
    )

    parser.add_argument(
        '-sso',
        '--sso',
        dest='sso',
        default=False,
        action='store_true',
        help=(
            'Use SSO login instead of normal login. This flag can be used together with --init and -nt.'
            + ' You will be guided through the Single Sign On (SSO) login process'
            + ' during initialization or new token retrieval.'
        ),
    )

    parser.add_argument(
        '-u',
        '--username',
        dest='username',
        default=None,
        type=str,
        help=('Specify username to skip the query when creating a new token.'),
    )

    parser.add_argument(
        '-pw',
        '--password',
        dest='password',
        default=None,
        type=str,
        help=('Specify password to skip the query when creating a new token.'),
    )

    parser.add_argument(
        '-tk',
        '--token',
        dest='token',
        default=None,
        type=str,
        help=('Specify token to skip the interactive login procedure.'),
    )
    parser.add_argument(
        '-p',
        '--path',
        dest='path',
        default='.',
        type=_dir_path,
        help=(
            'Sets the location of the configuration, logs and downloaded files. PATH must be an'
            + ' existing directory in which you have read and write access. (default: current working directory)'
        ),
    )

    parser.add_argument(
        '-mpac',
        '--max-parallel-api-calls',
        dest='max_parallel_api_calls',
        default=10,
        type=int,
        help=('Sets the number of max parallel Moodle Mobile API calls. (default: %(default)s)'),
    )

    parser.add_argument(
        '-mpd',
        '--max-parallel-downloads',
        dest='max_parallel_downloads',
        default=5,
        type=int,
        help=('Sets the number of max parallel downloads. (default: %(default)s)'),
    )

    parser.add_argument(
        '-mpyd',
        '--max-parallel-yt-dlp',
        dest='max_parallel_yt_dlp',
        default=5,
        type=int,
        help=('Sets the number of max parallel downloads using yt-dlp. (default: %(default)s)'),
    )

    parser.add_argument(
        '-dcs',
        '--download-chunk-size',
        dest='download_chunk_size',
        default=102400,
        type=int,
        help=('Sets the chunk size in bytes used when downloading files. (default: %(default)s)'),
    )

    parser.add_argument(
        '-iye',
        '--ignore-ytdl-errors',
        dest='ignore_ytdl_errors',
        default=False,
        action='store_true',
        help=(
            'Ignore errors that occur when downloading with the help of yt-dlp.'
            + ' Thus, no further attempt will be made to download the file using yt-dlp.'
            + ' By default, yt-dlp errors are critical, so the download of the corresponding file'
            + ' will be aborted and when you run moodle-dl again, the download will be repeated.'
        ),
    )

    parser.add_argument(
        '-wdf',
        '--without-downloading-files',
        dest='without_downloading_files',
        default=False,
        action='store_true',
        help=(
            'Do not download any file. This allows the local database to be updated'
            + ' without having to download all files.'
        ),
    )

    parser.add_argument(
        '--mpl',
        '--max-path-length-workaround',
        dest='max_path_length_workaround',
        default=False,
        action='store_true',
        help=(
            'Make all paths absolute in order to workaround the max_path limitation on Windows.'
            + ' To use relative paths on Windows you should disable the max_path limitation see:'
            + ' https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation'
        ),
    )

    parser.add_argument(
        '-ais',
        '--allow-insecure-ssl',
        dest='allow_insecure_ssl',
        default=False,
        action='store_true',
        help='Allow connections to unpatched servers. Use this option if your server uses a very old SSL version.',
    )
    parser.add_argument(
        '-scv',
        '--skip-cert-verify',
        dest='skip_cert_verify',
        default=False,
        action='store_true',
        help='Don\'t verify TLS certificates. This option should only be used in non production environments.',
    )

    parser.add_argument(
        '-v',
        '--verbose',
        dest='verbose',
        default=False,
        action='store_true',
        help='Print various debugging information',
    )

    parser.add_argument(
        '-q',
        '--quiet',
        dest='quiet',
        default=False,
        action='store_true',
        help='Sets the log level to error',
    )

    parser.add_argument(
        '-ltf',
        '--log-to-file',
        dest='log_to_file',
        default=False,
        action='store_true',
        help='Log all output additionally to a log file called MoodleDL.log',
    )

    return parser


def pre_process_opts(opts: MoodleDlOpts):
    if opts.max_path_length_workaround:
        opts.path = win_max_path_length_workaround(opts.path)

    # Max 32 yt-dlp threads
    opts.max_parallel_yt_dlp = min(opts.max_parallel_downloads, min(32, opts.max_parallel_yt_dlp))


# --- called at the program invocation: -------------------------------------
def main(args=None):
    """The main routine."""
    just_fix_windows_console()
    parser = get_parser()
    opts = MoodleDlOpts(**vars(parser.parse_args(args)))
    setup_logger(opts)
    pre_process_opts(opts)

    config = ConfigHelper(opts.path)
    if opts.init:
        init_config(config, opts)
        sys.exit(0)
    else:
        try:
            config.load()
        except ConfigHelper.NoConfigError as err_config:
            logging.error('Error: %s', err_config)
            logging.warning('You can create a configuration with the --init option')
            sys.exit(-1)

    try:
        if not check_debug():
            ProcessLock.lock(opts.path)

        choose_task(config, opts)

        logging.info('All done. Exiting..')
        ProcessLock.unlock(opts.path)
    except BaseException as base_err:  # pylint: disable=broad-except
        if not isinstance(base_err, ProcessLock.LockError):
            ProcessLock.unlock(opts.path)

        if opts.verbose or check_debug():
            logging.error(traceback.format_exc(), extra={'exception': base_err})
        else:
            logging.error('Exception: %s', base_err)

        logging.debug('Exception-Handling completed. Exiting...')

        sys.exit(1)
