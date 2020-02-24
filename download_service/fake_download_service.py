import os

from utils.logger import Log
from state_recorder.course import Course
from utils.string_tools import StringTools
from moodle_connector.moodle_service import MoodleService


class FakeDownloadService:
    """
    FakeDownloadService fakes a DownloadService.
    This way a local database of Moodle's current files
    can be created without actually downloading the files.
    """

    def __init__(self, courses: [Course], moodle_service: MoodleService,
                 storage_path: str):
        """
        Initiates the FakeDownloadService with all files that
        need to be downloaded (saved in the database).
        @param courses: A list of courses that contains all modified files.
        @param moodle_service: A reference to the moodle_service, currently
                               only to get to the state_recorder.
        @param storage_path: The location where the files would be saved.
        """

        self.courses = courses
        self.state_recorder = moodle_service.recorder
        self.storage_path = storage_path

        # delete files, that should be deleted
        self.state_recorder.batch_delete_files(self.courses)

        # Prepopulate queue with any files that were given
        for course in self.courses:
            for file in course.files:
                if(file.deleted is False):

                    save_destination = StringTools.path_of_file(
                        self.storage_path, course.fullname,
                        file.section_name,
                        file.content_filepath
                    )

                    # If the file is located in a folder or in an assignment,
                    # it should be saved in a subfolder
                    # (with the name of the module).
                    if (file.module_modname == "assign" or
                            file.module_modname == "folder"):
                        file_path = file.content_filepath
                        if (file.content_type == "submission_file"):
                            file_path = os.path.join('/submissions/',
                                                     file_path.strip('/'))

                        save_destination = StringTools.path_of_file_in_module(
                            self.storage_path, course.fullname,
                            file.section_name, file.module_name,
                            file_path
                        )

                    filename = StringTools.to_valid_name(file.content_filename)

                    file.saved_to = os.path.join(save_destination,
                                                 filename)

                    if (file.module_modname == 'url'):
                        file.saved_to = os.path.join(
                            save_destination, filename + ".desktop")
                        if os.name == "nt":
                            file.saved_to = os.path.join(
                                save_destination, filename + ".URL")

                    self.state_recorder.save_file(
                        file, course.id, course.fullname)

    def run(self):
        Log.success('All files stored in the Database!')
