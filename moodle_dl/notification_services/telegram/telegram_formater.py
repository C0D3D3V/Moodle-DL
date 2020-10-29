from moodle_dl.state_recorder.course import Course


def create_full_moodle_diff_message(changed_courses: [Course]) -> [str]:
    """
    Creates telegram messages with all changed files. This includes new,
    modified and deleted files. Files that have changed since the last message.

    @param changed_courses: A list of all courses with their modified files.
    @returns a list of messages
    """

    diff_count = 0
    for course in changed_courses:
        diff_count += len(course.files)

    result_list = []
    one_msg_content = '%s new Changes in the Moodle courses!' % (diff_count)

    for course in changed_courses:
        new_line = '\r\n\r\n\r\n> <b>' + course.fullname + '</b>\r\n'
        if len(one_msg_content) + len(new_line) >= 4096:
            result_list.append(one_msg_content)
            one_msg_content = new_line
        else:
            one_msg_content += new_line

        for file in course.files:
            if file.modified:
                new_line = '\r\n<i>* Modified:</i> ' + file.saved_to
            elif file.moved:
                if file.new_file is not None:
                    new_line = '\r\n<i>* Moved:</i> ' + file.new_file.saved_to
                else:
                    new_line = '\r\n<i>* Moved:</i> ' + file.saved_to
            elif file.deleted:
                new_line = '\r\n<i>- Deleted:</i> ' + file.saved_to
            else:
                new_line = '\r\n<i>+ Added:</i> ' + file.saved_to

            if len(one_msg_content) + len(new_line) >= 4096:
                result_list.append(one_msg_content)
                one_msg_content = new_line
            else:
                one_msg_content += new_line

    result_list.append(one_msg_content)
    return result_list


def create_full_error_message(details) -> (str, {str: str}):
    """
    Creates an error message
    """
    return 'The following error occurred during execution:' + details
