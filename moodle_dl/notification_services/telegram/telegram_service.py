import logging
import traceback

from moodle_dl.utils import cutie
from moodle_dl.utils.logger import Log
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget
from moodle_dl.notification_services.telegram.telegram_shooter import TelegramShooter
from moodle_dl.notification_services.notification_service import NotificationService
from moodle_dl.notification_services.telegram.telegram_formater import (
    create_full_moodle_diff_messages,
    create_full_error_messages,
    create_full_failed_downloads_messages,
)


class TelegramService(NotificationService):
    def interactively_configure(self) -> None:
        """
        Guides the user through the configuration of the telegram notification.
        """

        do_telegram = cutie.prompt_yes_or_no('Do you want to activate Notifications via Telegram?')

        if not do_telegram:
            self.config_helper.remove_property('telegram')
        else:
            print('[The following Inputs are not validated!]')
            print(
                'Open the following link for help in setting up telegram notifications:'
                + ' https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Telegram-Notification'
            )
            config_valid = False
            while not config_valid:
                telegram_token = input('Telegram Token:    ')
                telegram_chatID = input('Telegram Chat ID:   ')

                print('Testing Telegram-Config...')

                try:
                    telegram_shooter = TelegramShooter(telegram_token, telegram_chatID)
                    telegram_shooter.send('This is a Testmessage from Moodle Downloader!')
                except BaseException as e:
                    print('Error while sending the test message: %s' % (str(e)))
                    continue

                else:
                    input(
                        'Please check if you received the Testmessage.'
                        + ' If yes, confirm with Return.\nIf not, exit'
                        + ' this program ([CTRL]+[C]) and try again later.'
                    )
                    config_valid = True

                raw_send_error_msg = ''
                while raw_send_error_msg not in ['y', 'n']:
                    raw_send_error_msg = input('Do you want to also get error reports sent in telegram? [y/n]   ')

                do_send_error_msg = raw_send_error_msg == 'y'

                telegram_cfg = {
                    'token': telegram_token,
                    'chat_id': telegram_chatID,
                    'send_error_msg': do_send_error_msg,
                }

                self.config_helper.set_property('telegram', telegram_cfg)

    def _is_configured(self) -> bool:
        # Checks if the sending of Telegram messages has been configured.
        try:
            self.config_helper.get_property('telegram')
            return True
        except ValueError:
            logging.debug('Telegram-Notifications not configured, skipping.')
            return False

    def _send_messages(self, messages: [str]):
        """
        Sends an message
        """
        if not self._is_configured() or messages is None or len(messages) == 0:
            return

        telegram_cfg = self.config_helper.get_property('telegram')

        logging.debug('Sending Notification via Telegram...')
        Log.debug('Sending Notification via Telegram... (Please wait)')

        telegram_shooter = TelegramShooter(telegram_cfg['token'], telegram_cfg['chat_id'])

        for message_content in messages:
            try:
                telegram_shooter.send(message_content)
            except BaseException as e:
                error_formatted = traceback.format_exc()
                logging.error('While sending notification:\n%s' % (error_formatted), extra={'exception': e})
                raise e  # to be properly notified via Sentry

    def notify_about_changes_in_moodle(self, changes: [Course]) -> None:
        """
        Sends out a notification about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        if not self._is_configured():
            return

        messages = create_full_moodle_diff_messages(changes)

        self._send_messages(messages)

    def notify_about_error(self, error_description: str):
        """
        Sends out an error message if configured to do so.
        @param error_description: The error object.
        """
        if not self._is_configured():
            return

        telegram_cfg = self.config_helper.get_property('telegram')

        if not telegram_cfg.get('send_error_msg', True):
            return
        messages = create_full_error_messages(error_description)

        self._send_messages(messages)

    def notify_about_failed_downloads(self, failed_downloads: [URLTarget]):
        """
        Sends out an message about failed download if configured to send out error messages.
        @param failed_downloads: A list of failed URLTargets.
        """
        if not self._is_configured():
            return

        telegram_cfg = self.config_helper.get_property('telegram')

        if not telegram_cfg.get('send_error_msg', True):
            return
        messages = create_full_failed_downloads_messages(failed_downloads)

        self._send_messages(messages)
