RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"

# BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE


class Log:
    """
    Logs string to output with colors
    :param logString: the string that should be logged
    """

    @staticmethod
    def info(logString: str):
        print(COLOR_SEQ % 37 + logString + RESET_SEQ)

    @staticmethod
    def debug(logString: str):
        print(COLOR_SEQ % 36 + logString + RESET_SEQ)

    @staticmethod
    def warning(logString: str):
        print(COLOR_SEQ % 33 + logString + RESET_SEQ)

    @staticmethod
    def error(logString: str):
        print(COLOR_SEQ % 31 + logString + RESET_SEQ)

    @staticmethod
    def critical(logString: str):
        print(COLOR_SEQ % 35 + logString + RESET_SEQ)

    @staticmethod
    def success(logString: str):
        print(COLOR_SEQ % 32 + logString + RESET_SEQ)
