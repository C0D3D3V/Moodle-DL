from youtube_dl.YoutubeDL import YoutubeDL

from moodle_dl.ydl_extractors.zoomus import ZoomUSIE
from moodle_dl.ydl_extractors.opencast import OpencastIE, OpencastPlaylistIE
from moodle_dl.ydl_extractors.helixmedia import Helixmedia
from moodle_dl.ydl_extractors.owncloud import Owncloud
from moodle_dl.ydl_extractors.opencast_lti import OpencastLTI
from moodle_dl.ydl_extractors.googledrive import GoogleDriveIE


def add_additional_extractors(ydl: YoutubeDL):
    additional_extractors = [
        OpencastIE(ydl),
        OpencastPlaylistIE(ydl),
        ZoomUSIE(ydl),
        Helixmedia(ydl),
        Owncloud(ydl),
        OpencastLTI(ydl),
        GoogleDriveIE(ydl),
    ]

    for extractor in additional_extractors:
        ydl._ies.insert(0, extractor)
        ydl._ies_instances[extractor.ie_key()] = extractor
