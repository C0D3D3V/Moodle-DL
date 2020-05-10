import requests


class TelegramShooter:
    """
    Encapsulates the sending of notification-messages.
    """

    def __init__(self, telegram_token: str, telegram_chatid: str):
        self.telegram_token = telegram_token
        self.telegram_chatid = telegram_chatid

    def send(self, message: str):
        payload = {'chat_id': self.telegram_chatid,
                   'text': message, 'parse_mode': 'HTML'}

        request = requests.post('https://api.telegram.org/bot' +
                                self.telegram_token + '/sendMessage',
                                json=payload)
