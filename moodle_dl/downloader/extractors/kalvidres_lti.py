# coding: utf-8
from __future__ import unicode_literals

import html
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.kaltura import KalturaIE
from yt_dlp.utils import ExtractorError, extract_attributes, urlencode_postdata


class KalvidresLtiIE(InfoExtractor):
    IE_NAME = 'kalvidresLti'
    _VALID_URL = r'(?P<scheme>https?://)(?P<host>[^/]+)(?P<path>.*)?/mod/kalvidres/view.php\?.*?id=(?P<id>\d+)'
    _LAUNCH_FORM = 'ltiLaunchForm'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        # scheme = mobj.group('scheme')
        # host = mobj.group('host')
        # path = mobj.group('path')
        video_id = mobj.group('id')

        # Extract launch URL
        view_webpage = self._download_webpage(url, video_id, 'Downloading kalvidres video view webpage')
        mobj = re.search(r'<iframe[^>]+class="kaltura-player-iframe"[^>]+src=(["\'])(?P<url>[^"\']+)\1', view_webpage)
        if not mobj:
            raise ExtractorError('Unable to extract kalvidres launch url')

        launch_url = html.unescape(mobj.group('url'))

        # Get launch parameters
        launch_webpage = self._download_webpage(launch_url, video_id, 'Downloading kalvidres launch webpage')

        launch_form_str = self._search_regex(
            r'(?P<form><form[^>]*>)', launch_webpage, 'launch form', group='form', default=None
        )

        if launch_form_str:
            action_url = extract_attributes(launch_form_str).get('action') or launch_url
            launch_inputs = self._hidden_inputs(launch_webpage)

            # Launch kalvidres video app
            submit_page, dummy = self._download_webpage_handle(
                action_url, video_id, 'Launch kalvidres app', data=urlencode_postdata(launch_inputs)
            )
        else:
            submit_page = launch_webpage

        # Follow kalvidres video app redirect if present
        mobj = re.search(r'window(?:(?:\.top|\.parent))?\.location\.(?:href|replace)\s*(?:=|)\s*\(?[\'"](?P<url>[^\'"]+)[\'"]\)?', submit_page)
        if mobj:
            redirect_page, dummy = self._download_webpage_handle(
                html.unescape(mobj.group('url')), video_id, 'Follow kalvidres redirect'
            )
        else:
            redirect_page = submit_page

        kultura_url = KalturaIE._extract_url(redirect_page)  # pylint: disable=protected-access
        partner_id = entry_id = None

        if kultura_url:
            m = re.match(r'^kaltura:(\d+):([^:]+)', kultura_url)
            if m:
                partner_id = m.group(1)
                entry_id = m.group(2)

        combined_html = (launch_webpage or '') + '\n' + (submit_page or '') + '\n' + (redirect_page or '')

        if not partner_id or not entry_id:
            pid_match = re.search(r'(?:partner_?id|wid|p)["\'/=\s]+_?(\d{4,})', combined_html, re.IGNORECASE)
            eid_match = re.search(r'(?:entry_?id)["\'/=\s]+([0-1]_[a-zA-Z0-9]{8})', combined_html, re.IGNORECASE)
            if pid_match and eid_match:
                partner_id = pid_match.group(1)
                entry_id = eid_match.group(1)

        if not partner_id or not entry_id:
            raise ExtractorError('Unable to extract kaltura partner_id and entry_id')

        ks = None
        for r in [r'"ks"\s*:\s*"([^"]+)"', r'flashvars\[ks\]=([^&"\']+)', r'name=["\'](?:custom_)?ks["\']\s+value=["\']([^"\']+)["\']', r'(?:ks)["\'/=\s]+([a-zA-Z0-9_\-\|%]{20,})']:
            ks_match = re.search(r, combined_html, re.IGNORECASE)
            if ks_match:
                ks = ks_match.group(1)
                break

        ks_param = f'/ks/{ks}' if ks else ''

        direct_hls_url = f'https://cdnapisec.kaltura.com/p/{partner_id}/sp/{partner_id}00/playManifest/entryId/{entry_id}/format/applehttp/protocol/https{ks_param}'

        return {
            '_type': 'url',
            'url': direct_hls_url,
            'id': entry_id,
            'title': entry_id,
        }
