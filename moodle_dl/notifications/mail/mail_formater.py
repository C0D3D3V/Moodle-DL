# coding=utf-8

from string import Template
from email.utils import make_msgid

from moodle_dl.types import Course
from moodle_dl.downloader.task import Task

main_wrapper = Template(
    '''
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head></head>
    <body style="padding: 17px; background-color: #fefefe;
    font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
    sans-serif;">
        <div style="background-color: #ffffff; border: 1px solid #dfdede;">
            <table border-spacing="0" cellspacing="0" cellpadding="0"
            border="0" style="margin-bottom: 17px; width: 100%;
            border-spacing: 0;">
                <tbody><tr>
                    <td style="vertical-align: middle; width: 400px;
                    padding: 0; margin: 0;">
                        <img src="cid:${header_cid}" style="height: 70px;"/>
                    </td>
                    <td style="vertical-align: middle; width: auto;
                    padding: 0; margin: 0;">
                        <img src="cid:${extender_cid}" style="height: 70px;
                        width: 100%;"/>
                    </td>
                </tr></tbody>
            </table>

            <div style="margin: 20px; margin-bottom: 0;">
                <p>${introduction_text}</p>

                ${content}
            </div>
        </div>
    </body>
</html>
'''
)

error_message_box = Template(
    '''
    <table style="width: 100%; background-color: #ff3860; color: #fff;
    margin-bottom: 15px;">
        <tr>
            <td style="font-family: 'Segoe UI', 'Calibri', 'Lucida Grande',
            Arial, sans-serif; padding: 15px; padding-top: 7px;
            padding-bottom: 7px;">
                    ${details}
            </td>
        </tr>
    </table>
'''
)

failed_downloads_message_box = Template(
    '''
    <table style="width: 100%; margin-bottom: 15px;">
        <thead style="heigth: 0"><tr>
            <th style="width: 100%;"/>
        </tr></thead>
        ${list_entries}
    </table>
'''
)
failed_downloads_list_entry_box = Template(
    '''
    <tr>
        <td style="padding: 15px; padding-top: 7px; padding-bottom: 7px; color: #2b3033; font-size: 16px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif; ">
            ${file_name}
        </td>
    </tr>
    <tr>
        <td style="padding: 15px; padding-top: 7px; padding-bottom: 7px; font-size: 14px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif; background-color: #ff3860; color: #fff;">
            ${error_msg}
        </td>
    </tr>
'''
)

info_message_box = Template(
    '''
    <table style="width: 100%; background-color: #23d160; color: #fff;
    margin-bottom: 15px; padding: 10px;">
        <tr>
            <td style="font-family: 'Segoe UI', 'Calibri', 'Lucida Grande',
            Arial, sans-serif; padding: 15px; padding-top: 7px;
            padding-bottom: 7px;">
                <p>
                    ${text}
                </p>
            </td>
        </tr>
    </table>
'''
)

moodle_main_box = Template(
    '''
    <p style="padding-bottom: 10px; color: #7d878d; font-size: 20px;
    font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
    sans-serif;">
            ${course_name}
    </p>
    <table style="width: 100%;">
        <thead style="heigth: 0"><tr>
            <td style="width: 17px"/>
            <td style="width: auto"/>
        </tr></thead>
        <tbody>
            ${content}
        </tbody>
    </table>
'''
)

"""
Optional open Moodle Link
            <tr style="height: 50px">
                <td colspan="2">
                    <a style="border: 1px solid #e2001a;
                    border-radius: 3px; padding: 3px;
                    padding-left: 5px; padding-right: 7px;
                    color: #e2001a; text-decoration: none !important;"
                        target="_blank"
                        href="${moodle_link}">
                                <span style="text-decoration: none !important;
                                font-family: 'Segoe UI', 'Calibri',
                                'Lucida Grande', Arial, sans-serif;">
                                Open Moodle »</span>
                    </a>
                </td>
            </tr>
"""

moodle_added_box = Template(
    '''
    <tr>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 14px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            +
        </td>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 16px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            ${file_name}
        </td>
    </tr>
'''
)

moodle_modified_box = Template(
    '''
    <tr>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 14px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            ≠
        </td>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 16px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            ${file_name}
        </td>
    </tr>
'''
)

moodle_moved_box = Template(
    '''
    <tr>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 14px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            <->
        </td>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 16px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            ${file_name}
        </td>
    </tr>
'''
)

moodle_deleted_box = Template(
    '''
    <tr>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 14px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            -
        </td>
        <td style="padding-bottom: 10px; color: #7d878d; font-size: 16px;
        font-family: 'Segoe UI', 'Calibri', 'Lucida Grande', Arial,
        sans-serif;">
            ${file_name}
        </td>
    </tr>
'''
)


"""
Additionaly Text in the Table?
    <tr>
        <td colspan="2" style="padding-bottom: 10px;">
            <table>
                <tbody>
                    <tr>
                        <td style="background: #272822">
                            ${code_content}
                        </td>
                    </tr>
                </tbody>
            </table>
        </td>
    </tr>
"""


def _finish_with_main_wrapper(content: str, introduction: str) -> (str, {str: str}):
    """
    All emails use the main wrapper. This contains the normal html structure
    @return: A sendable mail object, with the content and the attachments
    """
    # cids link the attached media-files to be displayed inline
    header_cid = make_msgid()
    extender_cid = make_msgid()

    full_content = main_wrapper.substitute(
        content=content, introduction_text=introduction, header_cid=header_cid[1:-1], extender_cid=extender_cid[1:-1]
    )

    cids_and_filenames = {}
    cids_and_filenames.update({header_cid: 'header.png'})
    cids_and_filenames.update({extender_cid: 'header_extender.png'})

    return (full_content, cids_and_filenames)


def create_full_moodle_diff_mail(changed_courses: [Course]) -> (str, {str: str}):
    """
    Creates an email with all changed files. This includes new, modified
    and deleted files. Files that have changed since the last email.
    @param changed_courses: A list of all courses with their modified files.
    """
    full_content = ''

    for course in changed_courses:
        inner_content = ''
        for file in course.files:
            saved_to_path = file.saved_to
            if file.new_file is not None:
                saved_to_path = file.new_file.saved_to
            if file.modified:
                inner_content += moodle_modified_box.substitute(file_name=saved_to_path)
            elif file.moved:
                if file.new_file is not None:
                    inner_content += moodle_moved_box.substitute(file_name=(file.saved_to + ' ==> ' + saved_to_path))
                else:
                    inner_content += moodle_moved_box.substitute(file_name=saved_to_path)
            elif file.deleted:
                inner_content += moodle_deleted_box.substitute(file_name=saved_to_path)
            else:
                inner_content += moodle_added_box.substitute(file_name=saved_to_path)

        full_content += moodle_main_box.substitute(content=inner_content, course_name=course.fullname)

    count = len(changed_courses)

    full_content = _finish_with_main_wrapper(
        full_content,
        f'Changes were found in {count} courses:' if count > 1 else 'Changes were noted in the following course:',
    )

    return full_content


def create_full_welcome_mail() -> (str, {str: str}):
    """
    Creates a test email
    """
    content = info_message_box.substitute(text='Wow, it works! \\o/')

    full_content = _finish_with_main_wrapper(content, 'Welcome! Test Test...')

    return full_content


def create_full_error_mail(details) -> (str, {str: str}):
    """
    Creates an error message
    """
    content = error_message_box.substitute(details=details)

    full_content = _finish_with_main_wrapper(content, 'The following error occurred during execution:')

    return full_content


def create_full_failed_downloads_mail(failed_downloads: [Task]) -> (str, {str: str}):
    """
    Creates an message with all failed downloads
    """
    list_entries = ''
    for task in failed_downloads:
        list_entries += failed_downloads_list_entry_box.substitute(
            file_name=task.file.content_filename, error_msg=task.status.get_error_text()
        )

    content = failed_downloads_message_box.substitute(list_entries=list_entries)

    full_content = _finish_with_main_wrapper(
        content, 'Error while trying to download files, look at the log for more details. List of failed downloads:'
    )

    return full_content
