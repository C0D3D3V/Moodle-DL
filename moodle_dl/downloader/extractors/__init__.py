from typing import List

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.YoutubeDL import YoutubeDL

from moodle_dl.downloader.extractors.echo360 import Echo360IE  # noqa: F401
from moodle_dl.downloader.extractors.googledrive import GoogleDriveIE  # noqa: F401
from moodle_dl.downloader.extractors.helixmedia_lti import HelixmediaLtiIE  # noqa: F401
from moodle_dl.downloader.extractors.kalvidres_lti import KalvidresLtiIE  # noqa: F401
from moodle_dl.downloader.extractors.opencast_lti import OpencastLtiIE  # noqa: F401
from moodle_dl.downloader.extractors.owncloud import OwnCloudIE  # noqa: F401
from moodle_dl.downloader.extractors.sharepoint import SharePointIE  # noqa: F401
from moodle_dl.downloader.extractors.sharepointfiles import (  # noqa: F401
    SharePointFilesIE,
)

ALL_ADDITIONAL_EXTRACTORS = [Class for name, Class in globals().items() if name.endswith('IE')]


def add_additional_extractors(ydl: YoutubeDL) -> List[InfoExtractor]:
    moodle_dl_ies = {}
    moodle_dl_ies_instances = {}
    for extractor_class in ALL_ADDITIONAL_EXTRACTORS:
        extractor = extractor_class(ydl)
        ie_key = extractor.ie_key()
        moodle_dl_ies[ie_key] = extractor
        moodle_dl_ies_instances[ie_key] = extractor

    # We access protected member variables of the yt-dlp to add the extractors afterwards.
    # TODO: Use the new possibilities yt-dlp offers to add the extractors to yt-dlp.
    # pylint: disable=protected-access
    moodle_dl_ies.update(ydl._ies)
    moodle_dl_ies_instances.update(ydl._ies_instances)
    ydl._ies = moodle_dl_ies
    ydl._ies_instances = moodle_dl_ies_instances
