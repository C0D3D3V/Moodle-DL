from abc import ABCMeta, abstractmethod

from utils.config_helper import ConfigHelper
from utils.version_recorder import CollectionOfChanges


class NotificationService:
    __metaclass__ = ABCMeta
    # This enables us to use the @abstractmethod-annotation
    # By using it, we make it only possible to instantiate a derived class if
    # every abstractmethod  has a concrete implementation in it.

    def __init__(self, config_helper: ConfigHelper):
        self.config_helper = config_helper

    @abstractmethod
    def interactively_configure(self) -> None:
        """
         Walks the User through the configuration of the Notification-Service
         through an CLI. It also tests and persists the gathered config.
        """
        pass

    @abstractmethod
    def notify_about_changes_in_results(self, changes: CollectionOfChanges) -> None:
        """
        Sends out a Notification to inform about detected changes for the
        Moodle-Account. The caller shouldn't care about if the sending was
        successful.
        @param changes: The detected changes.
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
