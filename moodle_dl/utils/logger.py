RESET_SEQ = '\033[0m'
COLOR_SEQ = '\033[1;%dm'

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)


class Log:
    """
    Logs a given string to output with colors
    :param logString: the string that should be logged

    The string functions returns the strings that would be logged.
    """

    @staticmethod
    def info_str(logString: str):
        """
        Returns a string representation of a string.

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % WHITE + logString + RESET_SEQ

    @staticmethod
    def special_str(logString: str):
        """
        Returns a string with the given string.

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % BLUE + logString + RESET_SEQ

    @staticmethod
    def debug_str(logString: str):
        """
        Return debug string

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % CYAN + logString + RESET_SEQ

    @staticmethod
    def warning_str(logString: str):
        """
        Return a warning string

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % YELLOW + logString + RESET_SEQ

    @staticmethod
    def error_str(logString: str):
        """
        Returns a string representing the error message.

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % RED + logString + RESET_SEQ

    @staticmethod
    def critical_str(logString: str):
        """
        Return a string representation of the log file

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % MAGENTA + logString + RESET_SEQ

    @staticmethod
    def success_str(logString: str):
        """
        Returns a string of a success message

        Args:
            logString: (str): write your description
        """
        return COLOR_SEQ % GREEN + logString + RESET_SEQ

    @staticmethod
    def info(logString: str):
        """
        Prints a message to the log file.

        Args:
            logString: (str): write your description
        """
        print(Log.info_str(logString))

    @staticmethod
    def special(logString: str):
        """
        Prints a string to the log file

        Args:
            logString: (str): write your description
        """
        print(Log.special_str(logString))

    @staticmethod
    def debug(logString: str):
        """
        Prints a message

        Args:
            logString: (str): write your description
        """
        print(Log.debug_str(logString))

    @staticmethod
    def warning(logString: str):
        """
        Prints a warning

        Args:
            logString: (str): write your description
        """
        print(Log.warning_str(logString))

    @staticmethod
    def error(logString: str):
        """
        Prints an error message

        Args:
            logString: (str): write your description
        """
        print(Log.error_str(logString))

    @staticmethod
    def critical(logString: str):
        """
        Print a critical log string

        Args:
            logString: (str): write your description
        """
        print(Log.critical_str(logString))

    @staticmethod
    def success(logString: str):
        """
        Prints the message

        Args:
            logString: (str): write your description
        """
        print(Log.success_str(logString))
