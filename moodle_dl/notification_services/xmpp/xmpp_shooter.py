from moodle_dl.notification_services.xmpp.xmpp_bot import XmppBot


class XmppShooter:
    """
    Encapsulates the sending of notification-messages.
    """

    def __init__(self, xmpp_sender: str, xmpp_password: str, xmpp_target: str):
        self.xmpp_sender = xmpp_sender
        self.xmpp_password = xmpp_password
        self.xmpp_target = xmpp_target

    def send(self, message: str):
        xmpp = XmppBot(self.xmpp_sender, self.xmpp_password, self.xmpp_target, message)
        xmpp.register_plugin('xep_0030')  # Service Discovery
        xmpp.register_plugin('xep_0199')  # XMPP Ping

        # Connect to the XMPP server and start processing XMPP stanzas.
        xmpp.connect()
        xmpp.process(forever=False)
