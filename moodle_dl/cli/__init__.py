import os
import sys

from moodle_dl.config import ConfigHelper
from moodle_dl.types import MoodleDlOpts
from moodle_dl.utils import Cutie, Log

from moodle_dl.cli.config_wizard import ConfigWizard
from moodle_dl.cli.database_manager import DatabaseManager
from moodle_dl.cli.moodle_wizard import MoodleWizard
from moodle_dl.cli.notifications_wizard import NotificationsWizard

__all__ = ["ConfigWizard", "DatabaseManager", "NotificationsWizard"]


def init_config(config: ConfigHelper, opts: MoodleDlOpts):
    if config.is_present():
        do_override_input = Cutie.prompt_yes_or_no(Log.error_str('Do you want to override the existing config?'))

        if not do_override_input:
            sys.exit(0)

    NotificationsWizard(config, opts).interactively_configure_all_services()

    do_sentry = Cutie.prompt_yes_or_no('Do you want to configure Error Reporting via Sentry?')
    if do_sentry:
        sentry_dsn = input('Please enter your Sentry DSN:   ')
        config.set_property('sentry_dsn', sentry_dsn)

    MoodleWizard(config, opts).interactively_acquire_token()

    Log.success('Configuration finished and saved!')

    if os.name != 'nt':
        working_dir = os.path.abspath(opts.path)
        moodle_dl_path = os.path.abspath(sys.argv[0])
        Log.info(
            '  To set a cron-job for this program on your Unix-System:\n'
            + '    1. `crontab -e`\n'
            + f'    2. Add `*/15 * * * * cd "{working_dir}" && "{moodle_dl_path}" >/dev/null 2>&1`\n'
            + '    3. Save and you\'re done!'
        )

        Log.info(
            'For more ways to run `moodle-dl` periodically, take a look at the wiki'
            + ' (https://github.com/C0D3D3V/Moodle-DL/wiki/Start-Moodle-dl-periodically-or-via-Telegram)'
        )
    else:
        Log.info(
            'If you want to run moodle-dl periodically, you can take a look at the wiki '
            + '(https://github.com/C0D3D3V/Moodle-DL/wiki/Start-Moodle-dl-periodically-or-via-Telegram)'
        )

    print('')

    Log.info('You can always do the additional configuration later with the --config option.')

    do_config = Cutie.prompt_yes_or_no('Do you want to make additional configurations now?')
    if do_config:
        ConfigWizard(config, opts).interactively_acquire_config()

    print('')
    Log.success('All set and ready to go!')
