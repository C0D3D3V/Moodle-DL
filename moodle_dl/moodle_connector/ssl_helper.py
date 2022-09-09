import requests
import ssl
import urllib3
"""
A custom helper that fixes OpenSSL incompatibility issues.
See https://stackoverflow.com/a/71646353 for more details.
"""
class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    '''Transport adapter that allows us to use custom ssl_context.'''

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)


def configure_ssl_context(context):
    """
    Customize SSL context to circumvent issues where the client uses
    OpenSSL 3.X.X and the server only supports OpenSSL 1.X.X.
    """
    context.options |= 0x4 # set ssl.OP_LEGACY_SERVER_CONNECT bit (https://bugs.python.org/issue44888)


def custom_session():
    """
    Defines a new session with custom SSL context to support edge cases with OpenSSL 3.X.X
    """
    session = requests.Session()
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    configure_ssl_context(ctx)
    session.mount('https://', CustomHttpAdapter(ctx))
    return session
