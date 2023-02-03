import logging
import os
import platform

from pathlib import Path
from typing import List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.download_service.download_service import DownloadService
from moodle_dl.state_recorder.state_recorder import StateRecorder
from moodle_dl.types import Course
from moodle_dl.utils import PathTools as PT


class FakeDownloadService:
    """
    FakeDownloadService fakes a DownloadService.
    This way a local database of Moodle's current files can be created without actually downloading the files.
    """

    def __init__(self, courses: List[Course], config: ConfigHelper, opts):
        """
        Initiates the FakeDownloadService with all files that need to be saved in the database
        @param courses: A list of courses that contains all modified files
        @param config: Config helper
        @param opts: Moodle-dl options
        """
        self.courses = courses
        self.opts = opts
        self.config = config
        self.state_recorder = StateRecorder(opts)

        # delete files, that should be deleted
        self.state_recorder.batch_delete_files(self.courses)

        # save files, that should be saved
        for course in self.courses:
            for file in course.files:
                if file.deleted is False:
                    save_destination = DownloadService.gen_path(opts.path, course, file)

                    filename = PT.to_valid_name(file.content_filename)

                    file.saved_to = str(Path(save_destination) / filename)

                    if file.content_type == 'description':
                        file.saved_to = str(Path(save_destination) / (filename + '.md'))

                    elif file.content_type == 'html':
                        file.saved_to = str(Path(save_destination) / (filename + '.html'))

                    elif file.module_modname.startswith('url'):
                        file.saved_to = str(Path(save_destination) / (filename + '.desktop'))
                        if os.name == 'nt' or platform.system() == "Darwin":
                            file.saved_to = str(Path(save_destination) / (filename + '.URL'))

                    self.state_recorder.save_file(file, course.id, course.fullname)

    def get_failed_url_targets(self):
        """
        Return a list of failed Downloads, as a list of URLTargets.
        No download can fail, so this is only a dummy function.
        """
        return []

    def run(self):
        """Dummy function"""
        logging.info('All files stored in the Database!')
