class CollectionOfChanges:
    def __init__(self, changes: {str: [(str, str)]}):
        # changes := {course_name : [(type, file_name)]}
        self.changes = changes
