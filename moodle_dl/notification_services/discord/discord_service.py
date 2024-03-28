import logging
import traceback


from moodle_dl.utils import cutie
from moodle_dl.utils.logger import Log
from moodle_dl.state_recorder.course import Course
from moodle_dl.notification_services.discord.discord_shooter import DiscordShooter
from moodle_dl.notification_services.notification_service import NotificationService
from moodle_dl.notification_services.discord.discord_formatter import DiscordFormatter as DF


class DiscordService(NotificationService):
    def interactively_configure(self) -> None:
        """
        Guides the user through the configuration of the mail notification.
        """

        do_notify = cutie.prompt_yes_or_no('Do you want to activate notifications via Discord webhooks?')

        if do_notify:
            webhook_urls = input('Discord webhook URLs separated by commas (x,y,z) ')
            webhook_urls = webhook_urls.split(',')

            discord_cfg = {
                'webhook_urls': webhook_urls
            }

            self.config_helper.set_property('discord', discord_cfg)
        else:
            self.config_helper.remove_property('discord')

    def _is_configured(self) -> bool:
        # Checks if the sending of emails has been configured.
        try:
            self.config_helper.get_property('discord')
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

        discord_cfg = self.config_helper.get_property('discord')

        logging.debug('Sending Notification via Discord webhooks...')
        Log.debug('Sending Notification via Discord webhooks... (Please wait)')

        discord_shooter = DiscordShooter(discord_cfg['webhook_urls'])

        try:
            discord_shooter.send(embeds)
        except BaseException as e:
            error_formatted = traceback.format_exc()
            logging.error('While sending notification:\n%s', error_formatted, extra={'exception': e})
            raise e  # to be properly notified via Sentry

    def notify_about_changes_in_moodle(self, changes: [Course]) -> None:
        """
        Sends out a notification about the downloaded changes.
        @param changes: A list of changed courses with changed files.
        """
        if not self._is_configured():
            return

        domain = self.config_helper.get_moodle_domain()
        path = self.config_helper.get_moodle_path()
        messages = DF.create_full_moodle_diff_messages(changes, f"https://{domain}{path}course/view.php")

        self._send_embeds(messages)
