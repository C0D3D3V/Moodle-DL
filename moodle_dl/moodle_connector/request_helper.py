import re
import ssl
import json
import urllib
import certifi
import requests
import logging


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

    def __init__(self, moodle_domain: str, moodle_path: str = '/', token: str = '', skip_cert_verify=False):
        self.token = token
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path

        self.verify = not skip_cert_verify
        self.url_base = 'https://' + moodle_domain + moodle_path

        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def post_URL(self, url: str, data: {str: str} = None):
        """
        Sends a POST request to a specific URL 
        @param url: The url to which the request is sent. (the moodle base url is not added to the given URL)
        @param data: The optional data is added to the POST body.
        @return: The resulting response object and the session object.
        """

        data_urlencoded = ""
        if data is not None:
            data_urlencoded = RequestHelper.recursive_urlencode(data)

        session = requests.Session()
        response = session.post(url, data=data_urlencoded, headers=self.stdHeader, verify=self.verify)
        return response, session

    def get_URL_WC(self, url: str, cookie_dic: {str: str} = None):
        """
        Sends a GET request to a specific URL of the Moodle system, including additional cookies
        @param url: The url to which the request is sent. (the moodle base url is not added to the given URL)
        @param cookie_dic: The optional cookies to add to the request
        @return: The resulting Response object.
        """

        session = requests.Session()
        response = session.get(url, headers=self.stdHeader, cookies=cookie_dic, verify=self.verify)
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

        response = requests.post(url, data=data_urlencoded, headers=self.stdHeader, verify=self.verify)

        return self._initial_parse(response)

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

        response = requests.post(
            '%slogin/token.php' % (self.url_base),
            data=urllib.parse.urlencode(data),
            headers=self.stdHeader,
            verify=self.verify,
        )

        return self._initial_parse(response)

    @staticmethod
    def _check_response_code(response):
        # Normally Moodle answer with response 200
        if response.status_code != 200:
            raise RuntimeError(
                'An Unexpected Error happened on side of the Moodle System!'
                + (' Status-Code: %s' % str(response.getcode()))
                + ('\nHeader: %s' % (response.getheaders()))
                + ('\nResponse: %s' % (response.read()))
            )

    def get_simple_moodle_version(self) -> float:
        """
        Query the version by looking up the change-log (/lib/upgrade.txt)
        of the Moodle
        @return: a float number representing the newest version
                 parsed from the change-log
        """

        self.connection.request('GET', '%slib/upgrade.txt' % (self.moodle_path), headers=self.stdHeader)

        response = self.connection.getresponse()

        self._check_response_code(response)

        changelog = str(response.read()).split('\\n')
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
        except Exception as error:
            raise RuntimeError(
                'An Unexpected Error occurred while trying'
                + ' to parse the json response! Moodle'
                + ' response: %s.\nError: %s' % (response.read(), error)
            )
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
