#!/usr/bin/env python3
# coding=utf-8

import logging
import os
import sys
import traceback

from raven import fetch_git_sha
from raven.handlers.logging import Client as RavenClient

from utils.config_helper import ConfigHelper
from moodle_connector.dualis_service import MoodleService
from moodle_connector.request_helper import MoodleSleepingError
from notification_services.mail.mail_service import MailService


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


def run_init():
    config = ConfigHelper()

    if config.is_present():
        do_override_input = input(
            'Do you want to override the existing config [y/n]?   ')
        while not (do_override_input == 'y' or do_override_input == 'n'):
            do_override_input = input('Unrecognized input. Try again:   ')

        if do_override_input == 'n':
            sys.exit(0)

    MailService(config).interactively_configure()

    raw_do_sentry = ''
    while raw_do_sentry not in ['y', 'n']:
        raw_do_sentry = input(
            'Do you want to configure Error Reporting via Sentry? [y/n]')
    if raw_do_sentry == 'y':
        sentry_dsn = input('Please enter your Sentry DSN:   ')
        config.set_property('sentry_dsn', sentry_dsn)

    moodle = MoodleService(config)
    moodle.interactively_acquire_token()

    print('Configuration finished and saved!')

    print(
        '  To set a cron-job for this program on your Unix-System:\n'
        + '    1. `crontab -e`\n'
        + '    2. Add `*/15 * * * * cd %s && python3 main.py`\n' % (
            os.path.dirname(os.path.realpath(__file__)))
        + '    3. Save and you\'re done!'
    )

    print('All set and ready to go!')


def run_new_token():
    config = ConfigHelper()
    config.load()  # because we do not want to override the other settings

    MoodleService(config).interactively_acquire_token()

    print('New Token successfully saved!')


def run_change_notification_mail():
    config = ConfigHelper()
    config.load()

    MailService(config).interactively_configure()

    print('Configuration successfully updated!')


def run_main():
    logging.basicConfig(
        filename='MoodleWatcher.log', level=logging.DEBUG,
        format='%(asctime)s  %(levelname)s  {%(module)s}  %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info('--- main started ---------------------')
    if IS_DEBUG:
        logging.info(
            'Debug-Mode detected. Errors will not be logged but instead'
            + ' re-risen.')
        debug_logger = logging.getLogger()
        debug_logger.setLevel(logging.ERROR)
        debug_logger.addHandler(ReRaiseOnError())

    try:
        logging.debug('Loading config...')
        config = ConfigHelper()
        config.load()
    except BaseException as e:
        logging.error('Error while trying to load the Configuration! '
                      + 'Exiting...', extra={'exception': e})
        sys.exit(-1)

    r_client = None
    try:
        sentry_dsn = config.get_property('sentry_dsn')
        if sentry_dsn:
            r_client = RavenClient(
                sentry_dsn,
                auto_log_stacks=True,
                release=fetch_git_sha(os.path.dirname(__file__))
            )
    except BaseException:
        pass

    mail_service = MailService(config)

    try:
        moodle = MoodleService(config)

        logging.debug(
            'Checking for changes for the configured Moodle-Account....')
        changes = moodle.fetch_state()
        diff_count = 0

        for course_name in changes:
            diff_count += len(changes[course_name])

        if diff_count > 0:
            logging.info('%s changes found for the configured Moodle-Account.'
                         % (diff_count))
            mail_service.notify_about_changes_in_moodle(changes)
        else:
            logging.info('No changes found for the configured Moodle-Account.')

        logging.debug('All done. Exiting...')
    except MoodleSleepingError:
        logging.info('Moodle is sleeping, exiting and soon trying again.')
        sys.exit(-1)
    except BaseException as e:
        error_formatted = traceback.format_exc()
        logging.error(error_formatted, extra={'exception': e})

        if r_client:
            r_client.captureException(exec_info=True)

        mail_service.notify_about_error(str(e))

        logging.debug('Exception-Handling completed. Exiting...',
                      extra={'exception': e})
        sys.exit(-1)


# --- called at the program invocation: ---------------------
IS_DEBUG = False

if 'pydevd' in sys.modules:
    IS_DEBUG = True
    print('[RUNNING IN DEBUG-MODE!]')

if len(sys.argv) == 2:
    if sys.argv[1] == '--init':
        run_init()
    elif sys.argv[1] == '--new-token':
        run_new_token()
    elif sys.argv[1] == '--change-notification-mail':
        run_change_notification_mail()
elif len(sys.argv) == 1:
    # the name of the executed file always gets passed
    run_main()
else:
    print(
        'Unrecognized argument or combination of arguments passed!'
        + '\n  Possible arguments: None, `--init`, `--new-token`, '
        + '`--change-notification-mail`'
    )
    sys.exit(-1)
