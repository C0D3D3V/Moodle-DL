import json
from typing import Dict, List

from requests.exceptions import RequestException

from moodle_dl.utils import SslHelper


class DiscordShooter:
    RQ_HEADER = {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'
        ),
        'Content-Type': 'application/json',
    }

    def __init__(self, discord_webhooks: List[str]):
        self.discord_webhooks = discord_webhooks

    def send_msg(self, text):
        self.send_data(
            {
                'content': text,
                'username': 'Moodle Notifications',
                'avatar_url': 'https://i.imgur.com/J3Pxl41.png',
            }
        )

    def send(self, embeds: List):
        self.send_data(
            {
                'embeds': embeds,
                'username': 'Moodle Notifications',
                'avatar_url': 'https://i.imgur.com/J3Pxl41.png',
            }
        )

    def send_data(self, data: Dict):

        session = SslHelper.custom_requests_session(skip_cert_verify=False, allow_insecure_ssl=False)
        for webhook_url in self.discord_webhooks:
            try:
                response = session.post(webhook_url, data=json.dumps(data), headers=self.RQ_HEADER, timeout=60)
                self._check_response_code(response)
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
