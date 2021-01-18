import logging
import traceback

from getpass import getpass

from moodle_dl.utils import cutie
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget
from moodle_dl.notification_services.xmpp.xmpp_shooter import XmppShooter
from moodle_dl.notification_services.notification_service import NotificationService
from moodle_dl.notification_services.telegram.telegram_formater import (
    create_full_moodle_diff_messages,
    create_full_error_messages,
    create_full_failed_downloads_messages,
)


class XmppService(NotificationService):
    def interactively_configure(self) -> None:
        """
        Guides the user through the configuration of the xmpp notification.
        """

        do_xmpp = cutie.prompt_yes_or_no('Do you want to activate Notifications via XMPP?')

        if not do_xmpp:
            self.config_helper.remove_property('xmpp')
        else:
            print('[The following Inputs are not validated!]')
            config_valid = False
            while not config_valid:
                sender = input('JID of the Sender:   ')
                password = getpass('Password for the Sender [no output]:   ')
                target = input('JID of the Target:   ')
                print('Testing XMPP-Config...')

                try:
                    xmpp_shooter = XmppShooter(sender, password, target)
                    xmpp_shooter.send('This is a Testmessage from Moodle Downloader!')
                except BaseException as e:
                    print('Error while sending the test message: %s' % (str(e)))

                else:
                    input(
                        'Please check if you received the Testmessage.'
                        + ' If yes, confirm with Return.\nIf not, exit'
                        + ' this program ([CTRL]+[C]) and try again later.'
                    )
                    config_valid = True

                raw_send_error_msg = ''
                while raw_send_error_msg not in ['y', 'n']:
                    raw_send_error_msg = input('Do you want to also get error reports sent in xmpp? [y/n]   ')

                do_send_error_msg = raw_send_error_msg == 'y'

                xmpp_cfg = {
                    'sender': sender,
                    'password': password,
                    'target': target,
                    'send_error_msg': do_send_error_msg,
                }

                self.config_helper.set_property('xmpp', xmpp_cfg)

    def _is_configured(self) -> bool:
        # Checks if the sending of XMPP messages has been configured.
        try:
            self.config_helper.get_property('xmpp')
            return True
        except ValueError:
            logging.debug('XMPP-Notifications not configured, skipping.')
            return False

    def _send_message(self, message_content: str):
        """
        Sends an message
        """
        if not self._is_configured():
            return

        xmpp_cfg = self.config_helper.get_property('xmpp')

        try:
            logging.debug('Sending Notification via XMPP...')
            xmpp_shooter = XmppShooter(xmpp_cfg['sender'], xmpp_cfg['password'], xmpp_cfg['target'])
            xmpp_shooter.send(message_content)
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

        for message_content in messages:
            self._send_message(message_content)

    def notify_about_error(self, error_description: str):
        """
        Sends out an error message if configured to do so.
        @param error_description: The error object.
        """
        if not self._is_configured():
            return

        xmpp_cfg = self.config_helper.get_property('xmpp')

        if not xmpp_cfg.get('send_error_msg', True):
            return
        messages = create_full_error_messages(error_description)

        for message_content in messages:
            self._send_message(message_content)

    def notify_about_failed_downloads(self, failed_downloads: [URLTarget]):
        """
        Sends out an message about failed download if configured to send out error messages.
        @param failed_downloads: A list of failed URLTargets.
        """
        if not self._is_configured():
            return

        xmpp_cfg = self.config_helper.get_property('xmpp')

        if not xmpp_cfg.get('send_error_msg', True):
            return
        messages = create_full_failed_downloads_messages(failed_downloads)

        for message_content in messages:
            self._send_message(message_content)