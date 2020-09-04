import os
import smtplib

from email.message import EmailMessage


class MailShooter:
    """
    Encapsulates the sending of notifcation-mails.
    """

    def __init__(self, sender: str, smtp_server_host: str, smtp_server_port: int, username: str, password: str):
        self.sender = sender
        self.smtp_server_host = smtp_server_host
        self.smtp_server_port = smtp_server_port
        self.username = username
        self.password = password

    def send(self, target: str, subject: str, html_content_with_cids: str, inline_png_cids_filenames: {str: str}):
        """
        Sends an email
        @params: All parameters required for sending
        """
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = target
        msg['Content-Type'] = 'text/html; charset="UTF-8"'

        msg.set_content('')

        msg.add_alternative(html_content_with_cids, subtype='html')

        # Adds the header images to the email
        for png_cid in inline_png_cids_filenames:
            full_path_to_png = os.path.abspath(
                os.path.join(os.path.dirname(__file__), inline_png_cids_filenames[png_cid])
            )
            with open(full_path_to_png, 'rb') as png_file:
                file_contents = png_file.read()
                msg.get_payload()[1].add_related(file_contents, 'image', 'png', cid=png_cid)

        # Send the email with starttls
        with smtplib.SMTP(self.smtp_server_host, self.smtp_server_port) as smtp_connection:
            smtp_connection.starttls()
            smtp_connection.login(self.username, self.password)
            smtp_connection.send_message(msg)
