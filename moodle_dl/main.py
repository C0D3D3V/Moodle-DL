#!/usr/bin/env python3
# coding=utf-8

import os
import sys
import logging
import argparse
import traceback

from shutil import which

import sentry_sdk

import moodle_dl.utils.process_lock as process_lock


try:
    # In unix readline needs to be loaded so that
    # arrowkeys work in input
    import readline  # pylint: disable=unused-import
except ImportError:
    pass

from logging.handlers import RotatingFileHandler
from moodle_dl.utils import cutie
from moodle_dl.utils.logger import Log
from moodle_dl.version import __version__
from moodle_dl.download_service.path_tools import PathTools
from moodle_dl.config_service.config_helper import ConfigHelper
from moodle_dl.config_service.config_service import ConfigService
from moodle_dl.state_recorder.offline_service import OfflineService
from moodle_dl.moodle_connector.moodle_service import MoodleService
from moodle_dl.download_service.download_service import DownloadService
from moodle_dl.notification_services.mail.mail_service import MailService
from moodle_dl.notification_services.xmpp.xmpp_service import XmppService
from moodle_dl.download_service.fake_download_service import FakeDownloadService
from moodle_dl.notification_services.console.console_service import ConsoleService
from moodle_dl.notification_services.telegram.telegram_service import TelegramService

IS_DEBUG = False


class ReRaiseOnError(logging.StreamHandler):
    """
    A logging-handler class which allows the exception-catcher of i.e. PyCharm
    to intervine
    """

    def emit(self, record):
        if hasattr(record, 'exception'):
            raise record.exception


def run_init(storage_path, use_sso=False, skip_cert_verify=False):
    config = ConfigHelper(storage_path)

    if config.is_present():
        do_override_input = cutie.prompt_yes_or_no(Log.error_str('Do you want to override the existing config?'))

        if not do_override_input:
            sys.exit(0)

    MailService(config).interactively_configure()
    TelegramService(config).interactively_configure()
    XmppService(config).interactively_configure()

    do_sentry = cutie.prompt_yes_or_no('Do you want to configure Error Reporting via Sentry?')
    if do_sentry:
        sentry_dsn = input('Please enter your Sentry DSN:   ')
        config.set_property('sentry_dsn', sentry_dsn)

    moodle = MoodleService(config, storage_path, skip_cert_verify)

    if use_sso:
        moodle.interactively_acquire_sso_token()
    else:
        moodle.interactively_acquire_token()

    Log.success('Configuration finished and saved!')

    if os.name != 'nt':
        if storage_path == '.':
            Log.info(
                '  To set a cron-job for this program on your Unix-System:\n'
                + '    1. `crontab -e`\n'
                + '    2. Add `*/15 * * * * cd "{}" && moodle-dl`\n'.format(os.getcwd())
                + '    3. Save and you\'re done!'
            )
        else:
            Log.info(
                '  To set a cron-job for this program on your Unix-System:\n'
                + '    1. `crontab -e`\n'
                + '    2. Add `*/15 * * * * cd "{}" && moodle-dl -p "{}"`\n'.format(os.getcwd(), storage_path)
                + '    3. Save and you\'re done!'
            )

    print('')

    Log.info('You can always do the additional configuration later with the --config option.')

    do_config = cutie.prompt_yes_or_no('Do you want to make additional configurations now?')

    if do_config:
        run_configure(storage_path, skip_cert_verify)

    print('')
    Log.success('All set and ready to go!')


def run_configure(storage_path, skip_cert_verify=False):
    config = ConfigHelper(storage_path)
    config.load()  # because we do not want to override the other settings

    ConfigService(config, storage_path, skip_cert_verify).interactively_acquire_config()

    Log.success('Configuration successfully updated!')


def run_new_token(storage_path, use_sso=False, username: str = None, password: str = None, skip_cert_verify=False):
    config = ConfigHelper(storage_path)
    config.load()  # because we do not want to override the other settings

    moodle = MoodleService(config, storage_path, skip_cert_verify)

    if use_sso:
        moodle.interactively_acquire_sso_token(use_stored_url=True)
    else:
        moodle.interactively_acquire_token(use_stored_url=True, username=username, password=password)

    Log.success('New Token successfully saved!')


def run_manage_database(storage_path):
    config = ConfigHelper(storage_path)
    config.load()  # because we want to only manage configured courses

    offline_service = OfflineService(config, storage_path)
    offline_service.interactively_manage_database()

    Log.success('All done.')


def run_change_notification_mail(storage_path):
    config = ConfigHelper(storage_path)
    config.load()

    MailService(config).interactively_configure()

    Log.success('Configuration successfully updated!')


def run_change_notification_telegram(storage_path):
    config = ConfigHelper(storage_path)
    config.load()

    TelegramService(config).interactively_configure()

    Log.success('Telegram Configuration successfully updated!')


def run_change_notification_xmpp(storage_path):
    config = ConfigHelper(storage_path)
    config.load()

    XmppService(config).interactively_configure()

    Log.success('XMPP Configuration successfully updated!')


def run_main(
    storage_path,
    verbose=False,
    skip_cert_verify=False,
    ignore_ytdl_errors=False,
    without_downloading_files=False,
    log_responses=False,
):

    log_formatter = logging.Formatter('%(asctime)s  %(levelname)s  {%(module)s}  %(message)s', '%Y-%m-%d %H:%M:%S')
    log_file = os.path.join(storage_path, 'MoodleDownloader.log')
    log_handler = RotatingFileHandler(
        log_file, mode='a', maxBytes=1 * 1024 * 1024, backupCount=2, encoding='utf-8', delay=0
    )

    log_handler.setFormatter(log_formatter)
    if verbose:
        log_handler.setLevel(logging.DEBUG)
    else:
        log_handler.setLevel(logging.INFO)

    app_log = logging.getLogger()
    if verbose:
        app_log.setLevel(logging.DEBUG)
    else:
        app_log.setLevel(logging.INFO)
    app_log.addHandler(log_handler)

    logging.info('--- moodle-dl started ---------------------')
    Log.info('Moodle Downloader starting...')
    if verbose:
        logging.debug('moodle-dl version: %s', __version__)
        logging.debug('python version: %s', ".".join(map(str, sys.version_info[:3])))
        ffmpeg_available = which('ffmpeg') is not None
        logging.debug('Is ffmpeg available: %s', ffmpeg_available)

    if IS_DEBUG:
        logging.info('Debug-Mode detected. Errors will be re-risen.')
        app_log.addHandler(ReRaiseOnError())

    try:
        msg_load_config = 'Loading config...'
        logging.debug(msg_load_config)
        Log.debug(msg_load_config)

        config = ConfigHelper(storage_path)
        config.load()
    except BaseException as e:
        logging.error('Error while trying to load the Configuration! %s Exiting...', e, extra={'exception': e})
        Log.error('Error while trying to load the Configuration!')
        sys.exit(1)

    r_client = False
    try:
        sentry_dsn = config.get_property('sentry_dsn')
        if sentry_dsn:
            sentry_sdk.init(sentry_dsn)
    except BaseException:
        pass

    mail_service = MailService(config)
    tg_service = TelegramService(config)
    xmpp_service = XmppService(config)
    console_service = ConsoleService(config)

    PathTools.restricted_filenames = config.get_restricted_filenames()

    try:
        if not IS_DEBUG:
            process_lock.lock(storage_path)

        moodle = MoodleService(config, storage_path, skip_cert_verify, log_responses)

        msg_checking_for_changes = 'Checking for changes for the configured Moodle-Account....'
        logging.debug(msg_checking_for_changes)
        Log.debug(msg_checking_for_changes)
        changed_courses = moodle.fetch_state()

        if log_responses:
            msg_responses_logged = (
                "All JSON-responses from Moodle have been written to the responses.log file. Exiting..."
            )
            logging.debug(msg_responses_logged)
            Log.success(msg_responses_logged)
            process_lock.unlock(storage_path)
            return

        msg_start_downloading = 'Start downloading changed files...'
        logging.debug(msg_start_downloading)
        Log.debug(msg_start_downloading)

        if without_downloading_files:
            downloader = FakeDownloadService(changed_courses, moodle, storage_path)
        else:
            downloader = DownloadService(changed_courses, moodle, storage_path, skip_cert_verify, ignore_ytdl_errors)
        downloader.run()
        failed_downloads = downloader.get_failed_url_targets()

        changed_courses_to_notify = moodle.recorder.changes_to_notify()

        if len(changed_courses_to_notify) > 0:
            console_service.notify_about_changes_in_moodle(changed_courses_to_notify)
            mail_service.notify_about_changes_in_moodle(changed_courses_to_notify)
            tg_service.notify_about_changes_in_moodle(changed_courses_to_notify)
            xmpp_service.notify_about_changes_in_moodle(changed_courses_to_notify)

            moodle.recorder.notified(changed_courses_to_notify)

        else:
            msg_no_changes = 'No changes found for the configured Moodle-Account.'
            logging.info(msg_no_changes)
            Log.warning(msg_no_changes)

        if len(failed_downloads) > 0:
            console_service.notify_about_failed_downloads(failed_downloads)
            mail_service.notify_about_failed_downloads(failed_downloads)
            tg_service.notify_about_failed_downloads(failed_downloads)
            xmpp_service.notify_about_failed_downloads(failed_downloads)

        process_lock.unlock(storage_path)

        logging.debug('All done. Exiting...')
        Log.success('All done. Exiting..')
    except BaseException as e:
        print('\n')
        if not isinstance(e, process_lock.LockError):
            process_lock.unlock(storage_path)

        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={'exception': e})

        if r_client:
            sentry_sdk.capture_exception(e)

        if verbose:
            Log.critical('Exception:\n%s' % (error_formatted))

        short_error = str(e)
        if not short_error or short_error.isspace():
            short_error = traceback.format_exc(limit=1)

        console_service.notify_about_error(short_error)
        mail_service.notify_about_error(short_error)
        tg_service.notify_about_error(short_error)
        xmpp_service.notify_about_error(short_error)

        logging.debug('Exception-Handling completed. Exiting...')

        sys.exit(1)


def _dir_path(path):
    # Working around MAX_PATH limitation on Windows (see
    # http://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx)
    if os.name == 'nt':
        absfilepath = os.path.abspath(path)
        path = '\\\\?\\' + absfilepath

    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError('"%s" is not a valid path. Make sure the directory exists.' % (str(path)))


def check_debug():
    global IS_DEBUG
    if 'pydevd' in sys.modules:
        IS_DEBUG = True
        Log.debug('[RUNNING IN DEBUG-MODE!]')


def get_parser():
    """
    Creates a new argument parser.
    """
    parser = argparse.ArgumentParser(
        description=('Moodle Downloader 2 helps you download all the course files  of your Moodle account.')
    )
    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        '--version', action='version', version='moodle-dl ' + __version__, help='Print program version and exit'
    )

    group.add_argument(
        '-i',
        '--init',
        action='store_true',
        help=(
            'Guides you trough the configuration of the'
            + ' software, including the activation of'
            + ' mail-notifications and obtainment of a'
            + ' login-token for your Moodle-Account. It'
            + ' does not fetch the current state of your'
            + ' Moodle-Account.'
        ),
    )

    group.add_argument(
        '-c',
        '--config',
        action='store_true',
        help=(
            'Guides you through the additional'
            + ' configuration of the software. This'
            + ' includes the selection of the courses to'
            + ' be downloaded and various configuration'
            + ' options for these courses.'
        ),
    )

    group.add_argument(
        '-nt',
        '--new-token',
        action='store_true',
        help=(
            'Overrides the login-token with a newly obtained'
            + ' one. It does not fetch the current state of your'
            + ' Moodle-Account. Use it if at any point in time,'
            + ' for whatever reason, the saved token gets'
            + ' rejected by Moodle. It does not affect the rest'
            + ' of the config.'
        ),
    )

    group.add_argument(
        '-cm',
        '--change-notification-mail',
        action='store_true',
        help=(
            'Activate/deactivate/change the settings for'
            + ' receiving notifications via e-mail. It does not'
            + ' affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-ct',
        '--change-notification-telegram',
        action='store_true',
        help=(
            'Activate/deactivate/change the settings for'
            + ' receiving notifications via Telegram. It does not'
            + ' affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-cx',
        '--change-notification-xmpp',
        action='store_true',
        help=(
            'Activate/deactivate/change the settings for'
            + ' receiving notifications via XMPP. It does not'
            + ' affect the rest of the config.'
        ),
    )

    group.add_argument(
        '-md',
        '--manage-database',
        action='store_true',
        help=(
            'This option lets you manage the offline database.'
            + ' It allows you to delete entries from the database'
            + ' that are no longer available locally so that they'
            + ' can be downloaded again.'
        ),
    )

    group.add_argument(
        '--log-responses',
        default=False,
        action='store_true',
        help='To generate a responses.log file'
        + ' in which all JSON responses from Moodles are logged'
        + ' along with the requested URL.',
    )

    parser.add_argument(
        '-p',
        '--path',
        default='.',
        type=_dir_path,
        help=(
            'Sets the location of the configuration,'
            + ' logs and downloaded files. PATH must be an'
            + ' existing directory in which you have read and'
            + ' write access. (default: current working'
            + ' directory)'
        ),
    )

    parser.add_argument(
        '-t',
        '--threads',
        default=5,
        type=int,
        help=('Sets the number of download threads. (default: %(default)s)'),
    )

    parser.add_argument(
        '-u',
        '--username',
        default=None,
        type=str,
        help=('Specify username to skip the query when creating a new token.'),
    )

    parser.add_argument(
        '-pw',
        '--password',
        default=None,
        type=str,
        help=('Specify password to skip the query when creating a new token.'),
    )

    parser.add_argument(
        '-v',
        '--verbose',
        default=False,
        action='store_true',
        help='Print various debugging information',
    )

    parser.add_argument(
        '--skip-cert-verify',
        default=False,
        action='store_true',
        help='If this flag is set, the SSL certificate '
        + 'is not verified. This option should only be used in '
        + 'non production environments.',
    )

    parser.add_argument(
        '-iye',
        '--ignore-ytdl-errors',
        default=False,
        action='store_true',
        help='If this option is set, errors that occur when downloading with the help of Youtube-dl are ignored. '
        + 'Thus, no further attempt will be made to download the file using youtube-dl. '
        + 'By default, youtube-dl errors are critical, so the download of the corresponding file '
        + 'will be aborted and when you run moodle-dl again, the download will be repeated.',
    )

    parser.add_argument(
        '--without-downloading-files',
        default=False,
        action='store_true',
        help='If this flag is set, no files are downloaded.'
        + ' This allows the local database to be updated without'
        + ' having to download all files.',
    )

    parser.add_argument(
        '-sso',
        '--sso',
        default=False,
        action='store_true',
        help='This flag can be used together with --init. If'
        + ' this flag is set, you will be guided through the'
        + ' Single Sign On (SSO) login process during'
        + ' initialization.',
    )

    return parser


# --- called at the program invocation: -------------------------------------
def main(args=None):
    """The main routine."""

    check_debug()

    parser = get_parser()
    args = parser.parse_args(args)

    use_sso = args.sso
    verbose = args.verbose
    username = args.username
    password = args.password
    storage_path = args.path
    skip_cert_verify = args.skip_cert_verify
    ignore_ytdl_errors = args.ignore_ytdl_errors
    without_downloading_files = args.without_downloading_files
    log_responses = args.log_responses
    DownloadService.thread_count = args.threads

    if args.init:
        run_init(storage_path, use_sso, skip_cert_verify)
    elif args.config:
        run_configure(storage_path, skip_cert_verify)
    elif args.new_token:
        run_new_token(storage_path, use_sso, username, password, skip_cert_verify)
    elif args.change_notification_mail:
        run_change_notification_mail(storage_path)
    elif args.change_notification_telegram:
        run_change_notification_telegram(storage_path)
    elif args.change_notification_xmpp:
        run_change_notification_xmpp(storage_path)
    elif args.manage_database:
        run_manage_database(storage_path)
    else:
        run_main(storage_path, verbose, skip_cert_verify, ignore_ytdl_errors, without_downloading_files, log_responses)
