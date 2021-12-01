# coding: utf-8
from __future__ import unicode_literals


import re
import json
import html

from yt_dlp.compat import (
    compat_urllib_parse,
    compat_urllib_parse_urlparse,
)

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.kaltura import KalturaIE
from yt_dlp.utils import (
    ExtractorError,
    urlencode_postdata,
    js_to_json,
    determine_ext,
    mimetype2ext,
    extract_attributes,
    HEADRequest,
)


class KalvidresIE(InfoExtractor):
    IE_NAME = 'kalvidres'
    _VALID_URL = r'(?P<scheme>https?://)(?P<host>[^/]+)(?P<path>.*)?/mod/kalvidres/view.php\?.*?id=(?P<id>\d+)'
    _LAUNCH_FORM = 'ltiLaunchForm'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        scheme = mobj.group('scheme')
        host = mobj.group('host')
        path = mobj.group('path')
        video_id = mobj.group('id')

        # Extract launch URL
        view_webpage = self._download_webpage(url, video_id, 'Downloading kalvidres video view webpage')
        mobj = re.search(r'<iframe[^>]+class="kaltura-player-iframe"[^>]+src=(["\'])(?P<url>[^"\']+)\1', view_webpage)
        if not mobj:
            raise ExtractorError('Unable to extract kalvidres launch url')

        launch_url = html.unescape(mobj.group('url'))

        # Get launch parameters
        launch_webpage = self._download_webpage(launch_url, video_id, 'Downloading kalvidres launch webpage')
        launch_inputs = self._form_hidden_inputs(self._LAUNCH_FORM, launch_webpage)
        launch_form_str = self._search_regex(
            r'(?P<form><form[^>]+?id=(["\'])%s\2[^>]*>)' % self._LAUNCH_FORM, launch_webpage, 'login form', group='form'
        )

        action_url = extract_attributes(launch_form_str).get('action')

        # Launch kalvidres video app
        submit_page, start_urlh = self._download_webpage_handle(
            action_url, video_id, 'Launch kalvidres app', data=urlencode_postdata(launch_inputs)
        )

        mobj = re.search(r'window.location.href = \'(?P<url>[^\']+)\'', submit_page)
        if not mobj:
            raise ExtractorError('Unable to extract kalvidres redirect url')

        # Follow kalvidres video app redirect
        redirect_page, redirect_urlh = self._download_webpage_handle(
            html.unescape(mobj.group('url')), video_id, 'Follow kalvidres redirect'
        )

        kultura_url = KalturaIE._extract_url(redirect_page)
        if not kultura_url:
            raise ExtractorError('Unable to extract kaltura url')

        return {
            '_type': 'url',
            'url': kultura_url,
            'ie_key': 'Kaltura',
        }
