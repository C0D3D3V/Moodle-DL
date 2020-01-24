from state_recorder.file import File


class Course:
    def __init__(self, _id: int, fullname: str, files: [File] = []):
        self.id = _id
        self.fullname = fullname
        self.files = files

    def __str__(self):
        message = "Course ("

        message += 'id: %s' % (self.id)
        message += ', fullname: %s' % (self.fullname)
        message += ', files: %s' % (len(self.files))

        for i, file in enumerate(self.files):
            message += ', file[%i]: %s' % (i, file)

        message += ")"
        return message
