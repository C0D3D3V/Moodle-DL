from typing import List

from moodle_dl.state_recorder import File
from moodle_dl.utils import PathTools as PT


class Course:
    def __init__(self, _id: int, fullname: str, files: List[File] = None):
        self.id = _id
        self.fullname = PT.to_valid_name(fullname)
        if files is not None:
            self.files = files
        else:
            self.files = []

        self.overwrite_name_with = None
        self.create_directory_structure = True
        self.excluded_sections = []

    def __str__(self):
        message = 'Course ('

        message += f'id: {self.id}'
        message += f', fullname: "{self.fullname}"'
        message += f', overwrite_name_with: "{PT.to_valid_name(self.overwrite_name_with)}"'
        message += f', create_directory_structure: {self.create_directory_structure}'
        message += f', files: {len(self.files)}'
        message += ')'
        return message
