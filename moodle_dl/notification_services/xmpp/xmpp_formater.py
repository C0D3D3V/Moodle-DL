from moodle_dl.notification_services.telegram.telegram_formater import TelegramFormater


class XmppFormater(TelegramFormater):
    @staticmethod
    def append_with_limit(new_line: str, one_msg_content: str, msg_list: [str]):
        """Appends a new line to a message string,
        if the string is to long it ist appended to the message list.
        Returns the new message string.

        Args:
            new_line (str): A new line to append to a message string
            one_msg_content (str): The current message string
            msg_list ([str]): The list of finished messages
        Returns:
            str: The new message
        """
        if len(one_msg_content) + len(new_line) >= 4096:
            msg_list.append(one_msg_content)
            return new_line
        else:
            return one_msg_content + new_line

    @classmethod
    def make_bold(cls, string: str) -> str:
        """
        Makes a string bold in a xmpp message
        """
        return '*' + string + '*'
