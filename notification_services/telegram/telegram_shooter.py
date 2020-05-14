import urllib

from http.client import HTTPSConnection


class TelegramShooter:
    """
    Encapsulates the sending of notification-messages.
    """

    stdHeader = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64)' +
                       ' AppleWebKit/537.36 (KHTML, like Gecko)' +
                       ' Chrome/78.0.3904.108 Safari/537.36'),
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    def __init__(self, telegram_token: str, telegram_chatid: str):
        self.telegram_token = telegram_token
        self.telegram_chatid = telegram_chatid

        self.connection = HTTPSConnection("api.telegram.org")

    def send(self, message: str):
        payload = {'chat_id': self.telegram_chatid,
                   'text': message, 'parse_mode': 'HTML'}

        url = '/bot%s/sendMessage' % (self.telegram_token)
        data_urlencoded = urllib.parse.urlencode(payload)

        self.connection.request(
            'POST',
            url,
            body=data_urlencoded,
            headers=self.stdHeader
        )
