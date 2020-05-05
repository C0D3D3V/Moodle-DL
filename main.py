#!/usr/bin/env python3
# coding=utf-8

import os
import sys
import logging
import argparse
import readline  # needed for arrowkey support in inputs
import traceback
import sentry_sdk

from notification_services.telegram import telegram_service
from notification_services.telegram.telegram_service import TelegramService
from utils import cutie
from utils.logger import Log
from config_service.config_helper import ConfigHelper
from config_service.config_service import ConfigService
from state_recorder.offline_service import OfflineService
from moodle_connector.moodle_service import MoodleService
from download_service.fake_download_service import FakeDownloadService
from download_service.download_service import DownloadService
from notification_services.mail.mail_service import MailService
from notification_services.console.console_service import ConsoleService


class ReRaiseOnError(logging.StreamHandler):
    """
    A logging-handler class which allows the exception-catcher of i.e. PyCharm
    to intervine
    """

    def emit(self, record):
        if hasattr(record, 'exception'):
            raise record.exception
        else:
            raise RuntimeError(record.msg)


def run_init(storage_path, use_sso=False, skip_cert_verify=False):
    config = ConfigHelper(storage_path)

    if config.is_present():
        do_override_input = cutie.prompt_yes_or_no(
            'Do you want to override the existing config?')

        if not do_override_input:
            sys.exit(0)

    MailService(config).interactively_configure()

    do_sentry = cutie.prompt_yes_or_no(
        'Do you want to configure Error Reporting via Sentry?')
    if do_sentry:
        sentry_dsn = input('Please enter your Sentry DSN:   ')
        config.set_property('sentry_dsn', sentry_dsn)

    moodle = MoodleService(config, storage_path, skip_cert_verify)

    if (use_sso):
        moodle.interactively_acquire_sso_token()
    else:
        moodle.interactively_acquire_token()

    print('Configuration finished and saved!')

    if (storage_path == '.'):
        print(
            '  To set a cron-job for this program on your Unix-System:\n' +
            '    1. `crontab -e`\n' +
            '    2. Add `*/15 * * * * cd %s && python3 %smain.py`\n' % (
                os.getcwd(), os.path.join(os.path.dirname(
                    os.path.realpath(__file__)), '')) +
            '    3. Save and you\'re done!'
        )
    else:
        print(
            '  To set a cron-job for this program on your Unix-System:\n' +
            '    1. `crontab -e`\n' +
            '    2. Add `*/15 * * * *' +
            ' cd %s && python3 %smain.py --path %s`\n' % (
                os.getcwd(), os.path.join(os.path.dirname(
                    os.path.realpath(__file__)), ''), storage_path) +
            '    3. Save and you\'re done!'
        )

    print('')

    print('You can always do the additional configuration later' +
          ' with the --config option.')

    do_config = cutie.prompt_yes_or_no(
        'Do you want to make additional configurations now?')

    if do_config:
        run_configure(storage_path, skip_cert_verify)

    print('')
    print('All set and ready to go!')


def run_configure(storage_path, skip_cert_verify=False):
    config = ConfigHelper(storage_path)
    config.load()  # because we do not want to override the other settings

    ConfigService(config, storage_path,
                  skip_cert_verify).interactively_acquire_config()

    print('Configuration successfully updated!')


def run_new_token(storage_path, use_sso=False, skip_cert_verify=False):
    config = ConfigHelper(storage_path)
    config.load()  # because we do not want to override the other settings

    moodle = MoodleService(config, storage_path,
                           skip_cert_verify)

    if (use_sso):
        moodle.interactively_acquire_sso_token()
    else:
        moodle.interactively_acquire_token()

    print('New Token successfully saved!')


def run_manage_database(storage_path):
    config = ConfigHelper(storage_path)
    config.load()  # because we want to only manage configured courses

    offline_service = OfflineService(config, storage_path)
    offline_service.interactively_manage_database()

    print('All done.')


def run_change_notification_mail(storage_path):
    config = ConfigHelper(storage_path)
    config.load()

    MailService(config).interactively_configure()

    print('Configuration successfully updated!')


def run_change_notification_telegram(storage_path):
    config = ConfigHelper(storage_path)
    config.load()

    TelegramService(config).interactively_configure()

    print('Telegram Configuration successfully updated!')


def run_main(storage_path, skip_cert_verify=False,
             without_downloading_files=False):
    logging.basicConfig(
        filename=os.path.join(storage_path, 'MoodleDownloader.log'),
        level=logging.DEBUG,
        format='%(asctime)s  %(levelname)s  {%(module)s}  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info('--- main started ---------------------')
    Log.info('Moodle Downloader starting...')
    if IS_DEBUG:
        logging.info(
            'Debug-Mode detected. Errors will not be logged but instead' +
            ' re-risen.')
        debug_logger = logging.getLogger()
        debug_logger.setLevel(logging.ERROR)
        debug_logger.addHandler(ReRaiseOnError())

    try:
        logging.debug('Loading config...')
        Log.debug('Loading config...')
        config = ConfigHelper(storage_path)
        config.load()
    except BaseException as e:
        logging.error('Error while trying to load the Configuration! ' +
                      'Exiting...', extra={'exception': e})
        Log.error('Error while trying to load the Configuration!')
        sys.exit(-1)

    r_client = False
    try:
        sentry_dsn = config.get_property('sentry_dsn')
        if sentry_dsn:
            sentry_sdk.init(sentry_dsn)
    except BaseException:
        pass

    mail_service = MailService(config)
    tg_service = TelegramService(config)
    console_service = ConsoleService(config)

    try:
        moodle = MoodleService(config, storage_path, skip_cert_verify)

        logging.debug(
            'Checking for changes for the configured Moodle-Account....')
        Log.debug('Checking for changes for the configured Moodle-Account...')
        changed_courses = moodle.fetch_state()

        logging.debug(
            'Start downloading changed files...')
        Log.debug('Start downloading changed files...')

        if (without_downloading_files):
            downloader = FakeDownloadService(
                changed_courses, moodle, storage_path)
        else:
            downloader = DownloadService(
                changed_courses, moodle, storage_path, skip_cert_verify)
        downloader.run()

        changed_courses_to_notify = moodle.recorder.changes_to_notify()

        if (len(changed_courses_to_notify) > 0):
            console_service.notify_about_changes_in_moodle(
                changed_courses_to_notify)

            mail_service.notify_about_changes_in_moodle(
                changed_courses_to_notify)
            tg_service.notify_about_changes_in_moodle(changed_courses_to_notify)

            moodle.recorder.notified(changed_courses_to_notify)

        else:
            logging.info('No changes found for the configured Moodle-Account.')
            Log.warning('No changes found for the configured Moodle-Account.')

        logging.debug('All done. Exiting...')
        Log.success('All done. Exiting..')
    except BaseException as e:
        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={'exception': e})

        if r_client:
            sentry_sdk.capture_exception(e)

        mail_service.notify_about_error(str(e))
        tg_service.notify_about_error(str(e))

        logging.debug('Exception-Handling completed. Exiting...',
                      extra={'exception': e})
        Log.critical('Exception:\n%s' % (
            error_formatted))
        Log.error('The following error occurred during execution: %s' % (
            str(e)))

        sys.exit(-1)


def _dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            ("'%s' is not a valid path." % (str(path)) +
             " Make sure the directory exists."))


# --- called at the program invocation: -------------------------------------
IS_DEBUG = False

if 'pydevd' in sys.modules:
    IS_DEBUG = True
    print('[RUNNING IN DEBUG-MODE!]')

parser = argparse.ArgumentParser(
    description=('Moodle Downloader 2 helps you download all the course' +
                 ' files  of your Moodle account.'))
group = parser.add_mutually_exclusive_group()
group.add_argument('--init', action='store_true',
                   help=('Guides you trough the configuration of the' +
                         ' software, including the activation of' +
                         ' mail-notifications and obtainment of a' +
                         ' login-token for your Moodle-Account. It' +
                         ' does not fetch the current state of your' +
                         ' Moodle-Account.'))

group.add_argument('--config', action='store_true',
                   help=('Guides you through the additional' +
                         ' configuration of the software. This' +
                         ' includes the selection of the courses to' +
                         ' be downloaded and various configuration' +
                         ' options for these courses.'))

group.add_argument('--new-token', action='store_true',
                   help=('Overrides the login-token with a newly obtained' +
                         ' one. It does not fetch the current state of your' +
                         ' Moodle-Account. Use it if at any point in time,' +
                         ' for whatever reason, the saved token gets' +
                         ' rejected by Moodle. It does not affect the rest' +
                         ' of the config.'))

group.add_argument('--change-notification-mail', action='store_true',
                   help=('Activate/deactivate/change the settings for' +
                         ' receiving notifications via e-mail. It does not' +
                         ' affect the rest of the config.'))

group.add_argument('--change-notification-telegram', action='store_true',
                   help=('Activate/deactivate/change the settings for' +
                         ' receiving notifications via Telegram. It does not' +
                         ' affect the rest of the config.'))

group.add_argument('--manage-database', action='store_true',
                   help=('This option lets you manage the offline database.' +
                         ' It allows you to delete entries from the database' +
                         ' that are no longer available locally so that they' +
                         ' can be downloaded again.'))


parser.add_argument('--path', default='.', type=_dir_path,
                    help=('Sets the location of the configuration,' +
                          ' logs and downloaded files. PATH must be an' +
                          ' existing directory in which you have read and' +
                          ' write access. (default: current working' +
                          ' directory)'))

parser.add_argument('--skip-cert-verify', default=False, action='store_true',
                    help='If this flag is set, the SSL certificate ' +
                    'is not verified. This option should only be used in ' +
                    'non production environments.'
                    )

parser.add_argument('--without-downloading-files', default=False,
                    action='store_true',
                    help='If this flag is set, no files are downloaded.' +
                    ' This allows the local database to be updated without' +
                    ' having to download all files.'
                    )

parser.add_argument('--sso', default=False, action='store_true',
                    help='This flag can be used together with --init. If' +
                    ' this flag is set, you will be guided through the' +
                    ' Single Sign On (SSO) login process during' +
                    'initialization.'
                    )

args = parser.parse_args()

use_sso = args.sso
storage_path = args.path
skip_cert_verify = args.skip_cert_verify
without_downloading_files = args.without_downloading_files

if args.init:
    run_init(storage_path, use_sso, skip_cert_verify)
elif args.config:
    run_configure(storage_path, skip_cert_verify)
elif args.new_token:
    run_new_token(storage_path, use_sso, skip_cert_verify)
elif args.change_notification_mail:
    run_change_notification_mail(storage_path)
elif args.change_notification_telegram:
    run_change_notification_telegram(storage_path)
elif args.manage_database:
    run_manage_database(storage_path)
else:
    run_main(storage_path, skip_cert_verify, without_downloading_files)
