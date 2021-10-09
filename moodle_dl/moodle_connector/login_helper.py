from moodle_dl.moodle_connector.request_helper import RequestHelper


def obtain_login_token(
    username: str,
    password: str,
    moodle_domain: str,
    moodle_path: str = '/',
    skip_cert_verify: bool = False,
    use_http: bool = False,
) -> str:
    """
    Send the login credentials to the Moodle-System and extracts the resulting Login-Token.

    @params: The necessary parameters to create a Token.
    @return: The received token.
    """
    login_data = {'username': username, 'password': password, 'service': 'moodle_mobile_app'}

    response = RequestHelper(
        moodle_domain, moodle_path, skip_cert_verify=skip_cert_verify, use_http=use_http
    ).get_login(login_data)

    if 'token' not in response:
        # = we didn't get an error page (checked by the RequestHelper) but
        # somehow we don't have the needed token
        raise RuntimeError('Invalid response received from the Moodle System!  No token was received.')

    if 'privatetoken' not in response:
        return response.get('token', ''), None
    else:
        return response.get('token', ''), response.get('privatetoken', '')
