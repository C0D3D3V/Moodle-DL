import os
import html


class StringTools:

    @staticmethod
    def to_valid_name(name: str) -> str:
        """
        @param name: The String that should be filtered
        @return: A filtered String, that can be used as a filename.
        """

        # Moodle saves the titel of a section in HTML-Format,
        # so we need to unescape the string

        name = html.unescape(name)
        # Forward and Backward Slashes are not good for filenames
        name = name.replace(os.path.sep, '|')
        return name

    @staticmethod
    def path_of_file_in_module(storage_path: str, course_fullname: str,
                               file_section_name: str, file_module_name: str,
                               file_path: str):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_section_name: The name of the section where the file
                                  is located.
        @param file_module_name: The name of the module where the file
                                 is located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = os.path.join(
            storage_path,
            StringTools.to_valid_name(course_fullname),
            StringTools.to_valid_name(file_section_name),
            StringTools.to_valid_name(file_module_name),
            file_path.strip('/'))
        return path

    @staticmethod
    def path_of_file(storage_path: str, course_fullname: str,
                     file_section_name: str, file_path: str):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_section_name: The name of the section where the file
                                  is located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = os.path.join(
            storage_path,
            StringTools.to_valid_name(course_fullname),
            StringTools.to_valid_name(file_section_name),
            file_path.strip('/'))
        return path
