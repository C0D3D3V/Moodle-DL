from getpass import getpass

from aioxmpp.errors import StanzaError, UserError

from moodle_dl.config import ConfigHelper
from moodle_dl.notifications.mail.mail_formater import create_full_welcome_mail
from moodle_dl.notifications.mail.mail_shooter import MailShooter
from moodle_dl.notifications.telegram.telegram_shooter import TelegramShooter, RequestRejectedError
from moodle_dl.notifications.xmpp.xmpp_shooter import XmppShooter
from moodle_dl.types import MoodleDlOpts
from moodle_dl.utils import Cutie


class NotificationsWizard:
    def __init__(self, config: ConfigHelper, opts: MoodleDlOpts):
        self.config = config
        self.opts = opts

    def interactively_configure_all_services(self) -> None:
        services = [
            getattr(self, func)
            for func in dir(self)
            if callable(getattr(self, func))
            and func.startswith("interactively_configure_")
            and func != "interactively_configure_all_services"
        ]
        for service in services:
            service()

    def interactively_configure_mail(self) -> None:
        "Guides the user through the configuration of the mail notification."

        do_mail = Cutie.prompt_yes_or_no('Do you want to activate Notifications via mail?')

        if not do_mail:
            self.config.remove_property('mail')
        else:
            print('[The following Inputs are not validated!]')

            config_valid = False
            while not config_valid:
                sender = input('E-Mail-Address of the Sender:   ')
                server_host = input('Host of the SMTP-Server:   ')
                server_port = input('Port of the SMTP-Server [STARTTLS, default 587]:   ')
                if server_port == '':
                    print('Using default port 587!')
                    server_port = '587'
                username = input('Username for the SMTP-Server:   ')
                password = getpass('Password for the SMTP-Server [no output]:   ')
                target = input('E-Mail-Address of the Target:   ')

                print('Testing Mail-Config...')
                welcome_content = create_full_welcome_mail()
                mail_shooter = MailShooter(sender, server_host, int(server_port), username, password)
                try:
                    mail_shooter.send(target, 'Hey!', welcome_content[0], welcome_content[1])
                except OSError as e:
                    print(f'Error while sending the test mail: {str(e)}')
                    continue
                else:
                    input(
                        'Please check if you received the Welcome-Mail.'
                        + ' If yes, confirm with Return.\nIf not, exit'
                        + ' this program ([CTRL]+[C]) and try again later.'
                    )
                    config_valid = True

                raw_send_error_msg = ''
                while raw_send_error_msg not in ['y', 'n']:
                    raw_send_error_msg = input('Do you want to also get error reports sent by mail? [y/n]   ')
                do_send_error_msg = raw_send_error_msg == 'y'

                mail_cfg = {
                    'sender': sender,
                    'server_host': server_host,
                    'server_port': server_port,
                    'username': username,
                    'password': password,
                    'target': target,
                    'send_error_msg': do_send_error_msg,
                }

                self.config.set_property('mail', mail_cfg)

    def interactively_configure_telegram(self) -> None:
        "Guides the user through the configuration of the telegram notification."

        do_telegram = Cutie.prompt_yes_or_no('Do you want to activate Notifications via Telegram?')

        if not do_telegram:
            self.config.remove_property('telegram')
        else:
            print('[The following Inputs are not validated!]')
            print(
                'Open the following link for help in setting up telegram notifications:'
                + ' https://github.com/C0D3D3V/Moodle-DL/wiki/Telegram-Notification'
            )
            config_valid = False
            while not config_valid:
                telegram_token = input('Telegram Token:    ')
                telegram_chatID = input('Telegram Chat ID:   ')

                print('Testing Telegram-Config...')

                try:
                    telegram_shooter = TelegramShooter(telegram_token, telegram_chatID)
                    telegram_shooter.send('This is a test message from moodle-dl!')
                except (ConnectionError, RuntimeError, RequestRejectedError) as e:
                    print(f'Error while sending the test message: {str(e)}')
                    continue

                else:
                    input(
                        'Please check if you received the Testmessage.'
                        + ' If yes, confirm with Return.\nIf not, exit'
                        + ' this program ([CTRL]+[C]) and try again later.'
                    )
                    config_valid = True

                raw_send_error_msg = ''
                while raw_send_error_msg not in ['y', 'n']:
                    raw_send_error_msg = input('Do you want to also get error reports sent in telegram? [y/n]   ')

                do_send_error_msg = raw_send_error_msg == 'y'

                telegram_cfg = {
                    'token': telegram_token,
                    'chat_id': telegram_chatID,
                    'send_error_msg': do_send_error_msg,
                }

                self.config.set_property('telegram', telegram_cfg)

    def interactively_configure_xmpp(self) -> None:
        "Guides the user through the configuration of the xmpp notification."

        do_xmpp = Cutie.prompt_yes_or_no('Do you want to activate Notifications via XMPP?')

        if not do_xmpp:
            self.config.remove_property('xmpp')
        else:
            print('[The following Inputs are not validated!]')
            config_valid = False
            while not config_valid:
                sender = input('JID of the Sender:   ')
                password = getpass('Password for the Sender [no output]:   ')
                target = input('JID of the Target:   ')
                print('Testing XMPP-Config...')

                try:
                    xmpp_shooter = XmppShooter(sender, password, target)
                    xmpp_shooter.send('This is a test message from moodle-dl!')
                except (
                    ConnectionError,
                    StanzaError,
                    UserError,
                    OSError,
                    RuntimeError,
                ) as e:
                    print(f'Error while sending the test message: {str(e)}')
                    continue

                else:
                    input(
                        'Please check if you received the Testmessage.'
                        + ' If yes, confirm with Return.\nIf not, exit'
                        + ' this program ([CTRL]+[C]) and try again later.'
                    )
                    config_valid = True

                raw_send_error_msg = ''
                while raw_send_error_msg not in ['y', 'n']:
                    raw_send_error_msg = input('Do you want to also get error reports sent in xmpp? [y/n]   ')

                do_send_error_msg = raw_send_error_msg == 'y'

                xmpp_cfg = {
                    'sender': sender,
                    'password': password,
                    'target': target,
                    'send_error_msg': do_send_error_msg,
                }

                self.config.set_property('xmpp', xmpp_cfg)
