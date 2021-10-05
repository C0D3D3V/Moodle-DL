import logging
import traceback

from getpass import getpass

from moodle_dl.utils import cutie
from moodle_dl.utils.logger import Log
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget
from moodle_dl.notification_services.mail.mail_shooter import MailShooter
from moodle_dl.notification_services.notification_service import NotificationService
from moodle_dl.notification_services.mail.mail_formater import (
    create_full_welcome_mail,
    create_full_moodle_diff_mail,
    create_full_error_mail,
    create_full_failed_downloads_mail,
)


class MailService(NotificationService):
    def interactively_configure(self) -> None:
        """
        Guides the user through the configuration of the mail notification.
        """

        do_mail = cutie.prompt_yes_or_no('Do you want to activate Notifications via mail?')

        if not do_mail:
            self.config_helper.remove_property('mail')
        else:
            print('[The following Inputs are not validated!]')

            config_valid = False
            while not config_valid:
                sender = input('E-Mail-Address of the Sender:   ')
                server_host = input('Host of the SMTP-Server:   ')
                server_port = input('Port of the SMTP-Server [STARTTLS, default 587]:   ')
                if server_port == '':
                    print('Using default port 587!')
                    server_port = '587'
                username = input('Username for the SMTP-Server:   ')
                password = getpass('Password for the SMTP-Server [no output]:   ')
                target = input('E-Mail-Address of the Target:   ')

                print('Testing Mail-Config...')
                welcome_content = create_full_welcome_mail()
                mail_shooter = MailShooter(sender, server_host, int(server_port), username, password)
                try:
                    mail_shooter.send(target, 'Hey!', welcome_content[0], welcome_content[1])
                except BaseException as e:
                    print('Error while sending the test mail: %s' % (str(e)))
                    continue
                else:
                    input(
                        'Please check if you received the Welcome-Mail.'
                        + ' If yes, confirm with Return.\nIf not, exit'
                        + ' this program ([CTRL]+[C]) and try again later.'
                    )
                    config_valid = True

                raw_send_error_msg = ''
                while raw_send_error_msg not in ['y', 'n']:
                    raw_send_error_msg = input('Do you want to also get error reports sent by mail? [y/n]   ')
                do_send_error_msg = raw_send_error_msg == 'y'

                mail_cfg = {
                    'sender': sender,
                    'server_host': server_host,
                    'server_port': server_port,
                    'username': username,
                    'password': password,
                    'target': target,
                    'send_error_msg': do_send_error_msg,
                }

                self.config_helper.set_property('mail', mail_cfg)

    def _is_configured(self) -> bool:
        # Checks if the sending of emails has been configured.
        try:
            self.config_helper.get_property('mail')
            return True
        except ValueError:
            logging.debug('Mail-Notifications not configured, skipping.')
            return False

    def _send_mail(self, subject, mail_content: (str, {str: str})):
        """
        Sends an email
        """
        if not self._is_configured():
            return

        mail_cfg = self.config_helper.get_property('mail')

        try:
            logging.debug('Sending Notification via Mail...')
            Log.debug('Sending Notification via Mail... (Please wait)')

            mail_shooter = MailShooter(
                mail_cfg['sender'],
                mail_cfg['server_host'],
                int(mail_cfg['server_port']),
                mail_cfg['username'],
                mail_cfg['password'],
            )
            mail_shooter.send(mail_cfg['target'], subject, mail_content[0], mail_content[1])
        except BaseException as e:
            error_formatted = traceback.format_exc()
            logging.error('While sending notification:\n%s', error_formatted, extra={'exception': e})
            raise e  # to be properly notified via Sentry

    def notify_about_changes_in_moodle(self, changes: [Course]) -> None:
        """
        Sends out a notification email about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        if not self._is_configured():
            return

        mail_content = create_full_moodle_diff_mail(changes)

        diff_count = 0
        for course in changes:
            diff_count += len(course.files)

        self._send_mail('%s new Changes in the Moodle courses!' % (diff_count), mail_content)

    def notify_about_error(self, error_description: str):
        """
        Sends out an error mail if configured to do so.
        @param error_description: The error object.
        """
        if not self._is_configured():
            return

        mail_cfg = self.config_helper.get_property('mail')

        if not mail_cfg.get('send_error_msg', True):
            return

        mail_content = create_full_error_mail(error_description)
        self._send_mail('Error!', mail_content)

    def notify_about_failed_downloads(self, failed_downloads: [URLTarget]):
        """
        Sends out an mail with all failed download if configured to send out error messages.
        @param failed_downloads: A list of failed URLTargets.
        """
        if not self._is_configured():
            return

        mail_cfg = self.config_helper.get_property('mail')

        if not mail_cfg.get('send_error_msg', True):
            return

        mail_content = create_full_failed_downloads_mail(failed_downloads)
        self._send_mail('Faild to download files!', mail_content)
