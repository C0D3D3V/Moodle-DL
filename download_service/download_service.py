import urllib.parse as urlparse
from moodle_connector.moodle_service import MoodleService
from utils.state_recorder import Course


class DownloadService:
    def __init__(self, job: [Course], moodle_service: MoodleService):
        self.job = job
        self.moodle_service = moodle_service
        self.state_recorder = moodle_service.recorder
        self.token = moodle_service.get_token()

    def start(self):
        for course in self.job:
            for file in course.files:
                print("Download " +
                      self.add_token_to_url(file.content_fileurl))

    def add_token_to_url(self, url: str):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': self.token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)
