import logging
from collections import OrderedDict
from brutal.core.models import Action

from brutal.protocols.core import ProtocolBackend
# supported protocols - done for plugin access. kinda ugly
from brutal.protocols.irc import IrcBackend
from brutal.protocols.xmpp import XmppBackend
from brutal.protocols.testconsole import TestConsoleBackend


class ConnectionManager(object):
    """
    handles building and holding of connection clients
    """
    def __init__(self, config, bot):
        self.config = config
        self.bot = bot
        self.clients = OrderedDict()

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self._parse_config()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '<{0}: {1} clients>'.format(self.__class__.__name__, len(self.clients))

    def _parse_config(self):
        """
        setup clients based on the config
        """
        if isinstance(self.config, list):
            for conn_settings in self.config:
                conn = self._build_client(conn_settings)

                if conn is not None:
                    self.clients[conn.id] = conn
                else:
                    self.log.error('connection creation failed')
        else:
            self.log.error('invalid connection configuration, needs to be a list')

    def _build_client(self, conn_settings):
        if not isinstance(conn_settings, dict):
            self.log.error('invalid conn_settings passed to build_connection: {0!r}'.format(conn_settings))
            return

        if 'nick' not in conn_settings:
            conn_settings['nick'] = self.bot.nick

        protocol_name = conn_settings.get('protocol')
        if protocol_name is None:
            self.log.error('no protocol defined for connection: {0!r}'.format(conn_settings))
            return

        protocol_name = protocol_name.strip().lower()

        for protocol in ProtocolBackend.plugins:
            if protocol.protocol_name.lower() == protocol_name:
                #TODO: should probably try/except this
                try:
                    conn = protocol(bot=self.bot)
                    conn.configure(**conn_settings)
                except Exception as e:
                    self.log.exception('failed to build protocol: {0!r}'.format(e))
                else:
                    return conn

        self.log.error('unsupported protocol given: {0!r}'.format(protocol_name))

    def connect(self):
        """
        connect the actual connections to the reactor
        """
        for conn_id, conn in self.clients.items():
            conn.connect()

    def disconnect(self):
        """
        placeholder
        """
        pass

    def route_action(self, action):
        if isinstance(action, Action):
            self.log.debug('destination_bots: {0!r}'.format(action.destination_bots))
            self.log.debug('destination_client_ids: {0!r}'.format(action.destination_client_ids))
            self.log.debug('destination_rooms: {0!r}'.format(action.destination_rooms))

            if self.bot in action.destination_bots:
                for client_id in action.destination_client_ids:
                    if client_id in self.clients:
                        self.log.debug('queuing action {0!r} on client {1!r}'.format(action, self.clients[client_id]))
                        self.clients[client_id].queue_action(action)

    @property
    def default_connection(self):
        for client in self.clients:
            return client #.default_room
        self.log.error('unable to get default client on {0!r}'.format(self))

