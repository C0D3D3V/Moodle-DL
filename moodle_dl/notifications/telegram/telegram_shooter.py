import urllib

from requests.exceptions import RequestException

from moodle_dl.utils import SslHelper


class TelegramShooter:
    RQ_HEADER = {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'
        ),
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(self, telegram_token: str, telegram_chatid: str):
        self.telegram_token = telegram_token
        self.telegram_chatid = telegram_chatid

    def send(self, message: str):
        payload = {'chat_id': self.telegram_chatid, 'text': message, 'parse_mode': 'HTML'}

        url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
        data_urlencoded = urllib.parse.urlencode(payload)

        session = SslHelper.custom_requests_session(skip_cert_verify=False, allow_insecure_ssl=False)
        try:
            response = session.post(url, data=data_urlencoded, headers=self.RQ_HEADER, timeout=60)
        except RequestException as error:
            raise ConnectionError(f"Connection error: {str(error)}") from None

        self._check_errors(response)

    @staticmethod
    def _check_response_code(response):
        # Normally Telegram answer with response 200
        if response.status_code not in [200, 400]:
            raise RuntimeError(
                'An Unexpected Error happened on side of the Telegram System!'
                + f' Status-Code: {str(response.status_code)}'
                + f'\nHeader: {response.headers}'
                + f'\nResponse: {response.text}'
            )

    def _check_errors(self, response) -> object:
        """
        The first time parsing the result of a REST request.
        It is checked for known errors.
        @param response: The JSON response of the Moodle system
        @return: The parsed JSON object
        """

        self._check_response_code(response)

        # Try to parse the JSON
        try:
            response_extracted = response.json()
        except Exception as error:
            raise RuntimeError(
                'An Unexpected Error occurred while trying'
                + ' to parse the json response! Telegram'
                + f' response: {response.read()}.\nError: {error}'
            )
        # Check for known errors
        if "ok" in response_extracted:
            ok = response_extracted.get("ok", False)

            if not ok:
                raise RequestRejectedError(
                    'The Telegram System rejected the Request.'
                    + f" Details: {response_extracted.get('description', 'None')}"
                )

        return response_extracted


class RequestRejectedError(Exception):
    """An Exception which gets thrown if the Telegram-System answered with an
    Error to our Request"""

    pass
