from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import determine_ext, int_or_none, url_or_none


class SharePointFilesIE(InfoExtractor):
    _VALID_URL = r'https?://[^\.]+\.sharepoint\.com/:[pwx]:/g/[^/]+/[^/]+/(?P<id>[^/?]+)'

    _TESTS = [
        {
            'url': 'https://lut-my.sharepoint.com/:p:/g/personal/juha_eerola_student_lab_fi/'
            + 'EdHr6d6EV89LlfipfMzVsasBymdnQBpUVor9LrhiX24Z8w?e=003Xgv',
            'info_dict': {
                'id': 'EdHr6d6EV89LlfipfMzVsasBymdnQBpUVor9LrhiX24Z8w',
                'ext': 'pptx',
                'title': '2. K23 Kivun luokittelu keston mukaan.pptx',
                'modified_timestamp': 1675785393000,
            },
        },
        {
            'url': 'https://lut-my.sharepoint.com/:w:/g/personal/juha_eerola_student_lab_fi/'
            + 'EfjpAV2zXSpKmMflo08J15QBKWpb-0fFSsx-Q4yvmzc1mw?e=n14Mto',
            'info_dict': {
                'id': 'EfjpAV2zXSpKmMflo08J15QBKWpb-0fFSsx-Q4yvmzc1mw',
                'ext': 'docx',
                'title': 'LABin_opinnäytetyöraportin_kirjoituspohja_260822.docx',
                'modified_timestamp': 1675786271000,
            },
        },
        {
            'url': 'https://lut-my.sharepoint.com/:x:/g/personal/juha_eerola_student_lab_fi/'
            + 'EeMmrRu3BptJoH5WPTsdTyEB460rKPzMu-GmHIH2xcJGXQ?e=tVbK9U',
            'info_dict': {
                'id': 'EeMmrRu3BptJoH5WPTsdTyEB460rKPzMu-GmHIH2xcJGXQ',
                'ext': 'xlsx',
                'title': 'Kalenteri ryhmätöitä varten - Imatra.xlsx',
                'modified_timestamp': 1665724530000,
            },
            'params': {'skip_download': 'file small'},
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')
        webpage = self._download_webpage(url, video_id)

        metadata = self._search_json(r'_wopiContextJson\s*=', webpage, 'metadata', video_id)
        download_url = url_or_none(metadata.get('FileGetUrl'))
        return {
            'id': video_id,
            'title': metadata.get('FileName'),
            'modified_timestamp': metadata.get('LastModified'),
            'formats': [
                {
                    'url': download_url,
                    'ext': determine_ext(metadata.get('FileName')),
                    'filesize': int_or_none(metadata.get('FileSize')),
                }
            ],
        }
