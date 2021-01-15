import re
import os
import json
import urllib
import urllib3
import requests
import logging

from http.cookiejar import MozillaCookieJar
from requests.exceptions import RequestException


class RequestHelper:
    """
    Encapsulates the recurring logic for sending out requests to the
    Moodle-System.
    """

    stdHeader = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 7.1.1; Moto G Play Build/NPIS26.48-43-2; wv) AppleWebKit/537.36'
            + ' (KHTML, like Gecko) Version/4.0 Chrome/71.0.3578.99 Mobile Safari/537.36 MoodleMobile'
        ),
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    def __init__(
        self,
        moodle_domain: str,
        moodle_path: str = '/',
        token: str = '',
        skip_cert_verify: bool = False,
        log_responses_to: str = None,
    ):
        self.token = token
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path

        self.verify = not skip_cert_verify
        self.url_base = 'https://' + moodle_domain + moodle_path

        self.log_responses_to = log_responses_to
        self.log_responses = False

        if log_responses_to is not None:
            self.log_responses = True
            with open(self.log_responses_to, 'w') as response_log_file:
                response_log_file.write('JSON Log:\n\n')

        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        urllib3.disable_warnings()
        # logging.captureWarnings(True)

    def post_URL(self, url: str, data: {str: str} = None, cookie_jar_path: str = None):
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

        session = requests.Session()

        if cookie_jar_path is not None:
            session.cookies = MozillaCookieJar(cookie_jar_path)

            if os.path.exists(cookie_jar_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)

        try:
            response = session.post(url, data=data_urlencoded, headers=self.stdHeader, verify=self.verify, timeout=60)
        except RequestException as error:
            raise ConnectionError("Connection error: %s" % str(error)) from None

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

        session = requests.Session()

        if cookie_jar_path is not None:
            session.cookies = MozillaCookieJar(cookie_jar_path)

            if os.path.exists(cookie_jar_path):
                session.cookies.load(ignore_discard=True, ignore_expires=True)
        try:
            response = session.get(url, headers=self.stdHeader, verify=self.verify, timeout=60)
        except RequestException as error:
            raise ConnectionError("Connection error: %s" % str(error)) from None

        if cookie_jar_path is not None:
            session.cookies.save(ignore_discard=True, ignore_expires=True)

        return response, session

    def post_REST(self, function: str, data: {str: str} = None) -> object:
        """
        Sends a POST request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the POST body.
        @return: The JSON response returned by the Moodle system, already
        checked for errors.
        """

        if self.token is None:
            raise ValueError('The required Token is not set!')

        data_urlencoded = self._get_POST_DATA(function, self.token, data)
        url = self._get_REST_POST_URL(self.url_base, function)

        try:
            response = requests.post(url, data=data_urlencoded, headers=self.stdHeader, verify=self.verify, timeout=60)
        except RequestException as error:
            raise ConnectionError("Connection error: %s" % str(error)) from None

        json_result = self._initial_parse(response)
        if self.log_responses and function not in ['tool_mobile_get_autologin_key']:
            with open(self.log_responses_to, 'a') as response_log_file:
                response_log_file.write('URL: {}\n'.format(response.url))
                response_log_file.write('Function: {}\n\n'.format(function))
                response_log_file.write('Data: {}\n\n'.format(data))
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
        url = '%swebservice/rest/server.php?moodlewsrestformat=json&wsfunction=%s' % (url_base, function)

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

    def get_login(self, data: {str: str}) -> object:
        """
        Sends a POST request to the login endpoint of the Moodle system to
        obtain a token in JSON format.
        @param data: The data is inserted into the Post-Body as arguments. This
        should contain the login data.
        @return: The JSON response returned by the Moodle System, already
        checked for errors.
        """
        try:
            response = requests.post(
                '%slogin/token.php' % (self.url_base),
                data=urllib.parse.urlencode(data),
                headers=self.stdHeader,
                verify=self.verify,
                timeout=60,
            )
        except RequestException as error:
            raise ConnectionError("Connection error: %s" % str(error)) from None

        return self._initial_parse(response)

    @staticmethod
    def _check_response_code(response):
        # Normally Moodle answer with response 200
        if response.status_code != 200:
            raise RequestRejectedError(
                'An Unexpected Error happened on side of the Moodle System!'
                + (' Status-Code: %s' % str(response.status_code))
                + ('\nHeader: %s' % response.headers)
                + ('\nResponse: %s' % response.text)
            )

    def get_simple_moodle_version(self) -> float:
        """
        Query the version by looking up the change-log (/lib/upgrade.txt)
        of the Moodle
        @return: a float number representing the newest version
                 parsed from the change-log
        """

        url = '%slib/upgrade.txt' % (self.url_base)
        try:
            response = requests.get(url, headers=self.stdHeader, verify=self.verify, timeout=60)
        except RequestException as error:
            raise ConnectionError("Connection error: %s" % str(error)) from None

        self._check_response_code(response)

        changelog = str(response.text).split('\n')
        version_string = '1'
        for line in changelog:
            match = re.match(r'^===\s*([\d\.]+)\s*===$', line)
            if match:
                version_string = match.group(1)
                break

        majorVersion = version_string.split('.')[0]
        minorVersion = version_string[len(majorVersion) :].replace('.', '')

        version = float(majorVersion + '.' + minorVersion)
        return version

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
        except ValueError as error:
            raise RequestRejectedError('The Moodle Mobile API does not appear to be available at this time.') from None
        except Exception as error:
            raise RequestRejectedError(
                'An Unexpected Error occurred while trying'
                + ' to parse the json response! Moodle'
                + ' response: %s.\nError: %s' % (response.text, error)
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
                + (' Details: %s (Errorcode: %s, ' % (error, errorcode))
                + ('Stacktrace: %s, Debuginfo: %s, Reproductionlink: %s)' % (stacktrace, debuginfo, reproductionlink))
            )

        if 'exception' in response_extracted:
            exception = response_extracted.get('exception', '')
            errorcode = response_extracted.get('errorcode', '')
            message = response_extracted.get('message', '')

            if errorcode == 'invalidtoken':
                raise RequestRejectedError(
                    'Your Moodle token has expired. To create a new one run "moodle-dl -nt -u USERNAME -pw PASSWORD"'
                )

            raise RequestRejectedError(
                'The Moodle System rejected the Request.'
                + ' Details: %s (Errorcode: %s, Message: %s)' % (exception, errorcode, message)
            )

        return response_extracted

    @staticmethod
    def recursive_urlencode(data):
        """URL-encode a multidimensional dictionary.
        @param data: the data to be encoded
        @returns: the url encoded data
        """

        def recursion(data, base=[]):
            pairs = []

            for key, value in data.items():
                new_base = base + [key]
                if hasattr(value, 'values'):
                    pairs += recursion(value, new_base)
                else:
                    new_pair = None
                    if len(new_base) > 1:
                        first = urllib.parse.quote(new_base.pop(0))
                        rest = map(lambda x: urllib.parse.quote(x), new_base)
                        new_pair = '%s[%s]=%s' % (first, ']['.join(rest), urllib.parse.quote(str(value)))
                    else:
                        new_pair = '%s=%s' % (urllib.parse.quote(str(key)), urllib.parse.quote(str(value)))
                    pairs.append(new_pair)
            return pairs

        return '&'.join(recursion(data))


class RequestRejectedError(Exception):
    """An Exception which gets thrown if the Moodle-System answered with an
    Error to our Request"""

    pass
