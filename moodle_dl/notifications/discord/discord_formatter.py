from moodle_dl.types import Course


class DiscordFormatter:
    @classmethod
    def make_bold(cls, string: str) -> str:
        """
        Makes a string bold in a telegram message
        """
        return '**' + string + '**'

    @classmethod
    def create_full_moodle_diff_messages(cls, changed_courses: [Course], moodle_url_base) -> [str]:
        """
        Creates Discord messages with all changed files. This includes new,
        modified and deleted files. Files that have changed since the last message.

        @param changed_courses: A list of all courses with their modified files.
        @returns embeds to send
        """

        embeds = []

        for course in changed_courses:
            new_embed = {
                'author': {
                    'name': course.fullname,
                    'url': f"{moodle_url_base}course/view.php?id={course.id}",
                    'icon_url': 'https://i.imgur.com/Bt5TFIA.png',
                },
                'fields': [],
            }

            for file in course.files:
                saved_to_path = file.saved_to
                if file.new_file is not None:
                    saved_to_path = file.new_file.saved_to

                field_name = 'Added'
                new_embed['color'] = '7268279'  # emerald green

                if file.modified:
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
                        break
                else:
                    new_embed['fields'].append({'name': field_name, 'value': value})

            for field in new_embed['fields']:
                value = field['value']
                field['value'] = value[:1021] + '...' if len(value) > 1024 else value
            embeds.append(new_embed)

        return embeds
