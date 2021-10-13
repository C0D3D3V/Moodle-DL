import html2text

from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget


def append_with_limit(new_line: str, one_msg_content: str, msg_list: [str]):
    """Appends a new line to a message string,
    if the string is to long it ist appended to the message list.
    Returns the new message string.

    Args:
        new_line (str): A new line to append to a message string
        one_msg_content (str): The current message string
        msg_list ([str]): The list of finished messages
    Returns:
        str: The new message
    """
    if len(one_msg_content) + len(new_line) >= 4096:
        msg_list.append(one_msg_content)
        return new_line
    else:
        return one_msg_content + new_line


def create_full_moodle_diff_messages(changed_courses: [Course]) -> [str]:
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
        new_line = '\r\n\r\n\r\n> **' + course.fullname + '**\r\n'
        one_msg_content = append_with_limit(new_line, one_msg_content, result_list)

        for file in course.files:
            saved_to_path = file.saved_to
            if file.new_file is not None:
                saved_to_path = file.new_file.saved_to
            if file.modified:
                new_line = '\r\n🔄 Modified:\r\n ' + saved_to_path
            elif file.moved:
                new_line = '\r\n🔀 Moved:\r\n ' + saved_to_path
            elif file.deleted:
                new_line = '\r\n❌ Deleted:\r\n ' + saved_to_path
            else:
                new_line = '\r\n✅ Added:\r\n ' + saved_to_path

            one_msg_content = append_with_limit(new_line, one_msg_content, result_list)

            if file.content_type == 'description':
                try:
                    with open(saved_to_path, 'r') as description_file:
                        description_lines = description_file.read().splitlines()
                except Exception:
                    description_lines = []

                if len(description_lines) > 0:
                    one_msg_content = append_with_limit('\r\n==>\r\n', one_msg_content, result_list)
                    for new_line in description_lines:
                        new_line = new_line + '\r\n'
                        one_msg_content = append_with_limit(new_line, one_msg_content, result_list)
                    one_msg_content = append_with_limit('<==\r\n', one_msg_content, result_list)

    result_list.append(one_msg_content)
    return result_list


def create_full_error_messages(details) -> [str]:
    """
    Creates error messages
    """
    result_list = []

    one_msg_content = 'The following error occurred during execution:\r\n'
    for new_line in details.splitlines():
        new_line = new_line + '\r\n'
        one_msg_content = append_with_limit(new_line, one_msg_content, result_list)

    result_list.append(one_msg_content)
    return result_list


def create_full_failed_downloads_messages(failed_downloads: [URLTarget]) -> [str]:
    """
    Creates messages with all failed downloads
    """

    result_list = []
    if len(failed_downloads) == 0:
        return result_list

    one_msg_content = (
        'Error while trying to download files, look at the log for more details.\r\nList of failed downloads:\r\n\r\n'
    )
    for url_target in failed_downloads:
        new_line = '__%s:__\r\n%s\r\n\r\n' % (url_target.file.content_filename, url_target.error)
        one_msg_content = append_with_limit(new_line, one_msg_content, result_list)

    result_list.append(one_msg_content)
    return result_list
