import logging
import traceback

from typing import List

from moodle_dl.downloader.task import Task
from moodle_dl.notifications.mail.mail_shooter import MailShooter
from moodle_dl.notifications.notification_service import NotificationService
from moodle_dl.types import Course
from moodle_dl.notifications.mail.mail_formater import (
    create_full_error_mail,
    create_full_failed_downloads_mail,
    create_full_moodle_diff_mail,
)


class MailService(NotificationService):
    def _is_configured(self) -> bool:
        # Checks if the sending of emails has been configured.
        try:
            self.config.get_property('mail')
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

        mail_cfg = self.config.get_property('mail')

        try:
            logging.info('Sending Notification via Mail...')

            mail_shooter = MailShooter(
                mail_cfg['sender'],
                mail_cfg['server_host'],
                int(mail_cfg['server_port']),
                mail_cfg['username'],
                mail_cfg['password'],
            )
            mail_shooter.send(mail_cfg['target'], subject, mail_content[0], mail_content[1])
        except BaseException as e:
            logging.error('While sending notification:\n%s', traceback.format_exc(), extra={'exception': e})
            raise e  # to be properly notified via Sentry

    def notify_about_changes_in_moodle(self, changes: List[Course]) -> None:
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

        self._send_mail(f'{diff_count} new Changes in the Moodle courses!', mail_content)

    def notify_about_error(self, error_description: str):
        """
        Sends out an error mail if configured to do so.
        @param error_description: The error object.
        """
        if not self._is_configured():
            return

        mail_cfg = self.config.get_property('mail')

        if not mail_cfg.get('send_error_msg', True):
            return

        mail_content = create_full_error_mail(error_description)
        self._send_mail('Error!', mail_content)

    def notify_about_failed_downloads(self, failed_downloads: List[Task]):
        """
        Sends out an mail with all failed download if configured to send out error messages.
        @param failed_downloads: A list of failed Tasks.
        """
        if not self._is_configured():
            return

        mail_cfg = self.config.get_property('mail')

        if not mail_cfg.get('send_error_msg', True):
            return

        mail_content = create_full_failed_downloads_mail(failed_downloads)
        self._send_mail('Faild to download files!', mail_content)
