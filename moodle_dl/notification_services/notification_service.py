from abc import ABCMeta, abstractmethod
from typing import List

from moodle_dl.config_service import ConfigHelper
from moodle_dl.download_service.url_target import URLTarget
from moodle_dl.state_recorder import Course


class NotificationService(metaclass=ABCMeta):
    """
    Common class for a notification service
    """

    def __init__(self, config: ConfigHelper):
        self.config = config

    @abstractmethod
    def interactively_configure(self) -> None:
        """
        Walks the User through the configuration of the Notification-Service
        through an CLI. It also tests and persists the gathered config.
        """
        pass

    @abstractmethod
    def notify_about_changes_in_moodle(self, changes: List[Course]) -> None:
        """
        Sends out a Notification to inform about detected changes for the
        Moodle-Account. The caller shouldn't care about if the sending was
        successful.
        @param changes: The detected changes per course.
        """
        pass

    @abstractmethod
    def notify_about_error(self, error_description: str) -> None:
        """
        Sends out a Notification to inform about an error encountered during
        the execution of the program.
        The caller shouldn't care about if the sending was successful.
        @param error_description: The error text.
        """
        pass

    @abstractmethod
    def notify_about_failed_downloads(self, failed_downloads: List[URLTarget]) -> None:
        """
        Sends out a Notification to inform about failed downloads encountered during
        the execution of the program.
        The caller shouldn't care about if the sending was successful.
        @param failed_downloads: A list of failed URLTargets.
        """
        pass
