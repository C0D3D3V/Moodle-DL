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


class OpencastLTI(InfoExtractor):
    IE_NAME = 'opencastLTI'
    _VALID_URL = r'(?P<scheme>https?://)(?P<host>[^/]+)(?P<path>.*)?/mod/lti/view.php\?.*?id=(?P<id>\d+)'
    _LAUNCH_FORM = 'ltiLaunchForm'

    # _TEST = {'url': 'http://moodle.ruhr-uni-bochum.de/mod/lti/view.php?id=1406269'}

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        scheme = mobj.group('scheme')
        host = mobj.group('host')
        path = mobj.group('path')
        video_id = mobj.group('id')

        launch_url = scheme + host + path + '/mod/lti/launch.php?id=' + video_id

        # webpage = self._download_webpage(url, video_id)
        launch_webpage = self._download_webpage(launch_url, video_id, 'Downloading opencast lti launch webpage')
        launch_inputs = self._form_hidden_inputs(self._LAUNCH_FORM, launch_webpage)
        launch_form_str = self._search_regex(
            r'(?P<form><form[^>]+?id=(["\'])%s\2[^>]*>)' % self._LAUNCH_FORM, launch_webpage, 'login form', group='form'
        )

        action_url = extract_attributes(launch_form_str).get('action')

        submit_page, start_urlh = self._download_webpage_handle(
            action_url, video_id, 'Launch opencast app', data=urlencode_postdata(launch_inputs)
        )

        if start_urlh.status != 200:
            raise ExtractorError('Unable to launch opencast app', expected=True)

        return {
            '_type': 'url',
            'url': start_urlh.geturl(),
        }
