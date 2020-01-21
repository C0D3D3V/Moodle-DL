class File:
    def __init__(self, module_id: int, section_name: str, module_name: str,
                 content_filepath: str, content_filename: str,
                 content_fileurl: str, content_filesize: int,
                 content_timemodified: int, module_modname: str,
                 content_type: str, content_isexternalfile: bool,
                 saved_to: str = "", time_stamp: int = 0,
                 modified: bool = False, deleted: bool = False,
                 notified: bool = False):

        self.module_id = module_id
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
            'module_id': self.module_id,
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
            module_id=row['module_id'],
            section_name=row['section_name'],
            module_name=row['module_name'],
            content_filepath=row['content_filepath'],
            content_filename=row['content_filename'],
            content_fileurl=row['content_fileurl'],
            content_filesize=row['content_filesize'],
            content_timemodified=row['content_timemodified'],
            module_modname=row['module_modname'],
            content_type=row['content_type'],
            content_isexternalfile=False if (
                row['content_isexternalfile'] == 0) else True,

            saved_to=row['saved_to'],
            time_stamp=row['time_stamp'],
            modified=False if row['modified'] == 0 else True,
            deleted=False if row['deleted'] == 0 else True,
            notified=False if row['notified'] == 0 else True
        )

    def __str__(self):
        message = "File ("

        message += 'module_id: %s' % (self.module_id)
        message += ', section_name: %s' % (self.section_name)
        message += ', module_name: %s' % (self.module_name)
        message += ', content_filepath: %s' % (self.content_filepath)
        message += ', content_filename: %s' % (self.content_filename)
        message += ', content_fileurl: %s' % (self.content_fileurl)
        message += ', content_filesize: %s' % (self.content_filesize)
        message += ', content_timemodified: %s' % (self.content_timemodified)
        message += ', module_modname: %s' % (self.module_modname)
        message += ', content_isexternalfile: %s' % (
            self.content_isexternalfile)

        message += ', saved_to: %s' % (self.saved_to)
        message += ', time_stamp: %s' % (self.time_stamp)
        message += ', modified: %s' % (self.modified)
        message += ', deleted: %s' % (self.deleted)
        message += ', notified: %s' % (self.notified)

        message += ")"
        return message
