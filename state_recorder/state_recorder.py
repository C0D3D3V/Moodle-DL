import sqlite3

from sqlite3 import Error

from state_recorder.file import File
from state_recorder.course import Course


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
        self.db_file = db_file

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
            conn.close()

        except Error as error:
            raise RuntimeError(
                'Could not create database! Error: %s' % (error)
            )

    def __files_have_same_path(self, file1: File, file2: File) -> bool:
        # Returns True if the files have the same path attributes

        if (file1.module_id == file2.module_id and
            file1.section_name == file2.section_name and
            file1.content_filepath == file2.content_filepath and
                file1.content_filename == file2.content_filename):
            return True
        return False

    def __files_are_diffrent(self, file1: File, file2: File) -> bool:
        # Returns True if these files differ from each other

        # Not sure if this would be a good idea
        #  or file1.module_name != file2.module_name)
        if (file1.content_fileurl != file2.content_fileurl or
            file1.content_filesize != file2.content_filesize or
                file1.content_timemodified != file2.content_timemodified):
            return True
        return False

    def __get_stored_files(self) -> [Course]:
        # get all stored files (that are not yet deleted)
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        stored_courses = []

        cursor.execute("""SELECT course_id, course_fullname
            FROM files WHERE deleted = 0 GROUP BY course_id;""")

        curse_rows = cursor.fetchall()

        for course_row in curse_rows:
            course = Course(course_row['course_id'],
                            course_row['course_fullname'], [])

            cursor_inner = conn.cursor()
            cursor_inner.execute("""SELECT *
                FROM files WHERE deleted = 0 AND course_id = ?;""",
                                 (course.id,))

            file_rows = cursor_inner.fetchall()

            course.files = []

            for file_row in file_rows:
                notify_file = File.fromRow(file_row)
                course.files.append(notify_file)

            stored_courses.append(course)

        conn.close()
        return stored_courses

    def __get_modified_files(self, stored_courses: [Course],
                             current_courses: [Course]) -> [Course]:
        # retuns courses with modified and deleted files
        changed_courses = []

        for stored_course in stored_courses:

            same_course_in_current = None

            for current_course in current_courses:
                if (current_course.id == stored_course.id):
                    same_course_in_current = current_course
                    break

            if (same_course_in_current is None):
                # stroed_course does not exist anymore!

                # maybe it would be better
                # to not notify about this changes?
                for stored_file in stored_course.files:
                    stored_file.deleted = True
                    stored_file.notified = False
                changed_courses.append(stored_course)
                # skip the next checks!
                continue

            # there is the same couse in the current set
            # so try to find removed files, that are still exist in storage
            # also find modified files
            changed_course = Course(
                stored_course.id, stored_course.fullname, [])
            for stored_file in stored_course.files:
                matching_file = None

                for current_file in same_course_in_current.files:
                    # Try to find a matching file
                    if(self.__files_have_same_path(current_file, stored_file)):
                        matching_file = current_file
                        break

                if matching_file is None:
                    # No matching file was found --> file was deleted
                    stored_file.deleted = True
                    stored_file.notified = False
                    changed_course.files.append(stored_file)
                else:
                    # An matching file was found
                    # Test for modification
                    if(self.__files_are_diffrent(matching_file, stored_file)):
                        # file ist modified
                        matching_file.modified = True
                        changed_course.files.append(stored_file)

            if (len(changed_course.files) > 0):
                changed_courses.append(changed_course)

        return changed_courses

    def __get_new_files(self, changed_courses: [Course],
                        stored_courses: [Course],
                        current_courses: [Course]) -> [Course]:
        # check for new files
        for current_course in current_courses:
            # check if that file does not exist in stored

            same_course_in_stored = None

            for stored_course in stored_courses:
                if (stored_course.id == current_course.id):
                    same_course_in_stored = stored_course
                    break

            if (same_course_in_stored is None):
                # current_course is not saved yet

                changed_courses.append(current_course)
                # skip the next checks!
                continue

            # Does anyone know why it is necessary to give
            # a course an empty list of files O.o
            # if I don't do this then a course will be created
            # with the files of the previous course
            changed_course = Course(
                current_course.id, current_course.fullname, [])
            for current_file in current_course.files:
                matching_file = None

                for stored_file in same_course_in_stored.files:
                    # Try to find a matching file
                    if(self.__files_have_same_path(current_file, stored_file)):
                        matching_file = current_file
                        break

                if matching_file is None:
                    # current_file is a new file
                    changed_course.files.append(current_file)

            if (len(changed_course.files) > 0):
                matched_changed_course = None
                for ch_course in changed_courses:
                    if (ch_course.id == changed_course.id):
                        matched_changed_course = ch_course
                        break
                if(matched_changed_course is None):
                    changed_courses.append(changed_course)
                else:
                    matched_changed_course.files += changed_course.files
        return changed_courses

    def changes_of_new_version(self, current_courses: [Course]) -> [Course]:
        # The database should only have one entrence for one file,
        # no matter if it is deleted or modified, so is it easier
        # to track changes

        # all changes are stored inside changed_courses,
        # as a list of changed courses
        changed_courses = []

        # this is kind of bad code ... maybe someone can fix it

        # we need to check if there are files stored that
        # are no longer exists on moodle => deleted
        # And if there are files that are already exsisting
        # check if they are modified => modified

        # later check for new files

        # first get all stored files (that are not yet deleted)
        stored_courses = self.__get_stored_files()

        changed_courses = self.__get_modified_files(
            stored_courses, current_courses)
        # ----------------------------------------------------------

        # check for new files
        changed_courses = self.__get_new_files(
            changed_courses, stored_courses, current_courses)

        return changed_courses

    def changes_to_notify(self) -> [Course]:
        changed_courses = []

        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""SELECT course_id, course_fullname
            FROM files WHERE notified = 0 GROUP BY course_id;""")

        curse_rows = cursor.fetchall()

        for course_row in curse_rows:
            course = Course(course_row['course_id'],
                            course_row['course_fullname'], [])

            cursor_inner = conn.cursor()
            cursor_inner.execute("""SELECT *
                FROM files WHERE notified = 0 AND course_id = ?;""",
                                 (course.id,))

            file_rows = cursor_inner.fetchall()

            course.files = []

            for file_row in file_rows:
                notify_file = File.fromRow(file_row)
                course.files.append(notify_file)

            changed_courses.append(course)

        conn.close()
        return changed_courses

    def notified(self, courses: [Course]):
        # saves that a notification with the changes where send

        conn = sqlite3.connect(self.db_file)
        for course in courses:
            course_id = course.id

            for file in course.files:

                data = {'course_id': course_id}
                data.update(file.getMap())

                cursor = conn.cursor()
                cursor.execute("""UPDATE files
                    SET notified = 1
                    WHERE module_id = :module_id AND course_id = :course_id
                    AND notified = 0
                    AND section_name = :section_name
                    AND content_filepath = :content_filepath
                    AND content_filename = :content_filename
                    AND content_fileurl = :content_fileurl
                    AND content_filesize = :content_filesize
                    AND content_timemodified = :content_timemodified;
                    """, data)

        conn.commit()
        conn.close()

    def save_file(self, file: File, course_id: int, course_fullname: str):
        if (file.deleted):
            self.delete_file(file, course_id, course_fullname)
        elif (file.modified):
            self.modifie_file(file, course_id, course_fullname)
        else:
            self.new_file(file, course_id, course_fullname)

    def new_file(self, file: File, course_id: int, course_fullname: str):
        # saves a file to index

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        data = {'course_id': course_id, 'course_fullname': course_fullname}
        data.update(file.getMap())

        cursor.execute("""INSERT INTO files
                    (course_id, course_fullname, module_id, section_name,
                    module_name, content_filepath, content_filename,
                    content_fileurl, content_filesize, content_timemodified,
                    module_modname, content_type, content_isexternalfile,
                    saved_to, time_stamp, modified, deleted, notified)
                    VALUES (:course_id, :course_fullname, :module_id,
                    :section_name, :module_name, :content_filepath,
                    :content_filename, :content_fileurl, :content_filesize,
                    :content_timemodified, :module_modname, :content_type,
                    :content_isexternalfile, :saved_to, :time_stamp,
                    :modified, :deleted, 0);
                    """, data)

        conn.commit()
        conn.close()

    def delete_file(self, file: File, course_id: int, course_fullname: str):
        conn = sqlite3.connect(self.db_file)

        data = {'course_id': course_id, 'course_fullname': course_fullname}
        data.update(file.getMap())

        cursor = conn.cursor()
        cursor.execute("""UPDATE files
            SET notified = 0, deleted = 1, time_stamp = :time_stamp
            WHERE module_id = :module_id AND course_id = :course_id
            AND course_fullname = :course_fullname
            AND section_name = :section_name
            AND content_filepath = :content_filepath
            AND content_filename = :content_filename
            AND content_fileurl = :content_fileurl
            AND content_filesize = :content_filesize
            AND content_timemodified = :content_timemodified;
            """, data)

        conn.commit()
        conn.close()

    def modifie_file(self, file: File, course_id: int, course_fullname: str):
        conn = sqlite3.connect(self.db_file)

        data = {'course_id': course_id, 'course_fullname': course_fullname}
        data.update(file.getMap())

        cursor = conn.cursor()
        cursor.execute("""UPDATE files
            SET notified = 0, modified = 1, time_stamp = :time_stamp,
            saved_to = :saved_to, content_fileurl = :content_fileurl,
            content_filesize = :content_filesize,
            content_timemodified = :content_timemodified,
            module_name = :module_name
            WHERE module_id = :module_id AND course_id = :course_id
            AND course_fullname = :course_fullname
            AND section_name = :section_name
            AND content_filepath = :content_filepath
            AND content_filename = :content_filename;
            """, data)

        conn.commit()
        conn.close()
