import asyncio

import aioxmpp


class XmppShooter:

    """
    A basic XMPP shooter that will log in, send messages,
    and then log out.
    """

    def __init__(self, jid, password, recipient):
        self.g_jid = aioxmpp.JID.fromstr(jid)
        self.g_security_layer = aioxmpp.make_security_layer(password)

        self.to_jid = aioxmpp.JID.fromstr(recipient)

    def send(self, message):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.async_send_messages([message]))
        finally:
            loop.close()

    def send_messages(self, messages):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.async_send_messages(messages))
        finally:
            loop.close()

    async def async_send_messages(self, messages):
        client = aioxmpp.Client(
            self.g_jid,
            self.g_security_layer,
        )
        client.resumption_timeout = 0

        async with client.connected() as stream:
            for message_content in messages:
                msg = aioxmpp.Message(
                    to=self.to_jid,
                    type_=aioxmpp.MessageType.CHAT,
                )
                msg.body[None] = message_content

                await stream.send(msg)
