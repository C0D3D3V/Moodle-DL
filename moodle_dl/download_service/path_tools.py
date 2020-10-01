import os
import html

from pathlib import Path


class PathTools:
    """A set of methodes to create correct paths."""

    filename_character_map = {}

    @staticmethod
    def to_valid_name(name: str) -> str:
        """Filtering invalide characters in filenames and paths.

        Args:
            name (str): The string that will go through the filtering

        Returns:
            str: The filtered string, that can be used as a filename.
        """

        if name is None:
            return None

        # Moodle saves the title of a section in HTML-Format,
        # so we need to unescape the string
        try:
            name = html.unescape(name)
        except Exception:
            pass

        # Forward and Backward Slashes are not good for filenames
        for char in PathTools.filename_character_map:
            replacement = PathTools.filename_character_map[char]
            name = name.replace(char, replacement)

        if os.name != 'nt' and '/' not in PathTools.filename_character_map:
            name = name.replace('/', '／')

        if os.name == 'nt' and '\\' not in PathTools.filename_character_map:
            name = name.replace('\\', '／')

        name = name.replace('\n', ' ')
        name = name.replace('\r', ' ')
        name = name.replace('\t', ' ')
        name = name.strip('.')
        name = name.strip()

        return name

    @staticmethod
    def path_of_file_in_module(
        storage_path: str, course_fullname: str, file_section_name: str, file_module_name: str, file_path: str
    ):
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
        path = str(
            Path(storage_path)
            / PathTools.to_valid_name(course_fullname)
            / PathTools.to_valid_name(file_section_name)
            / PathTools.to_valid_name(file_module_name)
            / file_path.strip('/')
        )
        return path

    @staticmethod
    def path_of_file(storage_path: str, course_fullname: str, file_section_name: str, file_path: str):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_section_name: The name of the section where the file
                                  is located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = str(
            Path(storage_path)
            / storage_path
            / PathTools.to_valid_name(course_fullname)
            / PathTools.to_valid_name(file_section_name)
            / file_path.strip('/')
        )
        return path

    @staticmethod
    def flat_path_of_file(storage_path: str, course_fullname: str, file_path: str):
        """
        @param storage_path: The path where all files should be stored.
        @param course_fullname: The name of the course where the file is
                                located.
        @param file_path: The additional path of a file (subdirectory).
        @return: A path where the file should be saved.
        """
        path = str(Path(storage_path) / storage_path / PathTools.to_valid_name(course_fullname) / file_path.strip('/'))
        return path
