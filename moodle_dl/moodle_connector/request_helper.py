import json
import logging
import os
import urllib

from http.cookiejar import MozillaCookieJar
from time import sleep
from typing import Dict

import requests
import urllib3

from requests.exceptions import RequestException

from moodle_dl.utils import SslHelper, PathTools as PT


class RequestHelper:
    """
    Functions for sending out requests to the Moodle System.
    """

    stdHeader = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 7.1.1; Moto G Play Build/NPIS26.48-43-2; wv) AppleWebKit/537.36'
            + ' (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 MoodleMobile'
        ),
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(self, opts, use_http: bool, moodle_domain: str, moodle_path: str = '/', token: str = ''):
        self.token = token
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path
        self.use_http = use_http
        self.opts = opts

        # Make sure to either set stream to False or read the content property of the Response object
        self.session = SslHelper.custom_requests_session(opts.skip_cert_verify, opts.allow_insecure_ssl)

        scheme = 'https://'
        if use_http:
            scheme = 'http://'
        self.url_base = scheme + moodle_domain + moodle_path

        self.log_responses_to = None
        if opts.log_responses:
            self.log_responses_to = PT.make_path(opts.path, 'responses.log')
            with open(self.log_responses_to, 'w', encoding='utf-8') as response_log_file:
                response_log_file.write('JSON Log:\n\n')

        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        urllib3.disable_warnings()

    def post_URL(self, url: str, data: Dict[str, str] = None, cookie_jar_path: str = None):
        """
        Sends a POST request to a specific URL, including saving of cookies in cookie jar.
        @param url: The url to which the request is sent. (the moodle base url is not added to the given URL)
        @param data: The optional data is added to the POST body.
        @param cookie_jar_path: Path to the cookies file.
        @return: The resulting response object and the session object.
        """

        data_urlencoded = ""
        if data is not None:
            data_urlencoded = RequestHelper.recursive_urlencode(data)

        session = SslHelper.custom_requests_session(self.verify)

        if cookie_jar_path is not None:
            session.cookies = MozillaCookieJar(cookie_jar_path)

            if os.path.exists(cookie_jar_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)

        try:
            response = session.post(url, data=data_urlencoded, headers=self.stdHeader, timeout=60)
        except RequestException as error:
            raise ConnectionError(f"Connection error: {str(error)}") from None

        if cookie_jar_path is not None:
            for cookie in session.cookies:
                cookie.expires = 2147483647

            session.cookies.save(ignore_discard=True, ignore_expires=True)

        return response, session

    def get_URL(self, url: str, cookie_jar_path: str = None):
        """
        Sends a GET request to a specific URL of the Moodle system, including additional cookies
        (cookies are updated after the request)
        @param url: The url to which the request is sent. (the moodle base url is not added to the given URL)
        @param cookie_jar_path: The optional cookies to add to the request
        @return: The resulting Response object.
        """

        session = SslHelper.custom_requests_session(self.verify)

        if cookie_jar_path is not None:
            session.cookies = MozillaCookieJar(cookie_jar_path)

            if os.path.exists(cookie_jar_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)
        try:
            response = session.get(url, headers=self.stdHeader, timeout=60)
        except RequestException as error:
            raise ConnectionError(f"Connection error: {str(error)}") from None

        if cookie_jar_path is not None:
            session.cookies.save(ignore_discard=True, ignore_expires=True)

        return response, session

    async def async_post(self):
        pass

    def post(self, function: str, data: Dict[str, str] = None, timeout: str = 60) -> object:
        """
        Sends a POST request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the POST body.
        @return: The JSON response returned by the Moodle system, already
        checked for errors..
        """

        if self.token is None:
            raise ValueError('The required Token is not set!')

        data_urlencoded = self._get_POST_DATA(function, self.token, data)
        url = self._get_REST_POST_URL(self.url_base, function)

        error_ctr = 0
        max_retries = 5
        session = SslHelper.custom_requests_session(self.verify)
        while True:
            try:
                response = session.post(url, data=data_urlencoded, headers=self.stdHeader, timeout=timeout)
                break
            except (requests.ConnectionError, requests.Timeout) as error:
                # We treat requests.ConnectionErrors here specially, since they normally mean,
                # that something went wrong, which could be fixed by a restart.
                error_ctr += 1
                if error_ctr < max_retries:
                    logging.debug("The %sth Connection Error occurred, retrying. %s", error_ctr, str(error))
                    sleep(1)
                    continue
                raise ConnectionError(f"Connection error: {error}") from None
            except RequestException as error:
                raise ConnectionError(f"Connection error: {error}") from None

        json_result = self._initial_parse(response)
        if self.opts.log_responses and function not in ['tool_mobile_get_autologin_key']:
            with open(self.log_responses_to, 'a', encoding='utf-8') as response_log_file:
                response_log_file.write(f'URL: {response.url}\n')
                response_log_file.write(f'Function: {function}\n\n')
                response_log_file.write(f'Data: {data}\n\n')
                response_log_file.write(json.dumps(json_result, indent=4, ensure_ascii=False))
                response_log_file.write('\n\n\n')

        return json_result

    @staticmethod
    def _get_REST_POST_URL(url_base: str, function: str) -> str:
        """
        Generates an URL for a REST-POST request
        @params: The necessary parameters for a REST URL
        @return: A formatted URL
        """
        url = f'{url_base}webservice/rest/server.php?moodlewsrestformat=json&wsfunction={function}'

        return url

    @staticmethod
    def _get_POST_DATA(function: str, token: str, data_obj: str) -> str:
        """
        Generates the data for a REST-POST request
        @params: The necessary parameters for a REST URL
        @return: A URL-encoded data string
        """
        data = {'moodlewssettingfilter': 'true', 'moodlewssettingfileurl': 'true'}

        if data_obj is not None:
            data.update(data_obj)

        data.update({'wsfunction': function, 'wstoken': token})

        return RequestHelper.recursive_urlencode(data)

    def get_login(self, data: Dict[str, str]) -> object:
        """
        Sends a POST request to the login endpoint of the Moodle system to
        obtain a token in JSON format.
        @param data: The data is inserted into the Post-Body as arguments. This
        should contain the login data.
        @return: The JSON response returned by the Moodle System, already
        checked for errors.
        """
        session = SslHelper.custom_requests_session(self.verify)
        try:
            response = session.post(
                f'{self.url_base}login/token.php',
                data=urllib.parse.urlencode(data),
                headers=self.stdHeader,
                timeout=60,
            )
        except RequestException as error:
            raise ConnectionError(f"Connection error: {str(error)}") from None

        return self._initial_parse(response)

    @staticmethod
    def _check_response_code(response):
        # Normally Moodle answer with response 200
        if response.status_code != 200:
            raise RequestRejectedError(
                'An Unexpected Error happened on side of the Moodle System!'
                + f' Status-Code: {str(response.status_code)}'
                + f'\nHeader: {response.headers}'
                + f'\nResponse: {response.text}'
            )

    def _initial_parse(self, response) -> object:
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
        except ValueError:
            raise RequestRejectedError('The Moodle Mobile API does not appear to be available at this time.') from None
        except Exception as error:
            raise RequestRejectedError(
                'An Unexpected Error occurred while trying'
                + ' to parse the json response! Moodle'
                + f' response: {response.text}.\nError: {error}'
            ) from None
        # Check for known errors
        if 'error' in response_extracted:
            error = response_extracted.get('error', '')
            errorcode = response_extracted.get('errorcode', '')
            stacktrace = response_extracted.get('stacktrace', '')
            debuginfo = response_extracted.get('debuginfo', '')
            reproductionlink = response_extracted.get('reproductionlink', '')

            raise RequestRejectedError(
                'The Moodle System rejected the Request.'
                + f' Details: {error} (Errorcode: {errorcode}, '
                + f'Stacktrace: {stacktrace}, Debuginfo: {debuginfo}, Reproductionlink: {reproductionlink})'
            )

        if 'exception' in response_extracted:
            exception = response_extracted.get('exception', '')
            errorcode = response_extracted.get('errorcode', '')
            message = response_extracted.get('message', '')

            if errorcode == 'invalidtoken':
                raise RequestRejectedError(
                    'Your Moodle token has expired.'
                    + ' To create a new one run "moodle-dl -nt -u USERNAME -pw PASSWORD" or "moodle-dl -nt -sso"'
                )

            raise RequestRejectedError(
                'The Moodle System rejected the Request.'
                + f' Details: {exception} (Errorcode: {errorcode}, Message: {message})'
            )

        return response_extracted

    @staticmethod
    def recursive_urlencode(data):
        """URL-encode a multidimensional dictionary.
        @param data: the data to be encoded
        @returns: the url encoded data
        """

        def recursion(data, base=None):
            if base is None:
                base = []
            pairs = []

            for key, value in data.items():
                new_base = base + [key]
                if hasattr(value, 'values'):
                    pairs += recursion(value, new_base)
                else:
                    new_pair = None
                    if len(new_base) > 1:
                        first = urllib.parse.quote(new_base.pop(0))
                        rest = map(urllib.parse.quote, new_base)
                        new_pair = f"{first}[{']['.join(rest)}]={urllib.parse.quote(str(value))}"
                    else:
                        new_pair = f'{urllib.parse.quote(str(key))}={urllib.parse.quote(str(value))}'
                    pairs.append(new_pair)
            return pairs

        return '&'.join(recursion(data))


class RequestRejectedError(Exception):
    """An Exception which gets thrown if the Moodle-System answered with an
    Error to our Request"""

    pass
