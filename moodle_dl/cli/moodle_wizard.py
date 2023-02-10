import sys

from getpass import getpass

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.moodle_service import MoodleService
from moodle_dl.moodle.request_helper import RequestRejectedError
from moodle_dl.types import MoodleURL, MoodleDlOpts
from moodle_dl.utils import Log


class MoodleWizard:
    def __init__(self, config: ConfigHelper, opts: MoodleDlOpts):
        self.config = config
        self.opts = opts

    def interactively_acquire_token(self, use_stored_url: bool = False) -> str:
        if self.opts.sso or self.opts.token is not None:
            self.interactively_acquire_sso_token(use_stored_url=use_stored_url)
        else:
            self.interactively_acquire_normal_token(use_stored_url=use_stored_url)

    def interactively_get_moodle_url(self, use_stored_url: bool) -> MoodleURL:
        if use_stored_url:
            return self.config.get_moodle_URL()

        url_ok = False
        while not url_ok:
            url_ok = True
            moodle_url = input('URL of Moodle:   ')

            use_http = False
            if moodle_url.startswith('http://'):
                Log.warning(
                    'Warning: You have entered an insecure URL! Are you sure that the Moodle is'
                    + ' not accessible via `https://`? All your data will be transferred'
                    + ' insecurely! If your Moodle is accessible via `https://`, then run'
                    + ' the process again using `https://` to protect your data.'
                )
                use_http = True
            elif not moodle_url.startswith('https://'):
                Log.error('The url of your moodle must start with `https://`')
                url_ok = False

        moodle_domain, moodle_path = MoodleService.split_moodle_url(moodle_url)
        return MoodleURL(use_http, moodle_domain, moodle_path)

    def interactively_acquire_normal_token(self, use_stored_url: bool = False) -> str:
        """
        Walks the user through executing a login into the Moodle-System to get
        the Token and saves it.
        @return: The Token for Moodle.
        """

        automated = False
        stop_automatic_generation = False
        if self.opts.username is not None and self.opts.password is not None:
            automated = True

        if not automated:
            print('[The following Credentials are not saved, it is only used temporarily to generate a login token.]')

        moodle_token = None
        while moodle_token is None or (stop_automatic_generation and automated):
            moodle_url = self.interactively_get_moodle_url(use_stored_url)

            if self.opts.username is not None:
                moodle_username = self.opts.username
                stop_automatic_generation = True
            else:
                moodle_username = input('Username for Moodle:   ')

            if self.opts.password is not None:
                moodle_password = self.opts.password
            else:
                moodle_password = getpass('Password for Moodle [no output]:   ')

            try:
                moodle_token, moodle_privatetoken = MoodleService.obtain_login_token(
                    self.opts, moodle_username, moodle_password, moodle_url
                )

            except RequestRejectedError as error:
                Log.error(f'Login Failed! ({error}) Please try again.')
            except (ValueError, RuntimeError) as error:
                Log.error(f'Error while communicating with the Moodle System! ({error}) Please try again.')
            except ConnectionError as error:
                Log.error(str(error))

        if automated is True and moodle_token is None:
            sys.exit(1)

        self.config.set_tokens(moodle_token, moodle_privatetoken)
        self.config.set_moodle_URL(moodle_url)

        Log.success('Token successfully saved!')

        return moodle_token

    def interactively_acquire_sso_token(self, use_stored_url: bool = False) -> str:
        """
        Walks the user through the receiving of a SSO token
        @return: The Token for Moodle.
        """

        moodle_url = self.interactively_get_moodle_url(use_stored_url)

        if self.opts.token is not None:
            moodle_token = self.opts.token
        else:
            Log.warning('Please use the Chrome browser for the following procedure')
            print('1. Log into your Moodle Account')
            print('2. Open the developer console (press F12) and go to the Network tab')
            print('3. Then visit the following URL in the same browser tab you have logged in:')

            print(
                moodle_url.url_base
                + 'admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=12345&urlscheme=moodledl'
            )
            print()
            print(
                'If you open the link, no web page should load, instead an error will occur.'
                + ' In the Network tab of the developer console you opened before there should be an error entry.'
            )

            print('The script expects a URL that looks something like this:')
            Log.info('moodledl://token=$apptoken')
            print(
                ' Where $apptoken looks random and "moodledl" can also be a different url scheme '
                + ' like "moodlemobile". In reality $apptoken is a Base64 string containing the token to access moodle.'
            )

            print(
                '4. Copy the link address of the website that could not be loaded'
                + ' (right click the list entry, then click on Copy, then click on copy link address)'
            )

            token_address = input('Then insert the link address here:   ')

            moodle_token, moodle_privatetoken = MoodleService.extract_token(token_address)
            if moodle_token is None:
                raise ValueError('Invalid URL!')

        self.config.set_tokens(moodle_token, moodle_privatetoken)
        self.config.set_moodle_URL(moodle_url)

        Log.success('Token successfully saved!')

        return moodle_token
