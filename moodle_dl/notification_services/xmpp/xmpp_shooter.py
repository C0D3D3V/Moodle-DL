import slixmpp


class XmppShooter(slixmpp.ClientXMPP):

    """
    A basic Slixmpp shooter that will log in, send a message,
    and then log out.
    """

    def __init__(self, jid, password, recipient, messages):
        super().__init__(jid, password)

        self.recipient = recipient
        self.messages = messages

        self.add_event_handler("session_start", self.start)

    async def start(self, event):
        self.send_presence()

        for message_content in self.messages:
            self.send_message(mto=self.recipient, mbody=message_content, mtype='chat')

        self.disconnect()
