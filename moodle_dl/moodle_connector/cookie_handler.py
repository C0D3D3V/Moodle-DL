import sys
import logging

from moodle_dl.moodle_connector.request_helper import RequestHelper, RequestRejectedError


class CookieHandler:
    """
    Fetches and saves the cookies of Moodle.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_autologin_key(self, privatetoken: str) -> {str: str}:

        # do this only if version is greater then 3.2
        # because tool_mobile_get_autologin_key will fail
        if self.version < 2016120500:
            return {}

        print('\rDownloading autologin key\033[K', end='')

        extra_data = {'privatetoken': privatetoken}

        try:
            autologin_key_result = self.request_helper.post_REST('tool_mobile_get_autologin_key', extra_data)
            return autologin_key_result
        except RequestRejectedError as e:
            logging.debug("Cookie lockout: ".format(e))
            return None

    def fetch_cookies(self, privatetoken: str, userid: str):

        autologin_key = self.fetch_autologin_key(privatetoken)

        print('\rDownloading cookies\033[K', end='')

        post_data = {'key': autologin_key.get('key', ''), 'userid': userid}

        cookies_response = self.request_helper.post_URL(autologin_key.get('autologinurl', ''), post_data)

        cookies = cookies_response.getheader('Set-Cookie')

        return cookies
