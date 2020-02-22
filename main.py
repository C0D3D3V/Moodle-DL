#!/usr/bin/env python3
# coding=utf-8

import os
import sys
import logging
import argparse
import traceback
import sentry_sdk

from colorama import init

from utils.logger import Log
from config_service.config_helper import ConfigHelper
from config_service.config_service import ConfigService
from moodle_connector.moodle_service import MoodleService
from download_service.download_service import DownloadService
from notification_services.mail.mail_service import MailService
from notification_services.console.console_service import ConsoleService


init()


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


def run_init(storage_path):
    config = ConfigHelper(storage_path)

    if config.is_present():
        do_override_input = input(
            'Do you want to override the existing' +
            ' config [y/n]?   ').lower()
        while do_override_input not in ['y', 'n']:
            do_override_input = input('Unrecognized input.' +
                                      ' Try again:   ').lower()

        if do_override_input == 'n':
            sys.exit(0)

    MailService(config).interactively_configure()

    raw_do_sentry = ''
    while raw_do_sentry not in ['y', 'n']:
        raw_do_sentry = input(
            'Do you want to configure Error Reporting via' +
            ' Sentry? [y/n]   ').lower()
    if raw_do_sentry == 'y':
        sentry_dsn = input('Please enter your Sentry DSN:   ')
        config.set_property('sentry_dsn', sentry_dsn)

    moodle = MoodleService(config, storage_path)
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
    raw_do_config = ''
    while raw_do_config not in ['y', 'n']:
        raw_do_config = input(
            'Do you want to make additional configurations now?' +
            ' You can always do the additional configuration later' +
            ' with the --config option. [y/n]   ').lower()
    if raw_do_config == 'y':
        run_configure(storage_path)

    print('')
    print('All set and ready to go!')


def run_configure(storage_path):
    config = ConfigHelper(storage_path)
    config.load()  # because we do not want to override the other settings

    ConfigService(config, storage_path).interactively_acquire_config()

    print('Configuration successfully updated!')


def run_new_token(storage_path):
    config = ConfigHelper(storage_path)
    config.load()  # because we do not want to override the other settings

    MoodleService(config, storage_path).interactively_acquire_token()

    print('New Token successfully saved!')


def run_change_notification_mail(storage_path):
    config = ConfigHelper(storage_path)
    config.load()

    MailService(config).interactively_configure()

    print('Configuration successfully updated!')


def run_main(storage_path):
    logging.basicConfig(
        filename=os.path.join(storage_path, 'MoodleDownloader.log'),
        level=logging.DEBUG,
        format='%(asctime)s  %(levelname)s  {%(module)s}  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info('--- main started ---------------------')
    Log.info('Moodle Donwlaoder starting...')
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
    console_service = ConsoleService(config)

    try:
        moodle = MoodleService(config, storage_path)

        logging.debug(
            'Checking for changes for the configured Moodle-Account....')
        Log.debug('Checking for changes for the configured Moodle-Account...')
        changed_courses = moodle.fetch_state()

        diff_count = 0

        logging.debug(
            'Start downloading changed files...')
        Log.debug('Start downloading changed files...')

        downloader = DownloadService(changed_courses, moodle, storage_path)
        downloader.run()

        changed_courses_to_notify = moodle.recorder.changes_to_notify()

        for course in changed_courses:
            diff_count += len(course.files)

        if diff_count > 0:
            logging.info('%s changes found for the configured Moodle-Account.'
                         % (diff_count))

            Log.success('%s changes found for the configured Moodle-Account.'
                        % (diff_count))

            console_service.notify_about_changes_in_moodle(
                changed_courses)
        else:
            logging.info('No changes found for the configured Moodle-Account.')
            Log.warning('No changes found for the configured Moodle-Account.')

        if (len(changed_courses_to_notify) > 0):
            mail_service.notify_about_changes_in_moodle(
                changed_courses_to_notify)
            moodle.recorder.notified(changed_courses_to_notify)

        logging.debug('All done. Exiting...')
        Log.success('All done. Exiting..')
    except BaseException as e:
        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={'exception': e})

        if r_client:
            sentry_sdk.capture_exception(e)

        mail_service.notify_about_error(str(e))

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
            f"'{path}' is not a valid path. Make sure the directory exists.")


# --- called at the program invocation: -------------------------------------
IS_DEBUG = False

if 'pydevd' in sys.modules:
    IS_DEBUG = True
    print('[RUNNING IN DEBUG-MODE!]')

parser = argparse.ArgumentParser(
    description=('Moodle Donwlaoder 2 helps you download all the course' +
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

parser.add_argument('--path', default='.', type=_dir_path,
                    help=('Sets the location of the configuration,' +
                          ' logs and downloaded files. PATH must be an' +
                          ' existing directory in which you have read and' +
                          ' write access. (default: current working' +
                          ' directory)'))

args = parser.parse_args()

storage_path = args.path

if args.init:
    run_init(storage_path)
elif args.config:
    run_configure(storage_path)
elif args.new_token:
    run_new_token(storage_path)
elif args.change_notification_mail:
    run_change_notification_mail(storage_path)
else:
    run_main(storage_path)
