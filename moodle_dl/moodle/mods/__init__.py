import asyncio

from typing import List, Dict

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.request_helper import RequestHelper
from moodle_dl.moodle.mods.common import MoodleMod
from moodle_dl.types import Course

from moodle_dl.moodle.mods.assign import AssignMod  # noqa: F401
from moodle_dl.moodle.mods.data import DataMod  # noqa: F401
from moodle_dl.moodle.mods.folder import FolderMod  # noqa: F401
from moodle_dl.moodle.mods.forum import ForumMod  # noqa: F401
from moodle_dl.moodle.mods.lesson import LessonMod  # noqa: F401
from moodle_dl.moodle.mods.page import PageMod  # noqa: F401
from moodle_dl.moodle.mods.quiz import QuizMod  # noqa: F401
from moodle_dl.moodle.mods.workshop import WorkshopMod  # noqa: F401

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
    result = []
    for mod in ALL_MODS:
        result.append(mod(request_helper, moodle_version, user_id, last_timestamps, config))
    return result


async def fetch_mods_files(mods_to_fetch: List[MoodleMod], courses_to_load: List[Course]) -> Dict[str, Dict]:
    "@return: Dictionary of all fetched files, indexed by mod name, then by courses, then module id"
    mods_results = await asyncio.gather(*[mod.fetch_mod_entries(courses_to_load) for mod in mods_to_fetch])
    result = {}
    for idx, mod in enumerate(mods_to_fetch):
        result[mod.MOD_NAME] = mods_results[idx]
    return result


def get_mod_plurals():
    result = {}
    for mod in ALL_MODS:
        result[mod.MOD_NAME] = mod.MOD_PLURAL_NAME
    return result
