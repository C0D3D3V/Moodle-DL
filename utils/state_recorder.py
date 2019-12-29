import sqlite3
from sqlite3 import Error


class File:
    def __init__(self, content_id: int, section_name: str, module_name: str,
                 content_filepath: str, content_filename: str,
                 content_fileurl: str, content_filesize: int,
                 content_timemodified: int, module_modname: str,
                 content_type: str, content_isexternalfile: bool,
                 saved_to: str = "", time_stamp: int = 0,
                 modified: bool = False, deleted: bool = False,
                 notified: bool = False):

        self.content_id = content_id
        self.section_name = section_name
        self.module_name = module_name
        self.content_filepath = content_filepath
        self.content_filename = content_filename
        self.content_fileurl = content_fileurl
        self.content_filesize = content_filesize
        self.content_timemodified = content_timemodified
        self.module_modname = module_modname
        self.content_type = content_type
        self.content_isexternalfile = content_isexternalfile

        self.saved_to = saved_to
        self.time_stamp = time_stamp
        self.modified = modified
        self.deleted = deleted
        self.notified = notified

    def getMap(self) -> {str: str}:
        return {
            'content_id': self.content_id,
            'section_name': self.section_name,
            'module_name': self.module_name,
            'content_filepath': self.content_filepath,
            'content_filename': self.content_filename,
            'content_fileurl': self.content_fileurl,
            'content_filesize': self.content_filesize,
            'content_timemodified': self.content_timemodified,
            'module_modname': self.module_modname,
            'content_type': self.content_type,
            'content_isexternalfile': 1 if self.content_isexternalfile else 0,
            'saved_to': self.saved_to,
            'time_stamp': self.time_stamp,
            'modified': 1 if self.modified else 0,
            'deleted': 1 if self.deleted else 0,
            'notified': 1 if self.notified else 0,
        }

    def fromRow(row):
        return File(
            content_id=row['content_id'],
            section_name=row['section_name'],
            module_name=row['module_name'],
            content_filepath=row['content_filepath'],
            content_filename=row['content_filename'],
            content_fileurl=row['content_fileurl'],
            content_filesize=row['content_filesize'],
            content_timemodified=row['content_timemodified'],
            module_modname=row['module_modname'],
            content_type=row['content_type'],
            content_isexternalfile=False if row['content_isexternalfile'] == 0 else True,
            saved_to=row['saved_to'],
            time_stamp=row['time_stamp'],
            modified=False if row['modified'] == 0 else True,
            deleted=False if row['deleted'] == 0 else True,
            notified=False if row['notified'] == 0 else True
        )


class Course:
    def __init__(self, id: int, fullname: str, files: [File] = []):
        self.id = id
        self.fullname = fullname
        self.files = files


class StateRecorder:
    """
    Saves the state and provides utilities to detect changes in the current
    state against the previous.
    """

    def __init__(self, db_file: str):
        self.db_file = db_file

        try:
            conn = sqlite3.connect(self.db_file)

            c = conn.cursor()

            sql_create_index_table = """ CREATE TABLE IF NOT EXISTS files (
            course_id integer NOT NULL,
            course_fullname integer NOT NULL,
            content_id integer NOT NULL,
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

            sql_create_index = """
            CREATE INDEX IF NOT EXISTS idx_content_id
            ON files (content_id);
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

    def __does_file_already_exist(self, file: File, course_id: int,
                                  cursor) -> bool:
        # Returns True if the file is already in the Database BUT as
        # a different version

        data = {'course_id': course_id}
        data.update(file.getMap())

        cursor.execute("""SELECT saved_to FROM files WHERE content_id = :content_id
            AND course_id = :course_id AND section_name = :section_name
            AND content_filepath = :content_filepath
            AND content_filename = :content_filename
            AND content_fileurl = :content_fileurl
            AND content_filesize = :content_filesize""",
                       data)

        row = cursor.fetchone()
        if row is None:
            return False
        return True

    def __is_file_modified(self, file: File, course_id: int, cursor) -> bool:
        # Returns True if there is a file already in the database with the
        # same id but different content

        data = {'course_id': course_id}
        data.update(file.getMap())

        cursor.execute("""SELECT saved_to FROM files WHERE content_id = :content_id
            AND course_id = :course_id AND (section_name != :section_name
            OR content_filepath != :content_filepath
            OR content_filename != :content_filename
            OR content_fileurl != :content_fileurl
            OR content_filesize != :content_filesize)""",
                       data)

        row = cursor.fetchone()
        if row is None:
            return False
        return True

    def changes_of_new_version(self, courses: [Course]) -> [Course]:
        changed_courses = []

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Get ids to delete
        to_delete_ids = []
        for course in courses:
            list_of_ids = []
            course_id = course.id
            list_of_ids.append(course_id)
            for file in course.files:
                list_of_ids.append(file.content_id)

            sql = """SELECT content_id FROM files WHERE deleted = 0
            AND course_id = ? AND content_id NOT IN ({})""".format(
                ','.join('?' * (len(list_of_ids) - 1)))
            result_deleted = cursor.execute(sql, list_of_ids).fetchall()
            to_delete_ids += [x[0] for x in result_deleted]

        for course in courses:
            changed_course = Course(course.id, course.fullname)
            for file in course.files:
                changed_file = file

                if (file.content_id in to_delete_ids):
                    # Detect Deleted Files
                    changed_file.deleted = True
                    changed_course.files.append(changed_file)

                elif (not self.__does_file_already_exist(changed_file,
                                                         changed_course.id,
                                                         cursor)):
                    if (self.__is_file_modified(changed_file,
                                                changed_course.id, cursor)):
                        # Detect Modified Files
                        changed_file.modified = True
                        changed_course.files.append(changed_file)
                    else:
                        # Detect Added Files
                        changed_course.files.append(changed_file)

            if len(changed_course.files) > 0:
                changed_courses.append(changed_course)

        conn.close()
        return changed_courses

    def changes_to_notify(self) -> [Course]:
        changed_courses = []

        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""SELECT course_id, course_fullname
            FROM files WHERE notified = 0 GROUP BY course_id""")

        curse_rows = cursor.fetchall()

        for curs_row in curse_rows:
            course = Course(curs_row['course_id'], curs_row['course_fullname'])

            cursor.execute("""SELECT *
                FROM files WHERE notified = 0 AND course_id = ?""",
                           (course.id,))

            file_rows = cursor.fetchall()

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
        cursor = conn.cursor()

        for course in courses:
            course_id = course.id

            for file in course.files:

                data = {'course_id': course_id}
                data.update(file.getMap())

                cursor.execute("""UPDATE files
                    SET notified = 1
                    WHERE content_id = :content_id AND course_id = :course_id
                    AND notified = 0
                    AND section_name = :section_name
                    AND content_filepath = :content_filepath
                    AND content_filename = :content_filename
                    AND content_fileurl = :content_fileurl
                    AND content_filesize = :content_filesize
                    AND time_stamp = :time_stamp
                    """, data)

        conn.commit()
        conn.close()

    def save_file(self, file: File, course_id: int, course_fullname: str):
        # saves a file to index

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        data = {'course_id': course_id, 'course_fullname': course_fullname}
        data.update(file.getMap())

        cursor.execute("""INSERT INTO files
                    (course_id, course_fullname, content_id, section_name,
                    module_name, content_filepath, content_filename,
                    content_fileurl, content_filesize, content_timemodified,
                    module_modname, content_type, content_isexternalfile,
                    saved_to, time_stamp, modified, notified)
                    VALUES (:course_id, :course_fullname, :content_id,
                    :section_name, :module_name, :content_filepath,
                    :content_filename, :content_fileurl, :content_filesize,
                    :content_timemodified, :module_modname, :content_type,
                    :content_isexternalfile, :saved_to, :time_stamp,
                    :modified, :notified)
                    """, data)

        conn.commit()
        conn.close()
