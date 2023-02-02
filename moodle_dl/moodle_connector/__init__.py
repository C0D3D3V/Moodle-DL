from dataclasses import dataclass, field

from moodle_dl.moodle_connector.moodle_service import MoodleService
from moodle_dl.moodle_connector.request_helper import RequestRejectedError, RequestHelper
from moodle_dl.moodle_connector.first_contact_handler import FirstContactHandler

__all__ = ['MoodleService', 'RequestRejectedError', 'RequestHelper', 'FirstContactHandler']


@dataclass
class MoodleURL:
    use_http: bool
    domain: str
    path: str
    scheme: str = field(init=False)
    url_base: str = field(init=False)

    def __post_init__(self):
        if self.use_http:
            self.scheme = 'http://'
        else:
            self.scheme = 'https://'
        self.url_base = self.scheme + self.domain + self.path
