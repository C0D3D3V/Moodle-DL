import urllib
import json
from http.client import HTTPSConnection


class RequestHelper:
    """
    Encapsulates the recurring logic for sending out requests to the
    Moodle-System.
    """

    def __init__(self, moodle_domain: str, moodle_path: str = '/',
                 token: str = ''):
        self.connection = HTTPSConnection(moodle_domain)
        self.token = token
        self.moodle_domain = moodle_domain
        self.moodle_path = moodle_path
        self.stdHeader = {
            # 'Cookie': 'cookie1=' + cookie1,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'
            # copied straight out of Chrome
        }

    def get_REST(self, function: str, data: {str: str} = None) -> object:
        """
        Sends a GET request to the REST endpoint of the Moodle system
        @param function: The Web service function to be called.
        @param data: The optional data is added to the GET URL as arguments.
        @return: The Json response returned by the Moodle system, already
        checked for errors.
        """

        if (self.token is None):
            raise ValueError('The required Token is not set!')

        if (data is not None):
            data_enc = "&%s" % (urllib.parse.urlencode(data))
        else:
            data_enc = ''

        # uncomment this print to debug requested links
        # print('%swebservice/rest/server.php?wsfunction=%s&moodlewsrestformat=json&wstoken=%s%s' % (
         #   self.moodle_path, function, self.token, data_enc))

        self.connection.request(
            'GET',
            '%swebservice/rest/server.php?wsfunction=%s&moodlewsrestformat=json&wstoken=%s%s' % (
                self.moodle_path, function, self.token, data_enc
            ),
            headers=self.stdHeader
        )

        response = self.connection.getresponse()
        return self._initial_parse(response)

    def get_login(self, data: {str: str}) -> object:
        """
        Sends a GET request to the login endpoint of the Moodle system to
        obtain a token in Json format.
        @param data: The data is inserted into the GET-URL as arguments. This
        should contain the logon data.
        @return: The json response returned by the Moodle System, already
        checked for errors.
        """

        self.connection.request(
            'GET',
            '%slogin/token.php?%s' % (
                self.moodle_path, urllib.parse.urlencode(data)
            ),
            headers=self.stdHeader
        )

        response = self.connection.getresponse()
        return self._initial_parse(response)

    def _initial_parse(self, response) -> object:
        if (response.getcode() != 200):
            raise RuntimeError(
                'An Unexpected Error happened on side of the Moodle System!')

        try:
            response_extracted = json.loads(response.read())
        except ValueError as error:
            raise RuntimeError('An Unexpected Error occurred while trying to parse the json response! Moodle response: %s. Error: %s' % (
                response.read(), error))

        if ("error" in response_extracted):
            error = response_extracted.get("error", "")
            errorcode = response_extracted.get("errorcode", "")
            stacktrace = response_extracted.get("stacktrace", "")
            debuginfo = response_extracted.get("debuginfo", "")
            reproductionlink = response_extracted.get("reproductionlink", "")

            raise RequestRejectedError(
                'The Moodle System rejected the Request. Details: %s (Errorcode: %s, Stacktrace: %s, Debuginfo: %s, Reproductionlink: %s)' % (
                    error, errorcode, stacktrace, debuginfo, reproductionlink
                )
            )

        if ("exception" in response_extracted):
            exception = response_extracted.get("exception", "")
            errorcode = response_extracted.get("errorcode", "")
            message = response_extracted.get("message", "")

            raise RequestRejectedError(
                'The Moodle System rejected the Request. Details: %s (Errorcode: %s, Message: %s)' % (
                    exception, errorcode, message
                )
            )

        return response_extracted


class RequestRejectedError(Exception):
    """An Exception which gets thrown if the Moodle-System answered with an
    Error to our Request"""
    pass
