from moodle_dl.state_recorder.file import File
from moodle_dl.download_service.path_tools import PathTools


class Course:
    def __init__(self, _id: int, fullname: str, files: [File] = []):
        """
        Create a new file.

        Args:
            self: (todo): write your description
            _id: (int): write your description
            fullname: (str): write your description
            files: (list): write your description
            File: (str): write your description
        """
        self.id = _id
        self.fullname = fullname
        self.files = files

        self.overwrite_name_with = None
        self.create_directory_structure = True

    def __str__(self):
        """
        Generate a string representation of this message.

        Args:
            self: (todo): write your description
        """
        message = 'Course ('

        message += 'id: %s' % (self.id)
        message += ', fullname: "%s"' % (PathTools.to_valid_name(self.fullname))
        message += ', overwrite_name_with: "%s"' % (PathTools.to_valid_name(self.overwrite_name_with))
        message += ', create_directory_structure: %s' % (self.create_directory_structure)
        message += ', files: %s' % (len(self.files))

        # for i, file in enumerate(self.files):
        #     message += ', file[%i]: %s' % (i, file)

        message += ')'
        return message
