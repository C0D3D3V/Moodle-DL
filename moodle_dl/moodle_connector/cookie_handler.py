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

    def test_cookies(self, moodle_url: str, cookie_dic: {}) -> bool:
        """Test if cookies are valide

        Args:
            moodle_url (str): URL to test
            cookie_dic ([type]): cookies

        Returns:
            bool: True if valide
        """
        response, session = self.request_helper.get_URL_WC(moodle_url, cookie_dic)

        response_text = response.text

        if response_text.find('login/logout.php') >= 0:
            return True
        return False

    def fetch_cookies(self, privatetoken: str, userid: str, cookies: {}):
        if cookies is not None:
            # test if still logged in.
            moodle_url = cookies.get('moodle_url', '')
            cookie_dic = cookies.get('dict', {})

            if self.test_cookies(moodle_url, cookie_dic):
                return cookies

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

        cookies_response, cookies_session = self.request_helper.post_URL(
            autologin_key.get('autologinurl', ''), post_data
        )

        cookie_dic = cookies_session.cookies.get_dict()

        moodle_url = cookies_response.url

        result = {'dict': cookie_dic, 'moodle_url': moodle_url}

        if self.test_cookies(moodle_url, cookie_dic):
            return result
        else:
            error_msg = 'Failed to generate cookies!'
            logging.debug(error_msg)
            print('')
            Log.error(error_msg)
            return None
