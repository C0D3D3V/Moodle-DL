from datetime import datetime
from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.moodle.moodle_constants import (
    course_events_module_id,
    course_events_section_id,
    moodle_event_footer,
    moodle_event_header,
)
from moodle_dl.types import Course, File
from moodle_dl.utils import PathTools as PT

# TODO: should we use locale.setlocale(locale.LC_TIME, "") to set localized version of Date format
# or should we use https://babel.pocoo.org/en/latest/dates.html
# babel.dates.format_datetime(datetime_obj) is enough to use local setting,
# but we could also use user language settings of moodle,
# we can pass it to format_datetime by defining locale='user_lang' as extra argument
# We can also use babel.dates.format_timedelta(time_delta) to print the time delta into the date file


class CalendarMod(MoodleMod):
    MOD_NAME = 'calendar'
    MOD_PLURAL_NAME = 'events'
    MOD_MIN_VERSION = 2013051400  # 2.5

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        return config.get_download_calendars() or (not (file.module_modname.endswith(cls.MOD_NAME) and file.deleted))

    async def real_fetch_mod_entries(
        self, courses: List[Course], core_contents: Dict[int, List[Dict]]
    ) -> Dict[int, Dict[int, Dict]]:
        result = {}
        if not self.config.get_download_calendars():
            return result

        last_timestamp = self.last_timestamps.get(self.MOD_NAME, {}).get(course_events_module_id, 0)
        calendar_req_data = {
            'options': {'timestart': last_timestamp, 'userevents': 0},
            'events': self.get_data_for_mod_entries_endpoint(courses),
        }

        events = (await self.client.async_post('core_calendar_get_calendar_events', calendar_req_data)).get(
            'events', []
        )

        events_per_course = self.sort_by_courseid(events)

        for course_id, events in events_per_course.items():
            event_files = []
            for event in events:
                event_name = event.get('name', 'unnamed event')
                event_description = event.get('description', None)

                event_modulename = event.get('modulename', None)
                event_timestart = event.get('timestart', 0)
                event_timeduration = event.get('timeduration', 0)

                event_filename = PT.to_valid_name(
                    f'{datetime.fromtimestamp(event_timestart).strftime("%Y.%m.%d %H:%M")} {event_name}', is_file=False
                )
                event_content = moodle_event_header
                event_content += f'<div class="event-title"><span class="icon">&#128197;</span>{event_name}</div>'
                event_content += (
                    '<div class="attribute"><span class="icon">&#9201;</span>'
                    + f'Start Time: {datetime.fromtimestamp(event_timestart).strftime("%c")}</div>'
                )
                if event_timeduration != 0:
                    event_timeend = event_timestart + event_timeduration
                    event_content += (
                        '<div class="attribute"><span class="icon">&#9201;</span>'
                        + f'End Time: {datetime.fromtimestamp(event_timeend).strftime("%c")}</div>'
                    )
                if event_description is not None and event_description != '':
                    event_content += (
                        '<div class="attribute"><span class="icon">&#128196;</span>' + f'{event_description}</div>'
                    )
                if event_modulename is not None:
                    event_content += (
                        '<div class="attribute"><span class="icon">&#128218;</span>'
                        f'Module Type: {event_modulename}</div>'
                    )

                event_content += moodle_event_footer

                event_files.append(
                    {
                        'filename': event_filename,
                        'filepath': '/',
                        'html': event_content,
                        'type': 'html',
                        'timemodified': event.get('timemodified', 0),
                        'filesize': len(event_content),
                        'no_search_for_urls': True,
                    }
                )
            if course_id not in core_contents:
                core_contents[course_id] = []
            core_contents[course_id].append(
                {
                    'id': course_events_section_id,
                    'name': 'Events',
                    'modules': [{'id': course_events_module_id, 'name': 'Events', 'modname': 'calendar'}],
                }
            )

            self.add_module(
                result,
                course_id,
                course_events_module_id,
                {
                    'id': course_events_module_id,
                    'name': 'Events',
                    'files': event_files,
                },
            )

        return result

    @staticmethod
    def sort_by_courseid(events):
        sorted_dict = {}
        for event in events:
            course_id = event.get('courseid', 0)
            if course_id not in sorted_dict:
                sorted_dict[course_id] = []
            sorted_dict[course_id].append(event)
        return sorted_dict
