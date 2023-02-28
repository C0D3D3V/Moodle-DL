import re
from typing import List

import html2text

from moodle_dl.types import Course
from moodle_dl.downloader.task import Task
from moodle_dl.utils import PathTools as PT


class TelegramFormater:
    @staticmethod
    def append_with_limit(new_line: str, one_msg_content: str, msg_list: List[str], limit: int = 4096):
        """Appends a new line to a message string,
        if the string is to long it ist appended to the message list.
        Returns the new message string.

        Args:
            new_line (str): A new line to append to a message string
            one_msg_content (str): The current message string
            msg_list ([str]): The list of finished messages
        Returns:
            str: The new message string
        """
        # Replace Telegram Entities
        new_line = re.sub("<(?!/b>|b>)", '&lt;', new_line)
        new_line = re.sub("(?<!</b)(?<!<b)>", '&gt;', new_line)
        if len(one_msg_content) + len(new_line) >= limit:
            msg_list.append(one_msg_content)
            if len(new_line) >= limit:
                new_line = new_line[: limit - 3] + '…'
            return new_line
        else:
            return one_msg_content + new_line

    @staticmethod
    def make_bold(string: str) -> str:
        """
        Makes a string bold in a telegram message
        """
        return '<b>' + string + '</b>'

    @classmethod
    def create_full_moodle_diff_messages(cls, changed_courses: List[Course]) -> List[str]:
        """
        Creates telegram messages with all changed files. This includes new,
        modified and deleted files. Files that have changed since the last message.

        @param changed_courses: A list of all courses with their modified files.
        @return: a list of messages
        """

        diff_count = 0
        for course in changed_courses:
            diff_count += len(course.files)

        result_list = []
        one_msg_content = f'{diff_count} new Changes in the Moodle courses!'

        for course in changed_courses:
            new_line = '\r\n\r\n\r\n👉 ' + cls.make_bold(course.fullname) + '\r\n'
            one_msg_content = cls.append_with_limit(new_line, one_msg_content, result_list)

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

                one_msg_content = cls.append_with_limit(new_line, one_msg_content, result_list)

                if (not file.moved and not file.deleted) and (
                    file.content_type == 'description'
                    or (file.content_type == 'html' and file.module_modname == 'page')
                ):
                    text_lines = []
                    try:
                        with open(saved_to_path, 'r', encoding='utf-8') as content_file:
                            content = content_file.read()

                            if file.content_type == 'html':
                                h2t_handler = html2text.HTML2Text()
                                content = h2t_handler.handle(content).strip()
                                if content == '':
                                    continue

                            text_lines = content.splitlines()
                    except OSError:
                        text_lines = []

                    if len(text_lines) > 0:
                        one_msg_content = cls.append_with_limit('\r\n👇\r\n', one_msg_content, result_list)
                        for new_line in text_lines:
                            new_line = new_line + '\r\n'
                            one_msg_content = cls.append_with_limit(new_line, one_msg_content, result_list)
                        one_msg_content = cls.append_with_limit('👆\r\n', one_msg_content, result_list)

        result_list.append(one_msg_content)
        return result_list

    @classmethod
    def create_full_error_messages(cls, details) -> List[str]:
        """
        Creates error messages
        """
        result_list = []

        one_msg_content = '🛑 The following error occurred during execution:\r\n'
        for new_line in details.splitlines():
            new_line = new_line + '\r\n'
            one_msg_content = cls.append_with_limit(new_line, one_msg_content, result_list)

        result_list.append(one_msg_content)
        return result_list

    @classmethod
    def create_full_failed_downloads_messages(cls, failed_downloads: List[Task]) -> List[str]:
        """
        Creates messages with all failed downloads
        """

        result_list = []
        if len(failed_downloads) == 0:
            return result_list

        one_msg_content = (
            '⁉️ Error while trying to download files, look at the log for more details.'
            + '\r\nList of failed downloads:\r\n\r\n'
        )
        for task in failed_downloads:
            new_line = (
                f'⚠️ {PT.to_valid_name(task.file.content_filename, is_file=True)}:'
                + f'\r\n{task.status.get_error_text()}\r\n\r\n'
            )
            if task.file.content_filename != task.file.content_fileurl:
                new_line = (
                    f'⚠️ {PT.to_valid_name(task.file.content_filename, is_file=True)} ({task.file.content_fileurl}):'
                    + f'\r\n{task.status.get_error_text()}\r\n\r\n'
                )

            one_msg_content = cls.append_with_limit(new_line, one_msg_content, result_list)

        result_list.append(one_msg_content)
        return result_list
