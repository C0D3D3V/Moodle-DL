import base64
import urllib.parse as urlparse

from utils.logger import Log
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer


class TransferServer(BaseHTTPRequestHandler):
    """
    Transfer server is an http-server that waits for an incoming sso token.
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
        self.wfile.write(("Moodle Downloader - " +
                          "Token was successfully transferred."
                          ).encode('utf-8'))

    def log_message(self, format, *args):
        return


def receiver_token() -> str:
    """
    Starts an http server to recieve the sso token from browser.
    It waits till a token was received.
    """
    server_address = ('localhost', 80)
    try:
        httpd = HTTPServer(server_address, TransferServer)
    except PermissionError:
        Log.error('Permission denied: Please start the' +
                  ' downloader once with admin rights, so that it' +
                  ' can wait on port 80 for the token.')
        exit(1)

    extracted_token = None

    while extracted_token is None:
        httpd.handle_request()

        splitted = TransferServer.received_token.split('token=')

        if (len(splitted) < 2):
            continue

        extracted_token = splitted[1]

    httpd.server_close()

    decoded = str(base64.b64decode(extracted_token))

    splitted = decoded.split(':::')
    if (len(splitted) < 2):
        raise ValueError('Invalide Token: ' + extracted_token)

    return splitted[1]
