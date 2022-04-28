from moodle_dl.download_service.path_tools import PathTools


class File:
    def __init__(
        self,
        module_id: int,
        section_name: str,
        section_id: int,
        module_name: str,
        content_filepath: str,
        content_filename: str,
        content_fileurl: str,
        content_filesize: int,
        content_timemodified: int,
        module_modname: str,
        content_type: str,
        content_isexternalfile: bool,
        saved_to: str = '',
        time_stamp: int = 0,
        modified: int = 0,
        moved: int = 0,
        deleted: int = 0,
        notified: int = 0,
        file_hash: str = None,
        file_id: int = None,
        old_file_id: int = None,
    ):

        self.file_id = file_id

        self.module_id = module_id
        self.section_name = section_name
        self.section_id = section_id
        self.module_name = module_name

        self.content_filepath = content_filepath
        self.content_filename = content_filename
        self.content_fileurl = content_fileurl
        self.content_filesize = content_filesize
        self.content_timemodified = int(content_timemodified)

        self.module_modname = module_modname
        self.content_type = content_type

        if isinstance(content_isexternalfile, bool):
            self.content_isexternalfile = content_isexternalfile
        else:
            if content_isexternalfile == 1:
                self.content_isexternalfile = True
            else:
                self.content_isexternalfile = False

        self.saved_to = saved_to

        self.time_stamp = time_stamp

        if modified == 1:
            self.modified = True
        else:
            self.modified = False

        if moved == 1:
            self.moved = True
        else:
            self.moved = False

        if deleted == 1:
            self.deleted = True
        else:
            self.deleted = False

        if notified == 1:
            self.notified = True
        else:
            self.notified = False

        self.hash = file_hash

        # For Textlable
        self.text_content = None

        # For Created HTML-Files like Quizzes
        self.html_content = None

        # To manage the corresponding moved or changed files
        self.old_file = None
        self.new_file = None

        self.old_file_id = old_file_id

    def getMap(self) -> {str: str}:
        return {
            'file_id': self.file_id,
            'module_id': self.module_id,
            'section_name': self.section_name,
            'section_id': self.section_id,
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
            'moved': 1 if self.moved else 0,
            'deleted': 1 if self.deleted else 0,
            'notified': 1 if self.notified else 0,
            'hash': self.hash,
            'old_file_id': self.old_file_id,
        }

    @staticmethod
    def fromRow(row):

        return File(
            file_id=row['file_id'],
            module_id=row['module_id'],
            section_name=row['section_name'],
            section_id=row['section_id'],
            module_name=row['module_name'],
            content_filepath=row['content_filepath'],
            content_filename=row['content_filename'],
            content_fileurl=row['content_fileurl'],
            content_filesize=row['content_filesize'],
            content_timemodified=row['content_timemodified'],
            module_modname=row['module_modname'],
            content_type=row['content_type'],
            content_isexternalfile=row['content_isexternalfile'],
            saved_to=row['saved_to'],
            time_stamp=row['time_stamp'],
            modified=row['modified'],
            moved=row['moved'],
            deleted=row['deleted'],
            notified=row['notified'],
            file_hash=row['hash'],
            old_file_id=row['old_file_id'],
        )

    INSERT = """INSERT INTO files
            (course_id, course_fullname, module_id, section_name, section_id,
            module_name, content_filepath, content_filename,
            content_fileurl, content_filesize, content_timemodified,
            module_modname, content_type, content_isexternalfile,
            saved_to, time_stamp, modified, moved, deleted, notified,
            hash, old_file_id)
            VALUES (:course_id, :course_fullname, :module_id,
            :section_name, :section_id, :module_name, :content_filepath,
            :content_filename, :content_fileurl, :content_filesize,
            :content_timemodified, :module_modname, :content_type,
            :content_isexternalfile, :saved_to, :time_stamp,
            :modified, :moved, :deleted, :notified,  :hash,
            :old_file_id);
            """

    def __str__(self):
        message = 'File ('

        message += f'module_id: {self.module_id}'
        message += f', section_name: "{PathTools.to_valid_name(self.section_name)}"'
        message += f', section_id: "{self.section_id}"'
        message += f', module_name: "{PathTools.to_valid_name(self.module_name)}"'
        message += f', content_filepath: {self.content_filepath}'
        message += f', content_filename: "{PathTools.to_valid_name(self.content_filename)}"'
        message += f', content_fileurl: "{self.content_fileurl}"'
        message += f', content_filesize: {self.content_filesize}'
        message += f', content_timemodified: {self.content_timemodified}'
        message += f', module_modname: {self.module_modname}'
        message += f', content_type: {self.content_type}'
        message += f', content_isexternalfile: {self.content_isexternalfile}'

        message += f', saved_to: "{self.saved_to}"'
        message += f', time_stamp: {self.time_stamp}'
        message += f', modified: {self.modified}'
        message += f', moved: {self.moved}'
        message += f', deleted: {self.deleted}'
        message += f', notified: {self.notified}'
        message += f', hash: {self.hash}'
        message += f', file_id: {self.file_id}'
        message += f', old_file_id: {self.old_file_id}'

        message += ')'
        return message
