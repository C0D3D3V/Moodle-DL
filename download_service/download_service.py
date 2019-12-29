import os
import time
import html

import urllib.parse as urlparse

from moodle_connector.moodle_service import MoodleService
from utils.state_recorder import Course


class DownloadService:
    def __init__(self, job: [Course], moodle_service: MoodleService,
                 storage_path: str):
        self.job = job
        self.moodle_service = moodle_service
        self.state_recorder = moodle_service.recorder
        self.token = moodle_service.get_token()
        self.storage_path = storage_path

    def start(self):
        for course in self.job:
            course_id = course.id
            course_fullname = course.fullname
            for file in course.files:
                download_url = self.add_token_to_url(file.content_fileurl)
                download_path = os.path.join(
                    self.to_valid_name(course_fullname), self.to_valid_name(
                        file.section_name), file.content_filepath.strip('/'),
                    file.content_filename)

                time_stamp = int(time.time())

                file.saved_to = download_path
                file.time_stamp = time_stamp
                print(download_url)

                self.state_recorder.save_file(file, course_id, course_fullname)



    def add_token_to_url(self, url: str):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update({'token': self.token})
        url_parts[4] = urlparse.urlencode(query)
        return urlparse.urlunparse(url_parts)

    def to_valid_name(self, name: str):
        name = html.unescape(name)
        name = name.replace('/', '|')
        name = name.replace('\\', '|')
        return name
