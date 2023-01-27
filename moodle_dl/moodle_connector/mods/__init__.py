from typing import List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector.mods.common import MoodleMod
from moodle_dl.moodle_connector.request_helper import RequestHelper

from moodle_dl.moodle_connector.mods.assignments_handler import AssignmentsHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.databases_handler import DatabasesHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.folders_handler import FoldersHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.forums_handler import ForumsHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.lessons_handler import LessonsHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.pages_handler import PagesHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.quizzes_handler import QuizzesHandler  # noqa: F401
from moodle_dl.moodle_connector.mods.workshops_handler import WorkshopsHandler  # noqa: F401

ALL_MODS = [Class for name, Class in globals().items() if name.endswith('Handler')]


def get_all_moodle_mods(request_helper: RequestHelper, moodle_version: int, config: ConfigHelper) -> List[MoodleMod]:
    result_list = []
    for mod_handler in ALL_MODS:
        result_list.append(mod_handler(request_helper, moodle_version, config))
    return result_list
