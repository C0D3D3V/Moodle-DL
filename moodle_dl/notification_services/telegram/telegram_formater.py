from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget


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
        if len(one_msg_content) + len(new_line) >= 4096:
            result_list.append(one_msg_content)
            one_msg_content = new_line
        else:
            one_msg_content += new_line

        for file in course.files:
            if file.modified:
                new_line = '\r\n__* Modified:__ ' + file.saved_to
            elif file.moved:
                if file.new_file is not None:
                    new_line = '\r\n__* Moved:__ ' + file.new_file.saved_to
                else:
                    new_line = '\r\n__* Moved:__ ' + file.saved_to
            elif file.deleted:
                new_line = '\r\n__- Deleted:__ ' + file.saved_to
            else:
                new_line = '\r\n__+ Added:__ ' + file.saved_to

            if len(one_msg_content) + len(new_line) >= 4096:
                result_list.append(one_msg_content)
                one_msg_content = new_line
            else:
                one_msg_content += new_line

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
        if len(one_msg_content) + len(new_line) >= 4096:
            result_list.append(one_msg_content)
            one_msg_content = new_line
        else:
            one_msg_content += new_line

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
        if len(one_msg_content) + len(new_line) >= 4096:
            result_list.append(one_msg_content)
            one_msg_content = new_line
        else:
            one_msg_content += new_line

    result_list.append(one_msg_content)
    return result_list
