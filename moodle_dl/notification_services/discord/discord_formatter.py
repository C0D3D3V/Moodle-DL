import re

from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.url_target import URLTarget


class DiscordFormatter:
    @classmethod
    def make_bold(cls, string: str) -> str:
        """
        Makes a string bold in a telegram message
        """
        return '**' + string + '**'

    @classmethod
    def create_full_moodle_diff_messages(cls, changed_courses: [Course], moodle_url) -> [str]:
        """
        Creates telegram messages with all changed files. This includes new,
        modified and deleted files. Files that have changed since the last message.

        @param changed_courses: A list of all courses with their modified files.
        @returns embeds to send
        """

        embeds = []

        for course in changed_courses:
            new_embed = {
                'author': {
                    'name': course.fullname,
                    'url': f" {moodle_url}?id={course.id}",
                    'icon_url': 'https://i.imgur.com/Bt5TFIA.png'
                },
                'fields': []
            }

            for file in course.files:
                saved_to_path = file.saved_to
                if file.new_file is not None:
                    saved_to_path = file.new_file.saved_to

                field_name = 'Initialised'
                new_embed['color'] = '13948116'  # neutral grey
                if file.new_file:
                    field_name = 'Added'
                    new_embed['color'] = '7268279'  # emerald green
                elif file.modified:
                    field_name = 'Modified'
                    new_embed['color'] = '16628340'  # orange
                elif file.moved:
                    field_name = 'Moved'
                    new_embed['color'] = '8246268'  # sky blue
                elif file.deleted:
                    field_name = 'Deleted'
                    new_embed['color'] = '16622767'  # rose

                value = f"• {saved_to_path.replace(f'{course.fullname}/', '')}"

                for field in new_embed['fields']:
                    if field['name'] == field_name:
                        field['value'] += f"\n{value}"

                found = next((item for item in new_embed['fields'] if item['name'] == field_name), None)
                if not found:
                    new_embed['fields'].append({'name': field_name, 'value': value})

            for field in new_embed['fields']:
                value = field['value']
                field['value'] = value[:1021] + '...' if len(value) > 1024 else value
            embeds.append(new_embed)

        return embeds

    @classmethod
    def create_full_error_messages(cls, details) -> [str]:
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
    def create_full_failed_downloads_messages(cls, failed_downloads: [URLTarget]) -> [str]:
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
        for url_target in failed_downloads:
            new_line = f'⚠️ {url_target.file.content_filename}:\r\n{url_target.error}\r\n\r\n'
            if url_target.file.content_filename != url_target.file.content_fileurl:
                new_line = (
                        f'⚠️ {url_target.file.content_filename} ({url_target.file.content_fileurl}):'
                        + f'\r\n{url_target.error}\r\n\r\n'
                )

            one_msg_content = cls.append_with_limit(new_line, one_msg_content, result_list)

        result_list.append(one_msg_content)
        return result_list
