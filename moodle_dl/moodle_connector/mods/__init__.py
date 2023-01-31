from typing import List, Dict

from moodle_dl.config_service import ConfigHelper
from moodle_dl.moodle_connector import RequestHelper
from moodle_dl.moodle_connector.mods.common import MoodleMod

from moodle_dl.moodle_connector.mods.assign import AssignMod  # noqa: F401
from moodle_dl.moodle_connector.mods.data import DataMod  # noqa: F401
from moodle_dl.moodle_connector.mods.folder import FolderMod  # noqa: F401
from moodle_dl.moodle_connector.mods.forum import ForumMod  # noqa: F401
from moodle_dl.moodle_connector.mods.lesson import LessonMod  # noqa: F401
from moodle_dl.moodle_connector.mods.page import PageMod  # noqa: F401
from moodle_dl.moodle_connector.mods.quiz import QuizMod  # noqa: F401
from moodle_dl.moodle_connector.mods.workshop import WorkshopMod  # noqa: F401

ALL_MODS = [Class for name, Class in globals().items() if name.endswith('Mod') and name != 'MoodleMod']


def get_all_mods_classes() -> List[MoodleMod]:
    return ALL_MODS


def get_all_mods(
    request_helper: RequestHelper,
    moodle_version: int,
    user_id: int,
    last_timestamps: Dict[str, Dict[int, int]],
    config: ConfigHelper,
) -> List[MoodleMod]:
    result_list = []
    for mod_handler in ALL_MODS:
        result_list.append(mod_handler(request_helper, moodle_version, user_id, last_timestamps, config))
    return result_list
