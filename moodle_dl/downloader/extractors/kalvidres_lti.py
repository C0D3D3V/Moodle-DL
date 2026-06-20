# coding: utf-8
from __future__ import unicode_literals

import html
import re
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.extractor.kaltura import KalturaIE
from yt_dlp.utils import ExtractorError, extract_attributes, smuggle_url, urlencode_postdata


class KalvidresLtiIE(InfoExtractor):
    IE_NAME = 'kalvidresLti'
    _VALID_URL = r'(?P<scheme>https?://)(?P<host>[^/]+)(?P<path>.*)?/mod/kalvidres/view.php\?.*?id=(?P<id>\d+)'
    _LAUNCH_FORM = 'ltiLaunchForm'

    def _extract_service_url(self, html_content, partner_id=None):
        """Try to extract the actual Kaltura service URL from page content."""
        escaped_pid = re.escape(partner_id) if partner_id else r'\d+'
        patterns = [
            # Script embed tag (same approach as KalturaIE._extract_embed_urls)
            rf'<script[^>]+src=["\'](?P<url>(?:https?:)?//[^"\']+)/p/{escaped_pid}/sp/{escaped_pid}00/embedIframeJs',
            # Any Kaltura API/CDN URL with partner path
            rf'(?P<url>https?://[^"\'\s>]+)/p/{escaped_pid}(?:/|["\'\s>])',
            # ServiceUrl in flashvars/config
            r'["\'](?:serviceUrl|service_url)["\']\s*:\s*["\'](?P<url>https?://[^"\']+)["\']',
        ]
        for pattern in patterns:
            m = re.search(pattern, html_content)
            if m:
                url = m.group('url')
                # Normalize to base URL
                parsed = urllib.parse.urlparse(url if url.startswith('http') else 'https:' + url)
                return f'{parsed.scheme}://{parsed.netloc}'
        return None

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

        # Try specific LTI launch form first, then fall back to generic form
        launch_form_str = self._search_regex(
            fr'(?P<form><form[^>]+?id=(["\']){self._LAUNCH_FORM}\2[^>]*>)',
            launch_webpage, 'launch form', group='form', default=None
        )

        if launch_form_str:
            action_url = extract_attributes(launch_form_str).get('action') or launch_url
            launch_inputs = self._form_hidden_inputs(self._LAUNCH_FORM, launch_webpage)

            # Launch kalvidres video app
            submit_page, dummy = self._download_webpage_handle(
                action_url, video_id, 'Launch kalvidres app', data=urlencode_postdata(launch_inputs)
            )
        else:
            # Fall back to first form with an action URL
            launch_form_str = self._search_regex(
                r'(?P<form><form[^>]+action=[^>]*>)', launch_webpage,
                'launch form', group='form', default=None
            )
            if launch_form_str:
                action_url = extract_attributes(launch_form_str).get('action') or launch_url
                launch_inputs = self._hidden_inputs(launch_webpage)

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

        # Try to extract Kaltura URL from each page (most specific first)
        kultura_url = (
            KalturaIE._extract_url(redirect_page)  # pylint: disable=protected-access
            or KalturaIE._extract_url(submit_page)  # pylint: disable=protected-access
            or KalturaIE._extract_url(launch_webpage)  # pylint: disable=protected-access
        )

        combined_html = (launch_webpage or '') + '\n' + (submit_page or '') + '\n' + (redirect_page or '')

        if kultura_url:
            # Extract partner_id to help find service_url
            m = re.match(r'^kaltura:(\d+):([^:]+)', kultura_url)
            partner_id = m.group(1) if m else None

            service_url = self._extract_service_url(combined_html, partner_id)
            if service_url:
                kultura_url = smuggle_url(kultura_url, {'service_url': service_url})

            return {
                '_type': 'url',
                'url': kultura_url,
                'ie_key': 'Kaltura',
            }

        # Fallback: manually extract partner_id and entry_id from page content
        pid_match = re.search(r'\b(?:partner_?id|wid)\b["\'/=\s]+_?(\d{4,})', combined_html, re.IGNORECASE)
        eid_match = re.search(r'(?:entry_?id)["\'/=\s]+([01]_[a-zA-Z0-9]{8,10})', combined_html, re.IGNORECASE)

        if not pid_match or not eid_match:
            raise ExtractorError('Unable to extract kaltura partner_id and entry_id')

        partner_id = pid_match.group(1)
        entry_id = eid_match.group(1)

        kultura_url = f'kaltura:{partner_id}:{entry_id}'

        service_url = self._extract_service_url(combined_html, partner_id)
        if service_url:
            kultura_url = smuggle_url(kultura_url, {'service_url': service_url})

        return {
            '_type': 'url',
            'url': kultura_url,
            'ie_key': 'Kaltura',
        }
