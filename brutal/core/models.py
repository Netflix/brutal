import time
import logging

from brutal.core.constants import DEFAULT_EVENT_VERSION, DEFAULT_ACTION_VERSION


# class NetworkConfig(object):
#     __metaclass__ = PluginRoot
#     protocol_name = None
#
#     def __init__(self):
#         if self.protocol_name is None:
#             raise NotImplementedError
#


class Network(object):
    def __init__(self):
        self.protocol = None
        self.log_traffic = None
        self.server = None
        self.port = None
        self.use_ssl = None

        # network user / pass
        self.user = None
        self.password = None

        # rooms / users
        self.chats = None

    def parse_config(self, **kwargs):
        self.protocol = kwargs.get('protocol')
        self.log_traffic = kwargs.get('log_traffic', False)
        self.server = kwargs.get('server', 'localhost')
        self.port = kwargs.get('port')
        self.use_ssl = kwargs.get('use_ssl')

        self.nick = kwargs.get('nick')
        self.password = kwargs.get('password')

        if 'channels' in kwargs:
            self.rooms = kwargs.get('channels', [])
        elif 'rooms' in kwargs:
            self.rooms = kwargs.get('rooms', [])


class Chat(object):
    def __init__(self):
        # room id or user id
        self.id = None
        self.last_active = None

        self.users = None


class Room(Chat):
    pass


class User(Chat):
    pass


class Event(object):
    """
    This is the generic object which is used to handle objects received
    Gets generated for every single event the bot _receives_.
    """

    def __init__(self, source_bot, raw_details):  # channel, type, meta=None, server_info=None, version=None):
        """
        source_bot: the source bot the event was generated from

        details:
            client: if given, the source client the event was generated from
            type
            meta
            version
        """
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.source_bot = source_bot
        self.raw_details = raw_details
        #self.raw_line =
        self.time_stamp = time.time()

        self.event_version = DEFAULT_EVENT_VERSION
        self.event_type = None
        self.cmd = None
        self.args = None

        self.source_client = None
        self.source_client_id = None
        self.source_room = None
        self.scope = None

        self.meta = None
        self.from_bot = None

        # TODO: move so that the bot actually calls this and passes in its list of accepted tokens
        self.parse_details()

        # probably needs to know which protocol...
        # self.server_info = server_info or {}
        # self.version = version or '1' #todo: figure out how to handle these...

        # this might be too heavy...
        # self.response = Queue()

    def __repr__(self):
        return "<{0} {1}:{2}>".format(self.__class__.__name__, self.source_bot.nick, self.event_type)

    def __str__(self):
        return repr(self)

    def parse_details(self):
        if not isinstance(self.raw_details, dict):
            raise TypeError

        self.source_client = self.raw_details.get('client')
        self.source_client_id = self.raw_details.get('client_id')
        self.source_room = self.raw_details.get('channel') or self.raw_details.get('room')

        self.scope = self.raw_details.get('scope')
        self.event_type = self.raw_details.get('type')
        self.meta = self.raw_details.get('meta')
        self.from_bot = self.raw_details.get('from_bot')
        if self.from_bot is not True:
            self.from_bot = False

        if self.event_type == 'message' and isinstance(self.meta, dict) and 'body' in self.meta:
            res = self.parse_event_cmd(self.meta['body'])
            # if res is False:
            #     self.log.debug('event not parsed as a command')

    def check_message_match(self, starts_with=None, regex=None):
        """
        simple message matching to check for commands or general message structures,
        could lead to a crash because of the regex...
        """
        match = False
        if 'msg' in self.meta and self.meta['msg'] is not None and type(self.meta['msg']) in (str, unicode):
            if starts_with is not None:
                if self.meta['msg'].startswith(starts_with):
                    match = True
                else:
                    return False
            if regex is not None:
                if match:
                    match = True
                else:
                    return False
            return match

    def parse_event_cmd(self, body, token=None):
        token = token or '!'  # TODO: make this configurable
        if type(body) not in (str, unicode):
            return False

        split = body.split()
        if len(split):

            if split[0].startswith(token):
                try:
                    cmd = split[0][1:]
                    args = split[1:]
                except Exception as e:
                    self.log.exception('failed parsing cmd from {0!r}: {1!r}'.format(body, e))
                else:
                    self.event_type = 'cmd'
                    self.cmd = cmd
                    self.args = args
                    return True
        return False


class Action(object):
    """
    used to define bot actions, mostly responses to incoming events
    possibly refactor due to similarities to events

    action types:
        msg
        join
        part
    """
    def __init__(self, source_bot, source_event=None, destination_bots=None, destination_client_ids=None, rooms=None,
                 action_type=None, meta=None):
        """
        represents an action that the bot should handle.
        """
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.source_bot = source_bot
        self.source_event = source_event

        #TODO: this logic is so broken. fix
        # default to source_bot if no destinations given
        self.destination_bots = destination_bots or [self.source_bot, ]

        self.destination_client_ids = destination_client_ids
        self.destination_rooms = rooms
        #self.log.debug('source: {0!r}, destination: {1!r}'.format(self.source_bot, self.destination_bots))

        if source_event is not None:
            self.destination_client_ids = [self.source_event.source_client_id, ]
            self.destination_rooms = [source_event.source_room, ]

        # get client_id
        if self.destination_client_ids is None:
            if self.destination_bots:
                bot = self.destination_bots[0]

                conn_id = bot.connection_manager.default_connection

                if conn_id is not None:
                    self.destination_client_ids = [conn_id, ]
                else:
                    self.log.error('no default connections on {0!r}'.format(bot))
                    raise AttributeError

            else:
                self.log.error('no destination bots for action')
                raise AttributeError

        if self.destination_rooms is None:
            self.destination_rooms = []
            #TODO: fix this 'try all the things' method
            for bot in self.destination_bots:
                for conn_id in self.destination_client_ids:
                    if conn_id in bot.connection_manager.clients:
                        room = bot.connection_manager.clients[conn_id].default_room
                        if room is not None:
                            self.destination_rooms.append(room)

        self.time_stamp = time.time()
        self.action_version = DEFAULT_ACTION_VERSION

        self.scope = None
        if self.source_event is not None:
            self.scope = self.source_event.scope

        self.action_type = action_type
        self.meta = meta or {}

    def __repr__(self):
        return "<{0} {1}:{2} dest:{3}>".format(self.__class__.__name__, self.source_bot.nick, self.action_type,
                                               [bot.nick for bot in self.destination_bots])

    def _is_valid(self):
        """
        check contents of action to ensure that it has all required fields.
        """
        return True

    def _add_to_meta(self, key, value):
        if key is not None and value is not None:
            if type(self.meta) is dict:
                self.meta[key] = value
                return True

    def msg(self, msg, room=None):
        """
        send a msg to a room
        """
        if room:
            self.destination_room = room

        self.action_type = 'message'
        if msg is not None:
            self._add_to_meta('body', msg)
        return self

    def join(self, channel, key=None):
        """
        if supported, join a rooml
        """
        self.channel = channel
        self.type = 'join'
        if key is not None:
            self._add_to_meta('key', key)
        return self

    def part(self, channel, msg=None):
        """
        if supported, leave a room the bot is currently in
        """
        self.channel = channel
        self.type = 'part'
        if msg is not None:
            self._add_to_meta('msg', msg)
        return self