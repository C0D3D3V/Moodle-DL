import xmpp

from moodle_dl.utils import check_verbose


class XmppShooter:
    def __init__(self, jid, password, recipient):
        self.jid = xmpp.protocol.JID(jid)
        self.connection = xmpp.Client(server=self.jid.getDomain(), debug=check_verbose())
        self.is_connected = False
        self.password = password
        self.recipient = xmpp.protocol.JID(recipient)

    def send(self, message):
        if not self.is_connected:
            self.connection.connect()
            self.connection.auth(user=self.jid.getNode(), password=self.password, resource=self.jid.getResource())
            if not hasattr(self.connection, 'Bind') or getattr(self.connection, 'Bind').session != 1:
                raise ConnectionError('XMPP Session could not be opend')
            self.is_connected = True

        self.connection.send(xmpp.protocol.Message(to=self.recipient, body=message))
