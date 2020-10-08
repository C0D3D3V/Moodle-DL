import os
import logging

from pathlib import Path

from moodle_dl.utils.logger import Log
from moodle_dl.moodle_connector.request_helper import RequestHelper, RequestRejectedError


class CookieHandler:
    """
    Fetches and saves the cookies of Moodle.
    """

    def __init__(self, request_helper: RequestHelper, version: int, storage_path: str):
        self.request_helper = request_helper
        self.version = version
        self.storage_path = storage_path
        self.cookies_path = str(Path(storage_path) / 'Cookies.txt')

        self.moodle_test_url = self.request_helper.url_base

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
            logging.debug("Cookie lockout: %s", e)  # , extra={'exception': e}
            return None

    def test_cookies(self) -> bool:
        """Test if cookies are valide

        Returns:
            bool: True if valide
        """

        logging.debug('Testing cookies with this URL %s', self.moodle_test_url)

        response, session = self.request_helper.get_URL(self.moodle_test_url, self.cookies_path)

        response_text = response.text

        if response_text.find('login/logout.php') >= 0:
            return True
        return False

    def delete_cookie_file(self):
        try:
            os.remove(self.cookies_path)
        except OSError:
            pass

    def check_and_fetch_cookies(self, privatetoken: str, userid: str) -> bool:
        if os.path.exists(self.cookies_path):
            # test if still logged in.

            if self.test_cookies():
                logging.debug('Cookies are still valid')
                return True

            warning_msg = 'Moodle cookie has expired, an attempt is made to generate a new cookie.'
            logging.warning(warning_msg)
            Log.warning('\r' + warning_msg + '\033[K')

        if privatetoken is None:
            error_msg = (
                'Moodle Cookies are not retrieved because no private token is set.'
                + ' To set a private token, use the `--new-token` option (if necessary also with `--sso`).'
            )
            logging.warning(error_msg)
            Log.error('\r' + error_msg + '\033[K')
            self.delete_cookie_file()
            return False

        autologin_key = self.fetch_autologin_key(privatetoken)

        if autologin_key is None:
            error_msg = 'Failed to download autologin key!'
            logging.debug(error_msg)
            print('')
            Log.error(error_msg)
            self.delete_cookie_file()
            return False

        print('\rDownloading cookies\033[K', end='')

        post_data = {'key': autologin_key.get('key', ''), 'userid': userid}
        url = autologin_key.get('autologinurl', '')

        cookies_response, cookies_session = self.request_helper.post_URL(url, post_data, self.cookies_path)

        logging.debug('Autologin redirected to %s', cookies_response.url)

        if self.test_cookies():
            return True
        else:
            error_msg = 'Failed to generate cookies!'
            logging.debug(error_msg)
            print('')
            Log.error(error_msg)
            self.delete_cookie_file()
            return False
