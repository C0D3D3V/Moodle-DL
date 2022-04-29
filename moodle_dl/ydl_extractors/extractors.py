from yt_dlp.YoutubeDL import YoutubeDL

from moodle_dl.ydl_extractors.zoomus import ZoomUSIE
from moodle_dl.ydl_extractors.opencast import OpencastIE, OpencastPlaylistIE
from moodle_dl.ydl_extractors.helixmedia import HelixmediaIE
from moodle_dl.ydl_extractors.kalvidres import KalvidresIE
from moodle_dl.ydl_extractors.owncloud import OwncloudIE
from moodle_dl.ydl_extractors.opencast_lti import OpencastLTIIE
from moodle_dl.ydl_extractors.googledrive import GoogleDriveIE


def add_additional_extractors(ydl: YoutubeDL):
    additional_extractors = [
        OpencastIE(ydl),
        OpencastPlaylistIE(ydl),
        ZoomUSIE(ydl),
        HelixmediaIE(ydl),
        KalvidresIE(ydl),
        OwncloudIE(ydl),
        OpencastLTIIE(ydl),
        GoogleDriveIE(ydl),
    ]

    moodle_dl_ies = {}
    moodle_dl_ies_instances = {}
    for extractor in additional_extractors:
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
