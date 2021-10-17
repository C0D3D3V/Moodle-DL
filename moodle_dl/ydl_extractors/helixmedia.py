# coding: utf-8
from __future__ import unicode_literals


import re
import json

from youtube_dl.compat import (
    compat_urllib_parse,
    compat_urllib_parse_urlparse,
)

from youtube_dl.extractor.common import InfoExtractor
from youtube_dl.utils import (
    ExtractorError,
    urlencode_postdata,
    js_to_json,
    determine_ext,
    mimetype2ext,
    extract_attributes,
    HEADRequest,
)


class Helixmedia(InfoExtractor):
    IE_NAME = 'helixmedia'
    _VALID_URL = r'(?P<scheme>https?://)(?P<host>[^/]+)(?P<path>.*)?/mod/helixmedia/view.php\?.*?id=(?P<id>\d+)'
    _LAUNCH_FORM = 'ltiLaunchForm'

    # _TEST = {'url': 'http://localhost/moodle/mod/helixmedia/view.php?id=3'}

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        scheme = mobj.group('scheme')
        host = mobj.group('host')
        path = mobj.group('path')
        video_id = mobj.group('id')

        launch_url = scheme + host + path + '/mod/helixmedia/launch.php?type=1&id=' + video_id

        # webpage = self._download_webpage(url, video_id)
        launch_webpage = self._download_webpage(launch_url, video_id, 'Downloading helixmedia launch webpage')
        launch_inputs = self._form_hidden_inputs(self._LAUNCH_FORM, launch_webpage)
        launch_form_str = self._search_regex(
            r'(?P<form><form[^>]+?id=(["\'])%s\2[^>]*>)' % self._LAUNCH_FORM, launch_webpage, 'login form', group='form'
        )

        action_url = extract_attributes(launch_form_str).get('action')

        submit_page, start_urlh = self._download_webpage_handle(
            action_url, video_id, 'Launch helixmedia app', data=urlencode_postdata(launch_inputs)
        )

        if 'UploadSessionId' not in start_urlh.geturl():
            raise ExtractorError('Unable to launch helixmedia video', expected=True)

        parsed_mediaserver_url = list(compat_urllib_parse_urlparse(start_urlh.geturl()))
        parsed_mediaserver_url[4] += '&mobile=N&fullWidth=940&fullHeight=906'
        parsed_mediaserver_url[2] += 'Split'
        mediaserver_url = compat_urllib_parse.urlunparse(parsed_mediaserver_url)

        video_webpage = self._download_webpage(mediaserver_url, video_id, 'Downloading video details')

        video_model = json.loads(js_to_json(self._search_regex(r'var model = ([^;]+);', video_webpage, 'video model')))

        video_title = video_model.get('VideoTitle', None)

        video_description = video_model.get('VideoDescription', '')
        video_id = str(video_model.get('VideoId', video_id))
        download_url = video_model.get('DownloadUrl', None)
        video_json = json.loads(video_model.get('PlayScreenVm', {}).get('VodPlayerModel', {}).get('PlayerJson', '{}'))
        if video_json == {}:
            video_json = json.loads(video_model.get('VodPlayerModel', {}).get('PlayerJson', '{}'))
        if video_title is None:
            video_title = video_json.get('abouttext', 'Unknown title')

        thumbnail_list = video_json.get('tracks', [])
        thumbnail = None
        if len(thumbnail_list) >= 1:
            thumbnail = thumbnail_list[0].get('file', None)
            if thumbnail is not None:
                thumbnail = thumbnail.replace('vtt', 'jpg')

        sources_list = video_json.get('sources', [])

        formats = []
        for track in sources_list:
            href = track['file']
            ext = determine_ext(href, None)

            if ext == 'mpd':
                # DASH
                formats.extend(self._extract_mpd_formats(href, video_id, mpd_id='dash', fatal=False))
            elif ext == 'm3u8':
                # HLS
                formats.extend(
                    self._extract_m3u8_formats(href, video_id, m3u8_id='hls', entry_protocol='m3u8_native', fatal=False)
                )
            elif ext == 'f4m':
                # HDS
                formats.extend(self._extract_f4m_formats(href, video_id, f4m_id='hds', fatal=False))
            elif ext == 'smil':
                formats.extend(self._extract_smil_formats(href, video_id, fatal=False))
            else:
                track_obj = {
                    'url': href,
                    'ext': ext,
                }
                formats.append(track_obj)

        if download_url is not None:
            ext_req = HEADRequest(download_url)
            ext_handle = self._request_webpage(ext_req, video_id, note='Determining extension')
            ext = self.urlhandle_detect_ext(ext_handle)

            track_obj_direct = {
                'url': download_url,
                'ext': ext,
            }
            formats.append(track_obj_direct)

        self._sort_formats(formats)

        result_obj = {'formats': formats}

        if video_id is not None:
            result_obj.update({'id': video_id})

        if video_title is not None:
            result_obj.update({'title': video_title})

        if video_description is not None:
            result_obj.update({'creator': video_description})

        if thumbnail is not None:
            result_obj.update({'thumbnail': thumbnail})

        return result_obj

    def urlhandle_detect_ext(self, url_handle):
        getheader = url_handle.headers.get

        cd = getheader('Content-Disposition')
        if cd:
            m = re.match(r'attachment;.*filename="(?P<filename>[^"]+)"', cd)
            if m:
                e = determine_ext(m.group('filename'), default_ext=None)
                if e:
                    return e

        return mimetype2ext(getheader('Content-Type'))
