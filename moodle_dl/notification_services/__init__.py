from typing import List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.notification_services.notification_service import NotificationService

from moodle_dl.notification_services.console.console_service import ConsoleService

from moodle_dl.notification_services.mail.mail_service import MailService  # noqa: F401
from moodle_dl.notification_services.telegram.telegram_service import TelegramService  # noqa: F401
from moodle_dl.notification_services.xmpp.xmpp_service import XmppService  # noqa: F401

REMOTE_SERVICES = [Class for name, Class in globals().items() if name.endswith('Service') and name != 'ConsoleService']
ALL_SERVICES = [ConsoleService] + REMOTE_SERVICES


def get_remote_notify_services(config: ConfigHelper) -> List[NotificationService]:
    result_list = []
    for service in REMOTE_SERVICES:
        result_list.append(service(config))
    return result_list


def get_all_notify_services(config: ConfigHelper) -> List[NotificationService]:
    result_list = []
    for service in ALL_SERVICES:
        result_list.append(service(config))
    return result_list
