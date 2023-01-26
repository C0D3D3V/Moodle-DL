import argparse
import logging
import os
import sys
import traceback

from logging.handlers import RotatingFileHandler
from shutil import which

import sentry_sdk

try:
    # In unix readline needs to be loaded so that
    # arrowkeys work in input
    import readline  # pylint: disable=unused-import
except ImportError:
    pass

from colorama import just_fix_windows_console

from moodle_dl.config_service.config_helper import ConfigHelper
from moodle_dl.config_service.config_service import ConfigService
from moodle_dl.download_service.download_service import DownloadService
from moodle_dl.download_service.fake_download_service import FakeDownloadService
from moodle_dl.moodle_connector.moodle_service import MoodleService
from moodle_dl.notification_services.console.console_service import ConsoleService
from moodle_dl.notification_services.mail.mail_service import MailService
from moodle_dl.notification_services.telegram.telegram_service import TelegramService
from moodle_dl.notification_services.xmpp.xmpp_service import XmppService
from moodle_dl.state_recorder.offline_service import OfflineService
from moodle_dl.utils import Log, Cutie, ProcessLock, check_debug, check_verbose, PathTools as PT
from moodle_dl.version import __version__


class ReRaiseOnError(logging.StreamHandler):
    """
    A logging-handler class which allows the exception-catcher of i.e. PyCharm
    to intervine
    """

    def emit(self, record):
        if hasattr(record, 'exception'):
            raise record.exception


def run_init(config: ConfigHelper, opts):
    if config.is_present():
        do_override_input = Cutie.prompt_yes_or_no(Log.error_str('Do you want to override the existing config?'))

        if not do_override_input:
            sys.exit(0)

    notify_services = [MailService(config), TelegramService(config), XmppService(config)]
    for service in notify_services:
        service.interactively_configure()

    do_sentry = Cutie.prompt_yes_or_no('Do you want to configure Error Reporting via Sentry?')
    if do_sentry:
        sentry_dsn = input('Please enter your Sentry DSN:   ')
        config.set_property('sentry_dsn', sentry_dsn)

    MoodleService(config, opts).interactively_acquire_token()

    Log.success('Configuration finished and saved!')

    if os.name != 'nt':
        working_dir = os.path.abspath(opts.path)
        moodle_dl_path = os.path.abspath(sys.argv[0])
        Log.info(
            '  To set a cron-job for this program on your Unix-System:\n'
            + '    1. `crontab -e`\n'
            + f'    2. Add `*/15 * * * * cd "{working_dir}" && "{moodle_dl_path}" >/dev/null 2>&1`\n'
            + '    3. Save and you\'re done!'
        )

        Log.info(
            'For more ways to run `moodle-dl` periodically, take a look at the wiki'
            + ' (https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Start-Moodle-dl-periodically-or-via-Telegram)'
        )
    else:
        Log.info(
            'If you want to run moodle-dl periodically, you can take a look at the wiki '
            + '(https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Start-Moodle-dl-periodically-or-via-Telegram)'
        )

    print('')

    Log.info('You can always do the additional configuration later with the --config option.')

    do_config = Cutie.prompt_yes_or_no('Do you want to make additional configurations now?')
    if do_config:
        ConfigService(config, opts).interactively_acquire_config()

    print('')
    Log.success('All set and ready to go!')


def run_main(config: ConfigHelper, opts):
    setup_logger(opts.path)

    sentry_connected = False
    try:
        sentry_dsn = config.get_property('sentry_dsn')
        if sentry_dsn:
            sentry_sdk.init(sentry_dsn)
            sentry_connected = True
    except (ValueError, sentry_sdk.utils.BadDsn, sentry_sdk.utils.ServerlessTimeoutWarning):
        pass

    notify_services = [ConsoleService(config), MailService(config), TelegramService(config), XmppService(config)]

    # Todo: Change this
    PT.restricted_filenames = config.get_restricted_filenames()

    try:
        moodle = MoodleService(config, opts)

        msg_checking_for_changes = 'Checking for changes for the configured Moodle-Account....'
        logging.debug(msg_checking_for_changes)
        Log.debug(msg_checking_for_changes)
        changed_courses = moodle.fetch_state()

        if opts.log_responses:
            msg_responses_logged = "All JSON-responses from Moodle have been written to the responses.log file."
            logging.debug(msg_responses_logged)
            Log.success(msg_responses_logged)
            return

        msg_start_downloading = 'Start downloading changed files...'
        logging.debug(msg_start_downloading)
        Log.debug(msg_start_downloading)

        if opts.without_downloading_files:
            downloader = FakeDownloadService(changed_courses, moodle, opts)
        else:
            downloader = DownloadService(changed_courses, moodle, opts)
        downloader.run()
        failed_downloads = downloader.get_failed_url_targets()

        changed_courses_to_notify = moodle.recorder.changes_to_notify()

        if len(changed_courses_to_notify) > 0:
            for service in notify_services:
                service.notify_about_changes_in_moodle(changed_courses_to_notify)

            moodle.recorder.notified(changed_courses_to_notify)

        else:
            logging.info('No changes found for the configured Moodle-Account.')
            Log.warning('No changes found for the configured Moodle-Account.')

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


def setup_logger(storage_path: str):
    log_formatter = logging.Formatter('%(asctime)s  %(levelname)s  {%(module)s}  %(message)s', '%Y-%m-%d %H:%M:%S')
    log_file = os.path.join(storage_path, 'MoodleDownloader.log')
    log_handler = RotatingFileHandler(
        log_file, mode='a', maxBytes=1 * 1024 * 1024, backupCount=2, encoding='utf-8', delay=0
    )

    log_handler.setFormatter(log_formatter)
    IS_VERBOSE = check_verbose()
    if IS_VERBOSE:
        log_handler.setLevel(logging.DEBUG)
    else:
        log_handler.setLevel(logging.INFO)

    app_log = logging.getLogger()
    if IS_VERBOSE:
        app_log.setLevel(logging.DEBUG)
    else:
        app_log.setLevel(logging.INFO)
    app_log.addHandler(log_handler)

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    logging.info('--- moodle-dl started ---------------------')
    Log.info('Moodle Downloader starting...')
    if IS_VERBOSE:
        logging.debug('moodle-dl version: %s', __version__)
        logging.debug('python version: %s', ".".join(map(str, sys.version_info[:3])))
        ffmpeg_available = which('ffmpeg') is not None
        logging.debug('Is ffmpeg available: %s', ffmpeg_available)

    if check_debug():
        logging.info('Debug-Mode detected. Errors will be re-risen.')
        app_log.addHandler(ReRaiseOnError())


def _dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f'"{str(path)}" is not a valid path. Make sure the directory exists.')


def win_max_path_length_workaround(path):
    # Working around MAX_PATH limitation on Windows (see
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx)
    if os.name == 'nt':
        abs_file_path = PT.get_abs_path(path)
        path = '\\\\?\\' + abs_file_path
        Log.debug("Using windows max path length workaround")
    else:
        Log.info("You are not on Windows, you don't need to use this workaround")
    return path


def get_parser():
    """
    Creates a new argument parser.
    """
    parser = argparse.ArgumentParser(
        description=('Moodle Downloader 2 helps you download all the course files  of your Moodle account.')
    )
    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '--version',
        action='version',
        version='moodle-dl ' + __version__,
        help='Print program version and exit',
    )

    group.add_argument(
        '-i',
        '--init',
        dest='init',
        default=False,
        action='store_true',
        help=(
            'Guides you trough the configuration of the software, including the activation of'
            + ' notifications services and obtainment of a login-token for your Moodle-Account. It'
            + ' does not fetch the current state of you Moodle-Account.'
        ),
    )

    group.add_argument(
        '-c',
        '--config',
        dest='config',
        default=False,
        action='store_true',
        help=(
            'Guides you through the additional configuration of the software. This includes'
            + ' the selection of the courses to be downloaded and various configuration options for these courses.'
        ),
    )

    group.add_argument(
        '-nt',
        '--new-token',
        dest='new_token',
        default=False,
        action='store_true',
        help=(
            'Overrides the login-token with a newly obtained one. It does not fetch the current state of your'
            + ' Moodle-Account. Use it if at any point in time, for whatever reason, the saved token gets'
            + ' rejected by Moodle. It does not affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-cm',
        '--change-notification-mail',
        dest='change_notification_mail',
        default=False,
        action='store_true',
        help=(
            'Activate / deactivate / change the settings for receiving notifications via e-mail. It does not'
            + ' affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-ct',
        '--change-notification-telegram',
        dest='change_notification_telegram',
        default=False,
        action='store_true',
        help=(
            'Activate / deactivate / change the settings for receiving notifications via Telegram. It does not'
            + ' affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-cx',
        '--change-notification-xmpp',
        dest='change_notification_xmpp',
        default=False,
        action='store_true',
        help=(
            'Activate / deactivate / change the settings for receiving notifications via XMPP. It does not'
            + ' affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-md',
        '--manage-database',
        dest='manage_database',
        default=False,
        action='store_true',
        help=(
            'This option lets you manage the offline database. It allows you to delete entries from the database'
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
            'This option lets you delete old copies of files. It allows you to delete entries from the database'
            + ' and from local file system.'
        ),
    )

    group.add_argument(
        '--log-responses',
        dest='log_responses',
        default=False,
        action='store_true',
        help='To generate a responses.log file in which all JSON responses from Moodles are logged'
        + ' along with the requested URL.',
    )

    group.add_argument(
        '--add-all-visible-courses',
        default=False,
        action='store_true',
        help='To add all courses visible to the user to the configuration file.',
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
        '--mpl',
        '--max-path-length-workaround',
        dest='max_path_length_workaround',
        default=False,
        action='store_true',
        help=(
            'If this flag is set, all path are made absolute in order to workaround the max_path limitation on Windows.'
            + 'To use relative paths on Windows you should disable the max_path limitation'
            + 'https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation'
        ),
    )

    parser.add_argument(
        '-t',
        '--threads',
        dest='threads',
        default=5,
        type=int,
        help=('Sets the number of max parallel downloads. (default: %(default)s)'),
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
        '-v',
        '--verbose',
        dest='verbose',
        default=False,
        action='store_true',
        help='Print various debugging information',
    )

    parser.add_argument(
        '--skip-cert-verify',
        dest='skip_cert_verify',
        default=False,
        action='store_true',
        help='If this flag is set, TLS certificates are not verified. This option should only be used in '
        + 'non production environments.',
    )

    parser.add_argument(
        '-iye',
        '--ignore-ytdl-errors',
        dest='ignore_ytdl_errors',
        default=False,
        action='store_true',
        help='If this option is set, errors that occur when downloading with the help of yt-dlp are ignored. '
        + 'Thus, no further attempt will be made to download the file using yt-dlp. '
        + 'By default, yt-dlp errors are critical, so the download of the corresponding file '
        + 'will be aborted and when you run moodle-dl again, the download will be repeated.',
    )

    parser.add_argument(
        '--without-downloading-files',
        dest='without_downloading_files',
        default=False,
        action='store_true',
        help='If this flag is set, no files are downloaded. This allows the local database to be updated without'
        + ' having to download all files.',
    )

    parser.add_argument(
        '-sso',
        '--sso',
        dest='sso',
        default=False,
        action='store_true',
        help='This flag can be used together with --init and -nt. If this flag is set, you will be guided through the'
        + ' Single Sign On (SSO) login process during initialization or new token retrieval.',
    )

    return parser


def pre_process_opts(opts):
    if opts.max_path_length_workaround:
        opts.path = win_max_path_length_workaround(opts.path)


# --- called at the program invocation: -------------------------------------
def main(args=None):
    """The main routine."""
    just_fix_windows_console()
    parser = get_parser()
    opts = parser.parse_args(args)  # opts is of type Namespace
    pre_process_opts(opts)

    # Todo: Change this
    DownloadService.thread_count = args.threads

    config = ConfigHelper(opts.path)
    if opts.init:
        run_init(config, opts)
        exit(0)
    else:
        try:
            config.load()
        except ConfigHelper.NoConfigError as err_config:
            Log.error(f'Error: {err_config!s}')
            Log.warning('You can create a configuration with the --init option')
            exit(-1)

    try:
        if not check_debug():
            ProcessLock.lock(opts.path)

        if opts.config:
            ConfigService(config, opts).interactively_acquire_config()
        elif opts.new_token:
            MoodleService(config, opts).interactively_acquire_token(use_stored_url=True)
        elif opts.change_notification_mail:
            MailService(config).interactively_configure()
        elif opts.change_notification_telegram:
            TelegramService(config).interactively_configure()
        elif opts.change_notification_xmpp:
            XmppService(config).interactively_configure()
        elif opts.manage_database:
            OfflineService(config, opts).interactively_manage_database()
        elif opts.delete_old_files:
            OfflineService(config, opts).delete_old_files()
        elif opts.add_all_visible_courses:
            ConfigService(config, opts).interactively_add_all_visible_courses()
        else:
            run_main(config, opts)

        Log.success('All done. Exiting..')
        ProcessLock.unlock(opts.path)
    except BaseException as base_err:
        print('\n')
        if not isinstance(base_err, ProcessLock.LockError):
            ProcessLock.unlock(opts.path)

        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={'exception': base_err})

        if check_verbose() or check_debug():
            Log.critical(f'{error_formatted}')
        else:
            Log.error(f'Exception: {base_err!s}')

        logging.debug('Exception-Handling completed. Exiting...')

        sys.exit(1)
