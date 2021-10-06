import sqlite3
import logging

from sqlite3 import Error

from moodle_dl.state_recorder.file import File
from moodle_dl.state_recorder.course import Course


class StateRecorder:
    """
    Saves the state and provides utilities to detect changes in the current
    state against the previous.
    """

    def __init__(self, db_file: str):
        """
        Initiates the database.
        If no database exists yet, a new one is created.
        @param db_file: The path to the database
        """
        self.db_file = str(db_file)

        try:
            conn = sqlite3.connect(self.db_file)

            c = conn.cursor()

            sql_create_index_table = """ CREATE TABLE IF NOT EXISTS files (
            course_id integer NOT NULL,
            course_fullname integer NOT NULL,
            module_id integer NOT NULL,
            section_name text NOT NULL,
            module_name text NOT NULL,
            content_filepath text NOT NULL,
            content_filename text NOT NULL,
            content_fileurl text NOT NULL,
            content_filesize integer NOT NULL,
            content_timemodified integer NOT NULL,
            module_modname text NOT NULL,
            content_type text NOT NULL,
            content_isexternalfile text NOT NULL,
            saved_to text NOT NULL,
            time_stamp integer NOT NULL,
            modified integer DEFAULT 0 NOT NULL,
            deleted integer DEFAULT 0 NOT NULL,
            notified integer DEFAULT 0 NOT NULL
            );
            """

            # Create two indices for a faster search.
            sql_create_index = """
            CREATE INDEX IF NOT EXISTS idx_module_id
            ON files (module_id);
            """

            sql_create_index2 = """
            CREATE INDEX IF NOT EXISTS idx_course_id
            ON files (course_id);
            """

            c.execute(sql_create_index_table)
            c.execute(sql_create_index)
            c.execute(sql_create_index2)

            conn.commit()

            current_version = c.execute('pragma user_version').fetchone()[0]

            # Update Table
            if current_version == 0:
                # Add Hash Column
                sql_create_hash_column = """ALTER TABLE files
                ADD COLUMN hash text NULL;
                """
                c.execute(sql_create_hash_column)
                c.execute("PRAGMA user_version = 1;")
                current_version = 1
                conn.commit()

            if current_version == 1:
                # Add moved Column
                sql_create_moved_column = """ALTER TABLE files
                ADD COLUMN moved integer DEFAULT 0 NOT NULL;
                """
                c.execute(sql_create_moved_column)

                c.execute('PRAGMA user_version = 2;')
                current_version = 2
                conn.commit()

            if current_version == 2:
                # Modified gets a new meaning
                sql_remove_modified_entries = """UPDATE files
                    SET modified = 0
                    WHERE modified = 1;
                """
                c.execute(sql_remove_modified_entries)

                c.execute('PRAGMA user_version = 3;')
                current_version = 3

                conn.commit()

            if current_version == 3:
                # Add file_id Column
                sql_create_new_files_table_1 = """
                ALTER TABLE files
                RENAME TO old_files;
                """

                sql_create_new_files_table_2 = """
                CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id integer NOT NULL,
                course_fullname integer NOT NULL,
                module_id integer NOT NULL,
                section_name text NOT NULL,
                module_name text NOT NULL,
                content_filepath text NOT NULL,
                content_filename text NOT NULL,
                content_fileurl text NOT NULL,
                content_filesize integer NOT NULL,
                content_timemodified integer NOT NULL,
                module_modname text NOT NULL,
                content_type text NOT NULL,
                content_isexternalfile text NOT NULL,
                saved_to text NOT NULL,
                hash text NULL,
                time_stamp integer NOT NULL,
                old_file_id integer NULL,
                modified integer DEFAULT 0 NOT NULL,
                moved integer DEFAULT 0 NOT NULL,
                deleted integer DEFAULT 0 NOT NULL,
                notified integer DEFAULT 0 NOT NULL
                );"""

                sql_create_new_files_table_3 = """
                INSERT INTO files
                (course_id, course_fullname, module_id, section_name,
                 module_name, content_filepath, content_filename,
                 content_fileurl, content_filesize, content_timemodified,
                 module_modname, content_type, content_isexternalfile,
                 saved_to, time_stamp, modified, deleted, notified, hash,
                 moved)
                SELECT * FROM old_files
                """

                sql_create_new_files_table_4 = """
                DROP TABLE old_files;
                """
                c.execute(sql_create_new_files_table_1)
                c.execute(sql_create_new_files_table_2)
                c.execute(sql_create_new_files_table_3)
                c.execute(sql_create_new_files_table_4)

                c.execute('PRAGMA user_version = 4;')
                current_version = 4

                conn.commit()

            conn.commit()
            logging.debug('Database Version: %s', str(current_version))

            conn.close()

        except Error as error:
            raise RuntimeError('Could not create database! Error: %s' % (error))

    def __files_have_same_type(self, file1: File, file2: File) -> bool:
        # Returns True if the files have the same type attributes

        if file1.content_type == file2.content_type and file1.module_modname == file2.module_modname:
            return True

        elif (
            file1.content_type == 'description-url'
            and file1.content_type == file2.content_type
            and (
                file1.module_modname.startswith(file2.module_modname)
                or file2.module_modname.startswith(file1.module_modname)
            )
        ):
            # stop redownloading old description urls. Sorry the  module_modname structure has changed
            return True

        return False

    def __files_have_same_path(self, file1: File, file2: File) -> bool:
        # Returns True if the files have the same path attributes

        if (
            file1.module_id == file2.module_id
            and file1.section_name == file2.section_name
            and file1.content_filepath == file2.content_filepath
            and file1.content_filename == file2.content_filename
            and self.__files_have_same_type(file1, file2)
            and (file1.content_type != 'description' or file1.module_name == file2.module_name)
        ):
            return True
        return False

    def __files_are_diffrent(self, file1: File, file2: File) -> bool:
        # Returns True if these files differ from each other

        # Not sure if this would be a good idea
        #  or file1.module_name != file2.module_name)
        if (file1.content_fileurl != file2.content_fileurl or file1.content_filesize != file2.content_filesize) and (
            file1.content_timemodified != file2.content_timemodified
        ):
            return True
        if (
            file1.content_type == 'description'
            and file1.content_type == file2.content_type
            and file1.hash != file2.hash
        ):
            return True

        if (
            file1.content_type == 'description-url'
            and file1.content_type == file2.content_type
            and file1.content_fileurl != file2.content_fileurl
            # One consideration: or file1.section_name != file2.section_name)
            # But useless if description-links in the course must be unique anyway
        ):
            return True
        return False

    def __files_are_moveable(self, file1: File, file2: File) -> bool:
        # Descriptions are not not movable at all
        if file1.content_type != 'description' and file2.content_type != 'description':
            return True
        return False

    def __file_was_moved(self, file1: File, file2: File) -> bool:
        # Returns True if the file was moved to an other path

        if (
            not self.__files_are_diffrent(file1, file2)
            and self.__files_have_same_type(file1, file2)
            and not self.__files_have_same_path(file1, file2)
            and self.__files_are_moveable(file1, file2)
        ):
            return True
        return False

    def __ignore_deleted(self, file: File):
        # Returns true if the deleted file should be ignored.
        if file.module_modname.endswith('forum'):
            return True

        return False

    def get_stored_files(self) -> [Course]:
        # get all stored files (that are not yet deleted)
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        stored_courses = []

        cursor.execute(
            """SELECT course_id, course_fullname
            FROM files WHERE deleted = 0 AND modified = 0 AND moved = 0
            GROUP BY course_id;"""
        )

        curse_rows = cursor.fetchall()

        for course_row in curse_rows:
            course = Course(course_row['course_id'], course_row['course_fullname'])

            cursor.execute(
                """SELECT *
                FROM files
                WHERE deleted = 0
                AND modified = 0
                AND moved = 0
                AND course_id = ?;""",
                (course.id,),
            )

            file_rows = cursor.fetchall()

            course.files = []

            for file_row in file_rows:
                notify_file = File.fromRow(file_row)
                course.files.append(notify_file)

            stored_courses.append(course)

        conn.close()
        return stored_courses

    def __get_modified_files(self, stored_courses: [Course], current_courses: [Course]) -> [Course]:
        # returns courses with modified and deleted files
        changed_courses = []

        for stored_course in stored_courses:

            same_course_in_current = None

            for current_course in current_courses:
                if current_course.id == stored_course.id:
                    same_course_in_current = current_course
                    break

            if same_course_in_current is None:
                # stroed_course does not exist anymore!

                # maybe it would be better
                # to not notify about this changes?
                for stored_file in stored_course.files:
                    stored_file.deleted = True
                    stored_file.notified = False
                changed_courses.append(stored_course)
                # skip the next checks!
                continue

            # there is the same course in the current set
            # so try to find removed files, that are still exist in storage
            # also find modified files
            changed_course = Course(stored_course.id, stored_course.fullname)
            for stored_file in stored_course.files:
                matching_file = None

                for current_file in same_course_in_current.files:
                    # Try to find a matching file with same path
                    if self.__files_have_same_path(current_file, stored_file):
                        matching_file = current_file
                        # file does still exist
                        break

                if matching_file is not None:
                    # An matching file was found
                    # Test for modification
                    if self.__files_are_diffrent(matching_file, stored_file):
                        # file is modified
                        matching_file.modified = True
                        matching_file.old_file = stored_file
                        changed_course.files.append(matching_file)

                    continue

                # No matching file was found --> file was deleted or moved
                # check for moved files

                for current_file in same_course_in_current.files:
                    # Try to find a matching file that was moved
                    if self.__file_was_moved(current_file, stored_file):
                        matching_file = current_file
                        # file does still exist
                        break

                if matching_file is None and not self.__ignore_deleted(stored_file):
                    # No matching file was found --> file was deleted
                    stored_file.deleted = True
                    stored_file.notified = False
                    changed_course.files.append(stored_file)

                elif matching_file is not None:
                    matching_file.moved = True
                    matching_file.old_file = stored_file
                    changed_course.files.append(matching_file)

            if len(changed_course.files) > 0:
                changed_courses.append(changed_course)

        return changed_courses

    def __get_new_files(
        self, changed_courses: [Course], stored_courses: [Course], current_courses: [Course]
    ) -> [Course]:
        # check for new files
        for current_course in current_courses:
            # check if that file does not exist in stored

            same_course_in_stored = None

            for stored_course in stored_courses:
                if stored_course.id == current_course.id:
                    same_course_in_stored = stored_course
                    break

            if same_course_in_stored is None:
                # current_course is not saved yet

                changed_courses.append(current_course)
                # skip the next checks!
                continue

            changed_course = Course(current_course.id, current_course.fullname)
            for current_file in current_course.files:
                matching_file = None

                for stored_file in same_course_in_stored.files:
                    # Try to find a matching file
                    if self.__files_have_same_path(current_file, stored_file) or self.__file_was_moved(
                        current_file, stored_file
                    ):
                        matching_file = current_file
                        break

                if matching_file is None:
                    # current_file is a new file
                    changed_course.files.append(current_file)

            if len(changed_course.files) > 0:
                matched_changed_course = None
                for ch_course in changed_courses:
                    if ch_course.id == changed_course.id:
                        matched_changed_course = ch_course
                        break
                if matched_changed_course is None:
                    changed_courses.append(changed_course)
                else:
                    matched_changed_course.files += changed_course.files
        return changed_courses

    def changes_of_new_version(self, current_courses: [Course]) -> [Course]:
        # all changes are stored inside changed_courses,
        # as a list of changed courses
        changed_courses = []

        # this is kind of bad code ... maybe someone can fix it

        # we need to check if there are files stored that
        # are no longer exists on Moodle => deleted
        # And if there are files that are already existing
        # check if they are modified => modified

        # later check for new files

        # first get all stored files (that are not yet deleted)
        stored_courses = self.get_stored_files()

        changed_courses = self.__get_modified_files(stored_courses, current_courses)
        # ----------------------------------------------------------

        # check for new files
        changed_courses = self.__get_new_files(changed_courses, stored_courses, current_courses)

        return changed_courses

    def get_last_timestamps_per_forum(self) -> {}:
        """Returns a dict of timestamps per forum cmid"""

        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        result_dict = {}

        cursor.execute(
            """SELECT module_id, max(content_timemodified) as content_timemodified
            FROM files WHERE module_modname = 'forum' AND content_type = 'description'
            GROUP BY module_id;"""
        )

        curse_rows = cursor.fetchall()

        for course_row in curse_rows:
            result_dict[course_row['module_id']] = course_row['content_timemodified']

        conn.close()

        return result_dict

    def changes_to_notify(self) -> [Course]:
        changed_courses = []

        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """SELECT course_id, course_fullname
            FROM files WHERE notified = 0 GROUP BY course_id;"""
        )

        curse_rows = cursor.fetchall()

        for course_row in curse_rows:
            course = Course(course_row['course_id'], course_row['course_fullname'])

            cursor.execute(
                """SELECT *
                FROM files WHERE notified = 0 AND course_id = ?;""",
                (course.id,),
            )

            file_rows = cursor.fetchall()

            course.files = []

            for file_row in file_rows:
                notify_file = File.fromRow(file_row)
                if notify_file.modified or notify_file.moved:
                    # add reference to new file

                    cursor.execute(
                        """SELECT *
                        FROM files
                        WHERE old_file_id = ?;""",
                        (notify_file.file_id,),
                    )

                    file_row = cursor.fetchone()
                    if file_row is not None:
                        notify_file.new_file = File.fromRow(file_row)

                course.files.append(notify_file)

            changed_courses.append(course)

        conn.close()
        return changed_courses

    def notified(self, courses: [Course]):
        # saves that a notification with the changes where send

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        for course in courses:
            course_id = course.id

            for file in course.files:
                data = {'course_id': course_id}
                data.update(file.getMap())

                cursor.execute(
                    """UPDATE files
                    SET notified = 1
                    WHERE file_id = :file_id;
                    """,
                    data,
                )

        conn.commit()
        conn.close()

    def save_file(self, file: File, course_id: int, course_fullname: str):
        if file.deleted:
            self.delete_file(file, course_id, course_fullname)
        elif file.modified:
            self.modifie_file(file, course_id, course_fullname)
        elif file.moved:
            self.move_file(file, course_id, course_fullname)
        else:
            self.new_file(file, course_id, course_fullname)

    def new_file(self, file: File, course_id: int, course_fullname: str):
        # saves a file to index

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        data = {'course_id': course_id, 'course_fullname': course_fullname}
        data.update(file.getMap())

        data.update({'modified': 0, 'deleted': 0, 'moved': 0, 'notified': 0})

        cursor.execute(File.INSERT, data)

        conn.commit()
        conn.close()

    def batch_delete_files(self, courses: [Course]):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        for course in courses:
            for file in course.files:
                if file.deleted:
                    data = {'course_id': course.id, 'course_fullname': course.fullname}
                    data.update(file.getMap())

                    cursor.execute(
                        """UPDATE files
                        SET notified = 0, deleted = 1, time_stamp = :time_stamp
                        WHERE file_id = :file_id;
                        """,
                        data,
                    )

        conn.commit()
        conn.close()

    def batch_delete_files_from_db(self, files: [File]):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        for file in files:
            data = {}
            data.update(file.getMap())

            cursor.execute(
                """DELETE FROM files
                WHERE file_id = :file_id
                """,
                data,
            )

        conn.commit()
        conn.close()

    def delete_file(self, file: File, course_id: int, course_fullname: str):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        data = {'course_id': course_id, 'course_fullname': course_fullname}
        data.update(file.getMap())

        cursor.execute(
            """UPDATE files
            SET notified = 0, deleted = 1, time_stamp = :time_stamp
            WHERE file_id = :file_id;
            """,
            data,
        )

        conn.commit()
        conn.close()

    def move_file(self, file: File, course_id: int, course_fullname: str):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        data_new = {'course_id': course_id, 'course_fullname': course_fullname}
        data_new.update(file.getMap())

        if file.old_file is not None:
            # insert a new file,
            # but it is already notified because the same file already exists
            # as moved
            data_new.update(
                {'old_file_id': file.old_file.file_id, 'modified': 0, 'moved': 0, 'deleted': 0, 'notified': 1}
            )
            cursor.execute(File.INSERT, data_new)

            data_old = {'course_id': course_id, 'course_fullname': course_fullname}
            data_old.update(file.old_file.getMap())

            cursor.execute(
                """UPDATE files
            SET notified = 0, moved = 1
            WHERE file_id = :file_id;
            """,
                data_old,
            )
        else:
            # this should never happen, but the old file is not saved in the
            # file descriptor, so we need to inform about the new file
            # notified = 0
            data_new.update({'modified': 0, 'deleted': 0, 'moved': 0, 'notified': 0})
            cursor.execute(File.INSERT, data_new)

        conn.commit()
        conn.close()

    def modifie_file(self, file: File, course_id: int, course_fullname: str):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        data_new = {'course_id': course_id, 'course_fullname': course_fullname}
        data_new.update(file.getMap())

        if file.old_file is not None:
            # insert a new file,
            # but it is already notified because the same file already exists
            # as modified
            data_new.update(
                {'old_file_id': file.old_file.file_id, 'modified': 0, 'moved': 0, 'deleted': 0, 'notified': 1}
            )
            cursor.execute(File.INSERT, data_new)

            data_old = {'course_id': course_id, 'course_fullname': course_fullname}
            data_old.update(file.old_file.getMap())

            cursor.execute(
                """UPDATE files
            SET notified = 0, modified = 1,
            saved_to = :saved_to
            WHERE file_id = :file_id;
            """,
                data_old,
            )
        else:
            # this should never happen, but the old file is not saved in the
            # file descriptor, so we need to inform about the new file
            # notified = 0

            data_new.update({'modified': 0, 'deleted': 0, 'moved': 0, 'notified': 0})
            cursor.execute(File.INSERT, data_new)

        conn.commit()
        conn.close()
