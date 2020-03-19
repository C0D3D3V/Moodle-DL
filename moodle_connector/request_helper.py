import json
import urllib
import ssl
import re
from http.client import HTTPSConnection


class RequestHelper:
    """
    Encapsulates the recurring logic for sending out requests to the
    Moodle-System.
    """

    def __init__(self, moodle_domain: str, moodle_path: str = '/',
                 token: str = '', skip_cert_verify=False):
        """
        Opens a connection to the Moodle system
        """
        if skip_cert_verify:
            context = ssl._create_unverified_context()
        else:
            context = ssl._create_default_https_context()
        self.connection = HTTPSConnection(moodle_domain, context=context)

        self.token = token
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path

        RequestHelper.stdHeader = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)' +
            ' AppleWebKit/537.36 (KHTML, like Gecko)' +
            ' Chrome/78.0.3904.108 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def post_REST(self, function: str, data: {str: str} = None) -> object:
        """
        Sends a POST request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the POST body.
        @return: The JSON response returned by the Moodle system, already
        checked for errors.
        """

        if (self.token is None):
            raise ValueError('The required Token is not set!')

        data_urlencoded = self._get_POST_DATA(function, self.token, data)
        url = self._get_REST_POST_URL(self.moodle_path, function)

        # uncomment this print to debug requested post-urls
        # print(url)

        # uncomment this print to debug posted data
        # print(data_urlencoded)

        self.connection.request(
            'POST',
            url,
            body=data_urlencoded,
            headers=self.stdHeader
        )

        response = self.connection.getresponse()
        return self._initial_parse(response)

    @staticmethod
    def _get_REST_POST_URL(moodle_path: str, function: str) -> str:
        """
        Generates an URL for a REST-POST request
        @params: The necessary parameters for a REST URL
        @return: A formatted URL
        """
        url = (('%swebservice/rest/server.php?moodlewsrestformat=json&' % (
            moodle_path)) + ('wsfunction=%s' % (function)))

        return url

    @staticmethod
    def _get_POST_DATA(function: str, token: str,
                       data_obj: str) -> str:
        """
        Generates the data for a REST-POST request
        @params: The necessary parameters for a REST URL
        @return: A URL-encoded data string
        """
        data = {'moodlewssettingfilter': 'true',
                'moodlewssettingfileurl': 'true'
                }

        if data_obj is not None:
            data.update(data_obj)

        data.update({'wsfunction': function,
                     'wstoken': token})

        return urllib.parse.urlencode(data)

    def get_login(self, data: {str: str}) -> object:
        """
        Sends a POST request to the login endpoint of the Moodle system to
        obtain a token in JSON format.
        @param data: The data is inserted into the Post-Body as arguments. This
        should contain the login data.
        @return: The JSON response returned by the Moodle System, already
        checked for errors.
        """

        self.connection.request(
            'POST',
            '%slogin/token.php' % (
                self.moodle_path),
            body=urllib.parse.urlencode(data),
            headers=self.stdHeader
        )

        response = self.connection.getresponse()
        return self._initial_parse(response)

    @staticmethod
    def _check_response_code(response):
        # Normally Moodle answer with response 200
        if (response.getcode() != 200):
            raise RuntimeError(
                'An Unexpected Error happened on side of the Moodle System!' +
                (' Status-Code: %s' % str(response.getcode())) +
                ('\nHeader: %s' % (response.getheaders())) +
                ('\nResponse: %s' % (response.read())))

    def get_simple_moodle_version(self) -> float:
        """
        Query the version by looking up the change-log (/lib/upgrade.txt)
        of the Moodle
        @param moodle_domain: the domain of the Moodle instance
        @param moodle_path: the path of the Moodle installation
        @return: a float number representing the newest version
                 parsed from the change-log
        """

        self.connection.request(
            'GET',
            '%slib/upgrade.txt' % (
                self.moodle_path),
            headers=self.stdHeader
        )

        response = self.connection.getresponse()

        self._check_response_code(response)

        changelog = str(response.read()).split('\\n')
        version_string = '1'
        for line in changelog:
            match = re.match(r"^===\s*([\d\.]+)\s*===$", line)
            if match:
                version_string = match.group(1)
                break

        majorVersion = version_string.split('.')[0]
        minorVersion = version_string[len(majorVersion):].replace('.', '')

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
            response_extracted = json.loads(response.read())
        except ValueError as error:
            raise RuntimeError('An Unexpected Error occurred while trying' +
                               ' to parse the json response! Moodle' +
                               ' response: %s.\nError: %s' % (
                                   response.read(), error))
        # Check for known errors
        if ("error" in response_extracted):
            error = response_extracted.get("error", "")
            errorcode = response_extracted.get("errorcode", "")
            stacktrace = response_extracted.get("stacktrace", "")
            debuginfo = response_extracted.get("debuginfo", "")
            reproductionlink = response_extracted.get("reproductionlink", "")

            raise RequestRejectedError(
                'The Moodle System rejected the Request.' +
                (' Details: %s (Errorcode: %s, ' % (error, errorcode)) +
                ('Stacktrace: %s, Debuginfo: %s, Reproductionlink: %s)' % (
                    stacktrace, debuginfo, reproductionlink)
                 )
            )

        if ("exception" in response_extracted):
            exception = response_extracted.get("exception", "")
            errorcode = response_extracted.get("errorcode", "")
            message = response_extracted.get("message", "")

            raise RequestRejectedError(
                'The Moodle System rejected the Request.' +
                ' Details: %s (Errorcode: %s, Message: %s)' % (
                    exception, errorcode, message
                )
            )

        return response_extracted


class RequestRejectedError(Exception):
    """An Exception which gets thrown if the Moodle-System answered with an
    Error to our Request"""
    pass
