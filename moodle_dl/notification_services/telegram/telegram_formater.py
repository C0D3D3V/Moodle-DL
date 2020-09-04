from moodle_dl.state_recorder.course import Course


def create_full_moodle_diff_message(changed_courses: [Course]) -> str:
    """
    Creates an telegram message with all changed files. This includes new,
    modified and deleted files. Files that have changed since the last message.
    There is a maximum of characters for this message.
    @param changed_courses: A list of all courses with their modified files.
    """
    full_content = ''

    for course in changed_courses:
        full_content += '\r\n> <b>' + course.fullname + '</b>'
        for file in course.files:
            if len(full_content) > 2000:
                return full_content + '\r\n\r\n<b>...and more changes. But it is to much text for this message.</b>'
            if file.modified:
                full_content += '\r\n* Modified: ' + file.content_filename
            elif file.moved:
                if file.new_file is not None:
                    full_content += '\r\n* Moved: ' + file.new_file.content_filename
                else:
                    full_content += '\r\n* Moved: ' + file.content_filename
            elif file.deleted:
                full_content += '\r\n- Deleted: ' + file.content_filename
            else:
                full_content += '\r\n+ Added: ' + file.content_filename

    return full_content


def create_full_error_message(details) -> (str, {str: str}):
    """
    Creates an error message
    """
    return 'The following error occurred during execution:' + details
