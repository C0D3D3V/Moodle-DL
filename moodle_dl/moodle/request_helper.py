import asyncio
import json
import logging
import os
import urllib

from time import sleep
from typing import Dict

import aiohttp
import requests

from requests.exceptions import RequestException

from moodle_dl.types import MoodleURL, MoodleDlOpts
from moodle_dl.utils import SslHelper, PathTools as PT, MoodleDLCookieJar


class RequestHelper:
    """
    Functions for sending out requests to the Moodle System.
    """

    RQ_HEADER = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 7.1.1; Moto G Play Build/NPIS26.48-43-2; wv) AppleWebKit/537.36'
            + ' (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 MoodleMobile'
        ),
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    MAX_RETRIES = 5

    def __init__(self, opts: MoodleDlOpts, moodle_url: MoodleURL, token: str = ''):
        self.token = token
        self.moodle_url = moodle_url
        self.opts = opts

        self.url_base = moodle_url.url_base

        # Semaphore for async requests
        # Keep in mind Semaphore needs to be initialized in the same async loop as it is used
        self.semaphore = asyncio.Semaphore(opts.max_parallel_api_calls)

        self.log_responses_to = None
        if opts.log_responses:
            self.log_responses_to = PT.make_path(opts.path, 'responses.log')
            with open(self.log_responses_to, 'w', encoding='utf-8') as response_log_file:
                response_log_file.write('JSON Log:\n\n')

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

        session = SslHelper.custom_requests_session(self.opts.skip_cert_verify, self.opts.allow_insecure_ssl)
        if cookie_jar_path is not None:
            session.cookies = MoodleDLCookieJar(cookie_jar_path)

            if os.path.exists(cookie_jar_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)
        try:
            response = session.post(url, data=data_urlencoded, headers=self.RQ_HEADER, timeout=60)
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

        session = SslHelper.custom_requests_session(self.opts.skip_cert_verify, self.opts.allow_insecure_ssl)
        if cookie_jar_path is not None:
            session.cookies = MoodleDLCookieJar(cookie_jar_path)

            if os.path.exists(cookie_jar_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)
            session.cookies = session.cookies
        try:
            response = session.get(url, headers=self.RQ_HEADER, timeout=60)
        except RequestException as error:
            raise ConnectionError(f"Connection error: {str(error)}") from None

        if cookie_jar_path is not None:
            session.cookies.save(ignore_discard=True, ignore_expires=True)

        return response, session

    async def async_post(self, function: str, data: Dict[str, str] = None, timeout: int = 60) -> Dict:
        """
        Sends async a POST request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the POST body.
        @return: The JSON response returned by the Moodle system, already checked for errors..
        """

        if self.token is None:
            raise ValueError('The required token is not set!')

        data_urlencoded = self._get_POST_DATA(function, self.token, data)
        url = self._get_REST_POST_URL(self.url_base, function)
        ssl_context = SslHelper.get_ssl_context(self.opts.skip_cert_verify, self.opts.allow_insecure_ssl)

        error_ctr = 0
        async with self.semaphore, aiohttp.ClientSession() as session:
            while error_ctr < self.MAX_RETRIES:
                try:
                    async with session.post(
                        url,
                        data=data_urlencoded,
                        headers=self.RQ_HEADER,
                        timeout=timeout,
                        ssl=ssl_context,
                        raise_for_status=True,
                    ) as resp:
                        resp_json = await resp.json()
                        resp_url = resp.url
                    break
                except (aiohttp.client_exceptions.ClientError, OSError, ValueError) as req_err:
                    if (isinstance(req_err, aiohttp.client_exceptions.ClientResponseError)) and (
                        req_err.status not in [408, 409, 429]  # pylint: disable=no-member
                    ):
                        # 408 (timeout) or 409 (conflict) and 429 (too many requests)
                        raise ConnectionError(f"Connection error: {req_err}") from None
                    if isinstance(req_err, aiohttp.client_exceptions.ContentTypeError):
                        raise RequestRejectedError(
                            'The Moodle Mobile API does not appear to be available at this time.'
                        ) from None

                    error_ctr += 1
                    if error_ctr < self.MAX_RETRIES:
                        logging.debug("The %sth connection error occurred, retrying. %s", error_ctr, req_err)
                        asyncio.sleep(1)
                        continue
                    raise ConnectionError(f"Connection error: {req_err}") from None

        self.check_json_for_moodle_error(resp_json)
        self.log_response(function, data, resp_url, resp_json)

        return resp_json

    def post(self, function: str, data: Dict[str, str] = None, timeout: int = 60) -> Dict:
        """
        Sends a POST request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the POST body.
        @return: The JSON response returned by the Moodle system, already checked for errors..
        """

        if self.token is None:
            raise ValueError('The required Token is not set!')

        data_urlencoded = self._get_POST_DATA(function, self.token, data)
        url = self._get_REST_POST_URL(self.url_base, function)

        session = SslHelper.custom_requests_session(self.opts.skip_cert_verify, self.opts.allow_insecure_ssl)
        error_ctr = 0
        while error_ctr <= self.MAX_RETRIES:
            try:
                response = session.post(url, data=data_urlencoded, headers=self.RQ_HEADER, timeout=timeout)
                break
            except (requests.ConnectionError, requests.Timeout) as req_err:
                # We treat requests.ConnectionErrors here specially, since they normally mean,
                # that something went wrong, which could be fixed by a restart.
                error_ctr += 1
                if error_ctr < self.MAX_RETRIES:
                    logging.debug("The %sth Connection Error occurred, retrying. %s", error_ctr, str(req_err))
                    sleep(1)
                    continue
                raise ConnectionError(f"Connection error: {req_err}") from None
            except RequestException as req_err:
                raise ConnectionError(f"Connection error: {req_err}") from None

        json_result = self._initial_parse(response)
        self.log_response(function, data, response.url, json_result)

        return json_result

    def log_response(self, function: str, data: Dict[str, str], url: str, json_result: Dict):
        if self.opts.log_responses and function not in ['tool_mobile_get_autologin_key']:
            with open(self.log_responses_to, 'a', encoding='utf-8') as response_log_file:
                response_log_file.write(f'URL: {url}\n')
                response_log_file.write(f'Function: {function}\n\n')
                response_log_file.write(f'Data: {data}\n\n')
                response_log_file.write(json.dumps(json_result, indent=4, ensure_ascii=False))
                response_log_file.write('\n\n\n')

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
        session = SslHelper.custom_requests_session(self.opts.skip_cert_verify, self.opts.allow_insecure_ssl)
        try:
            response = session.post(
                f'{self.url_base}login/token.php',
                data=urllib.parse.urlencode(data),
                headers=self.RQ_HEADER,
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
            resp_json = response.json()
        except ValueError:
            raise RequestRejectedError('The Moodle Mobile API does not appear to be available at this time.') from None
        except Exception as error:
            raise RequestRejectedError(
                'An Unexpected Error occurred while trying'
                + ' to parse the json response! Moodle'
                + f' response: {response.text}.\nError: {error}'
            ) from None

        self.check_json_for_moodle_error(resp_json)
        return resp_json

    def check_json_for_moodle_error(self, resp_json: Dict):
        # Check for known errors
        if 'error' in resp_json:
            raise RequestRejectedError(
                'The Moodle System rejected the Request.'
                + f" Details: {resp_json.get('error', '')} (Errorcode: {resp_json.get('errorcode', '')},"
                + f" Stacktrace: {resp_json.get('stacktrace', '')}, Debuginfo: {resp_json.get('debuginfo', '')},"
                + f" Reproductionlink: {resp_json.get('reproductionlink', '')})"
            )

        if 'exception' in resp_json:
            errorcode = resp_json.get('errorcode', '')

            if errorcode == 'invalidtoken':
                raise RequestRejectedError(
                    'Your Moodle token has expired.'
                    + ' To create a new one run "moodle-dl -nt -u USERNAME -pw PASSWORD" or "moodle-dl -nt -sso"'
                )

            raise RequestRejectedError(
                'The Moodle System rejected the Request.'
                + f" Details: {resp_json.get('exception', '')} (Errorcode: {errorcode},"
                + f" Message: {resp_json.get('message', '')})"
            )

    @staticmethod
    def recursive_urlencode(data):
        """URL-encode a multidimensional dictionary.
        @param data: the data to be encoded
        @return: the url encoded data
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
