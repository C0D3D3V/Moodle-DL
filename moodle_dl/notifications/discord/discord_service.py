import logging
import traceback
from typing import List

from moodle_dl.downloader.task import Task
from moodle_dl.notifications.discord.discord_formatter import DiscordFormatter as DF
from moodle_dl.notifications.discord.discord_shooter import DiscordShooter
from moodle_dl.notifications.notification_service import NotificationService
from moodle_dl.types import Course


class DiscordService(NotificationService):

    def _is_configured(self) -> bool:
        # Checks if the sending of Discord messages has been configured.
        try:
            self.config.get_property('discord')
            return True
        except ValueError:
            logging.debug('Discord webhook notifications not configured, skipping.')
            return False

    def _send_embeds(self, embeds: []):
        """
        Sends a Discord webhook notification
        """
        if not self._is_configured():
            return

        discord_cfg = self.config.get_property('discord')

        logging.info('Sending Notification via Discord webhooks...')

        discord_shooter = DiscordShooter(discord_cfg['webhook_urls'])

        try:
            discord_shooter.send(embeds)
        except BaseException as e:
            logging.error('While sending notification:\n%s', traceback.format_exc(), extra={'exception': e})
            raise e  # to be properly notified via Sentry

    def notify_about_changes_in_moodle(self, changes: [Course]) -> None:
        """
        Sends out a notification about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        if not self._is_configured():
            return

        messages = DF.create_full_moodle_diff_messages(changes, self.config.get_moodle_URL().url_base)

        self._send_embeds(messages)

    def notify_about_error(self, error_description: str) -> None:
        # Not yet implemented
        pass

    def notify_about_failed_downloads(self, failed_downloads: List[Task]) -> None:
        # Not yet implemented
        pass
