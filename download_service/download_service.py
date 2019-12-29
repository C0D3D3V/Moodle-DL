import urllib.parse as urlparse
from utils.state_recorder import StateRecorder, Course


class DownloadService:
    def __init__(self, job: [Course], state_recorder: StateRecorder):
        self.job = job
        self.state_recorder = state_recorder

    def start(self):
        print("lol")

    def add_token_to_url(url: str, token: str):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)
