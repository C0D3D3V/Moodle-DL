import urllib.parse as urlparse


def add_token_to_url(url: str, token: str):
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update({'token': token})
    url_parts[4] = urlparse.urlencode(query)
    return urlparse.urlunparse(url_parts)
