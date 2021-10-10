import re
import sys
import base64

from http.server import BaseHTTPRequestHandler, HTTPServer

from moodle_dl.utils.logger import Log


class TransferServer(BaseHTTPRequestHandler):
    """
    Transfer server is an HTTP-server that waits for an incoming SSO token.
    """

    received_token = ''

    def do_GET(self):
        if self.path == '/favicon.ico':
            # Don't serve favicon
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            return

        TransferServer.received_token = self.path

        # Token recieved
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(('Moodle Downloader - Token was successfully transferred.').encode('utf-8'))

    def log_message(self, format, *args):
        return


def extract_token(address: str) -> str:
    """
    Extracts a token from a returned URL
    """
    splitted = address.split('token=')

    if len(splitted) < 2:
        return None

    decoded = str(base64.b64decode(splitted[1]))

    splitted = decoded.split(':::')
    if len(splitted) < 2:
        return None

    token = re.sub(r'[^A-Za-z0-9]+', '', splitted[1])

    if len(splitted) < 3:
        return token, None
    else:
        secret_token = re.sub(r'[^A-Za-z0-9]+', '', splitted[2])
        return token, secret_token


def receive_token() -> str:
    """
    Starts an HTTP server to receive the SSO token from browser.
    It waits till a token was received.
    """
    server_address = ('localhost', 80)
    try:
        httpd = HTTPServer(server_address, TransferServer)
    except PermissionError:
        Log.error(
            'Permission denied: Please start the'
            + ' downloader once with administrator rights, so that it'
            + ' can wait on port 80 for the token.'
        )
        sys.exit(1)

    extracted_token = None

    while extracted_token is None:
        httpd.handle_request()

        extracted_token = extract_token(TransferServer.received_token)

    httpd.server_close()

    return extracted_token
