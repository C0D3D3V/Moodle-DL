import logging
import os
import platform

from pathlib import Path
from typing import List

from moodle_dl.config import ConfigHelper
from moodle_dl.database import StateRecorder
from moodle_dl.downloader.task import Task
from moodle_dl.types import Course, MoodleDlOpts
from moodle_dl.utils import PathTools as PT


class FakeDownloadService:
    """
    FakeDownloadService fakes a DownloadService.
    This way a local database of Moodle's current files can be created without actually downloading the files.
    """

    def __init__(self, courses: List[Course], config: ConfigHelper, opts: MoodleDlOpts, database: StateRecorder):
        self.courses = courses
        self.opts = opts
        self.config = config
        self.database = database

    def get_failed_tasks(self):
        """
        Return a list of failed downloads.
        No download can fail, so this is only a dummy function.
        """
        return []

    def run(self):
        # delete files, that should be deleted
        self.database.batch_delete_files(self.courses)

        # save files, that should be saved
        for course in self.courses:
            for file in course.files:
                if file.deleted is False:
                    save_destination = Task.gen_path(self.opts.path, course, file)
                    filename = PT.to_valid_name(file.content_filename, is_file=True)

                    if file.content_type == 'description':
                        file.saved_to = str(Path(save_destination) / (filename + '.md'))

                    elif file.content_type == 'html':
                        file.saved_to = str(Path(save_destination) / (filename + '.html'))

                    elif file.module_modname.startswith('url'):
                        file.saved_to = str(Path(save_destination) / (filename + '.desktop'))
                        if os.name == 'nt' or platform.system() == "Darwin":
                            file.saved_to = str(Path(save_destination) / (filename + '.URL'))
                    else:
                        file.saved_to = str(Path(save_destination) / filename)

                    self.database.save_file(file, course.id, course.fullname)

        logging.info('All files stored in the Database!')
