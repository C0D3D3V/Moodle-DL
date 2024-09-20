import logging
import traceback
from typing import List

import moodle_dl.notifications.ntfy.ntfy_formatter as NF
from moodle_dl.downloader.task import Task
from moodle_dl.notifications.notification_service import NotificationService
from moodle_dl.notifications.ntfy.ntfy_shooter import NtfyShooter
from moodle_dl.types import Course


class NtfyService(NotificationService):
    def _is_configured(self) -> bool:
        # Checks if the sending of ntfy messages has been configured.
        try:
            self.config.get_property("ntfy")
            return True
        except ValueError:
            logging.debug("ntfy-Notifications not configured, skipping.")
            return False

    def _send_messages(self, messages: List[str]):
        """
        Sends an message
        """
        if not self._is_configured() or messages is None or len(messages) == 0:
            return

        ntfy_cfg = self.config.get_property("ntfy")

        logging.info("Sending Notification via ntfy...")
        ntfy_shooter = NtfyShooter(ntfy_cfg["topic"], ntfy_cfg.get("server"))

        for message in messages:
            try:
                ntfy_shooter.send(**message)
            except BaseException as e:
                logging.error(
                    "While sending notification:\n%s",
                    traceback.format_exc(),
                    extra={"exception": e},
                )
                raise e  # to be properly notified via Sentry

    def notify_about_changes_in_moodle(self, changes: List[Course]) -> None:
        """
        Sends out a notification about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        if not self._is_configured():
            return

        messages = NF.create_full_moodle_diff_messages(changes)

        self._send_messages(messages)

    def notify_about_error(self, error_description: str):
        """
        Sends out an error message if configured to do so.
        @param error_description: The error object.
        """
        pass

    def notify_about_failed_downloads(self, failed_downloads: List[Task]):
        """
        Sends out an message about failed download if configured to send out error messages.
        @param failed_downloads: A list of failed Tasks.
        """
        pass
