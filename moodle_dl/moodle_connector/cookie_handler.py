import sys
import logging

from moodle_dl.utils.logger import Log
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
            return None

        print('\rDownloading autologin key\033[K', end='')

        extra_data = {'privatetoken': privatetoken}

        try:
            autologin_key_result = self.request_helper.post_REST('tool_mobile_get_autologin_key', extra_data)
            return autologin_key_result
        except RequestRejectedError as e:
            logging.debug("Cookie lockout: {}".format(e))  # , extra={'exception': e}
            return None

    def fetch_cookies(self, privatetoken: str, userid: str, cookies: {}):
        if cookies is not None:
            return cookies

        if privatetoken is None:
            error_msg = 'Moodle Cookies are not retrieved because no private token is set. To set a private token, use the `--new-token` option.'
            logging.warning(error_msg)
            Log.error('\r' + error_msg + '\033[K')
            return None

        autologin_key = self.fetch_autologin_key(privatetoken)

        if autologin_key is None:
            error_msg = 'Failed to download autologin key!'
            logging.debug(error_msg)
            print('')
            Log.error(error_msg)
            return None

        print('\rDownloading cookies\033[K', end='')

        post_data = {'key': autologin_key.get('key', ''), 'userid': userid}

        cookies_response = self.request_helper.post_URL(autologin_key.get('autologinurl', ''), post_data)

        response_text = cookies_response.read()

        cookies = cookies_response.getheader('Set-Cookie')

        moodle_url = cookies_response.getheader('Location')

        result = {'cookies': cookies, 'moodle_url': moodle_url}

        return result
