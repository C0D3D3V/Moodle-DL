from youtube_dl.YoutubeDL import YoutubeDL

from moodle_dl.ydl_extractors.zoomus import ZoomUSIE
from moodle_dl.ydl_extractors.opencast import OpencastIE, OpencastPlaylistIE


def add_additional_extractors(ydl: YoutubeDL):
    additional_extractors = [
        OpencastIE(ydl),
        OpencastPlaylistIE(ydl),
        ZoomUSIE(ydl),
    ]

    for extractor in additional_extractors:
        ydl._ies.insert(0, extractor)
        ydl._ies_instances[extractor.ie_key()] = extractor
