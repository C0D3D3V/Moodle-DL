from typing import List

import requests
import json

from requests.exceptions import RequestException


class DiscordShooter:
    """
    Encapsulates the sending of notification-messages.
    """

    def __init__(self, discord_webhooks: List[str]):
        self.discord_webhooks = discord_webhooks

    def send(self, embeds):
        data = {
            'embeds': embeds,
            'username': 'Moodle Notifications',
            'avatar_url': 'https://i.imgur.com/J3Pxl41.png'
        }

        try:
            for webhook_url in self.discord_webhooks:
                requests.post(webhook_url,
                              data=json.dumps(data),
                              headers={'Content-Type': 'application/json'}
                              )
        except requests.exceptions.HTTPError as error:
            raise SystemExit(error)
        except RequestException as error:
            raise ConnectionError(f"Connection error: {str(error)}") from None

    @staticmethod
    def _check_response_code(response):
        # Normally Discord answers with response 204
        if response.status_code not in [200, 204, 400]:
            raise RuntimeError(
                'An unexpected error happened on'
                + " Discord's servers."
                + f' Status code: {str(response.status_code)}'
                + f'\nHeader: {response.headers}'
                + f'\nResponse: {response.text}'
            )
