import os
import asyncio

import aioxmpp

from moodle_dl.utils import SslHelper


class XmppShooter:

    """
    A basic XMPP shooter that will log in, send messages,
    and then log out.
    """

    @staticmethod
    def my_ssl_factory():
        ssl_context = aioxmpp.security_layer.default_ssl_context()
        SslHelper.load_default_certs(ssl_context)
        return ssl_context

    def __init__(self, jid, password, recipient):
        self.g_jid = aioxmpp.JID.fromstr(jid)
        self.g_security_layer = aioxmpp.make_security_layer(password)._replace(
            ssl_context_factory=self.my_ssl_factory,
        )

        self.to_jid = aioxmpp.JID.fromstr(recipient)

        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def send(self, message):
        asyncio.run(self.async_send_messages([message]))

    def send_messages(self, messages):
        asyncio.run(self.async_send_messages(messages))

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
