import logging
from twisted.internet import reactor, protocol
from twisted.python import log
from twisted.words.protocols import irc

from brutal.protocols.core import ProtocolBackend
#from brutal.protocols.core import catch_error

IRC_DEFAULT_PORT = 6667

# OLD
# def irc_event_parser(raw_event):
#     if 'meta' in raw_event:
#         if 'user' in raw_event['meta']:
#             try:
#                 username = raw_event['meta']['user'].split('!', 1)[0]
#             except KeyError:
#                 pass
#             else:
#                 raw_event['meta']['username'] = username
#
#     raw_event['event_version'] = event_version or None
#
#     # server info - protocol_name probably useles...
#     #server_info = {'protocol': self.__class__.__name__, 'hostname': self.hostname}
#     #hostname gets changed on connection RPL_WELCOMEMSG
#     try:
#         server_info['addr'] = transport.addr[0]
#     except Exception:
#         server_info['addr'] = None
#     try:
#         server_info['port'] = transport.addr[1]
#     except Exception:
#         server_info['port'] = None
#
#     raw_event['server_info'] = server_info
#
#     #this needs to return a defered... should use maybedeferred?
#     d = self.factory.new_event(raw_event)


class IrcBotProtocol(irc.IRCClient):
    """
    Handles basic bot activity on irc. generates events and fires
    """
    event_version = '1'

    def __init__(self):
        self.state_handler = None
        self.timer = None
        self.channel_users = {}
        self.hostname = 'trolololol'  # <- nothing
        self.realname = 'brutal_bot'  # <- ircname
        self.username = 'brutal'  # <- ~____@...

    @property
    def nickname(self):
        return self.factory.nickname

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.factory.conn = self

    #-- server info
    def created(self, when):
        log.msg('created: {0!r}'.format(when), logLevel=logging.DEBUG)

    def yourHost(self, info):
        log.msg('yourHost: {0!r}'.format(info), logLevel=logging.DEBUG)

    def myInfo(self, servername, version, umodes, cmodes):
        log.msg('myInfo - servername: {0!r}, version: {1!r}, umodes: {2!r}, cmodes: {3!r}'.format(servername, version,
                                                                                                  umodes, cmodes),
                logLevel=logging.DEBUG)

    def luserClient(self, info):
        log.msg('luserClient: {0!r}'.format(info), logLevel=logging.DEBUG)

    def bounce(self, info):
        log.msg('bounce: {0!r}' % info, logLevel=logging.DEBUG)

    def isupport(self, options):
        log.msg('isupport: supported._features {0!r}'.format(self.supported._features), logLevel=logging.DEBUG)

    def luserChannels(self, channels):
        log.msg('luserChannels: {0!r}'.format(channels), logLevel=logging.DEBUG)

    def luserOp(self, ops):
        log.msg('luserOp: {0!r}'.format(ops), logLevel=logging.DEBUG)

    def luserMe(self, info):
        log.msg('luserMe: {0!r}'.format(info), logLevel=logging.DEBUG)

    #-- methods involving dis bot
    def privmsg(self, user, channel, message):
        """
        handle a new msg on irc
        """
        log.msg('privmsg - user: {0!r}, channel: {1!r}, msg: {2!r}'.format(user, channel, message),
                logLevel=logging.DEBUG)

        nick, _, host = user.partition('!')
        message = message.strip()

        #command, sep, rest = message.lstrip('!').partition(' ')

        event_data = {'type': 'priv_msg',
                      'channel': channel,
                      'meta': {
                          'user': user,
                          'msg': message}}

        self._botte_event(event_data)

        #event = Event(self, self, 'msg', {'user':user, 'source':channel, 'msg':message})
        #self._botte_event(event)
#        if self.nickname in message:
#            self.msg(channel, 'no :E')
#            log.msg('whois'n %s' % user)
#            log.msg(repr(user))
#            log.msg('derp:')
#            self.whois(user)

    def joined(self, channel):
        log.msg('joined: {0!r}'.format(channel), logLevel=logging.DEBUG)
        #self.say(channel, 'hi guys!')# %s' % channel)
        #self.sendLine('NAMES %s' % channel)

    def left(self, channel):
        log.msg('left: {0!r}'.format(channel), logLevel=logging.DEBUG)

    def noticed(self, user, channel, message):
        # automatic replies MUST NEVER be sent in response to a NOTICE message
        log.msg('noticed - user: {0!r}, channel: {1!r}, msg: {2!r}'.format(user, channel, message),
                logLevel=logging.DEBUG)

    def modeChanged(self, user, channel, set, modes, args):
        log.msg('modeChanged - user: {0!r}, channel: {1!r}, set: {2!r}, modes: {3!r}, args: {4!r}'.format(user, channel,
                                                                                                          set, modes,
                                                                                                          args),
                logLevel=logging.DEBUG)

    #pong

    def signedOn(self):
        for channel in self.factory.channels:
            if isinstance(channel, tuple):
                #TODO: confirm len and
                self.join(channel[0], channel[1])
            else:
                self.join(channel)

    def kickedFrom(self, channel, kicker, message):
        log.msg('kickedFrom - channel: {0!r}, kicker: {2!r}, msg: {3!r}'.format(channel, kicker, message),
                logLevel=logging.DEBUG)

    #nickChanged
    #TODO: track dis

    #-- observed actions of others in a channel
    def userJoined(self, user, channel):
        log.msg('userJoined - user: {0!r}, channel: {1!r}'.format(user, channel), logLevel=logging.DEBUG)

    def userLeft(self, user, channel):
        log.msg('userLeft - tuser: {0!r}, channel: {1!r}'.format(user, channel), logLevel=logging.DEBUG)

    def userQuit(self, user, quitMessage):
        log.msg('userQuit - user: {0!r}, quit msg: {1!r}'.format(user, quitMessage), logLevel=logging.DEBUG)

    def userKicked(self, kickee, channel, kicker, message):
        log.msg('userKicked - user: {0!r}, channel: {1!r}, kicker: {2!r}, msg: {3!r}'.format(kickee, channel, kicker,
                                                                                             message),
                logLevel=logging.DEBUG)

    def action(self, user, channel, data):
        log.msg('action - user: {0!r}, channel: {1!r}, data: {2!r}'.format(user, channel, data), logLevel=logging.DEBUG)

    def topicUpdated(self, user, channel, newTopic):
        log.msg('topicUpdated - user: {0!r}, channel: {1!r}, topic: {2!r}'.format(user, channel, newTopic),
                logLevel=logging.DEBUG)

    def userRenamed(self, oldname, newname):
        log.msg('userRenamed - old: {0!r}, new: {1!r}'.format(oldname, newname), logLevel=logging.DEBUG)

    #-- recv server info
    def receivedMOTD(self, motd):
        log.msg('receivedMOTD: {0!r}'.format(motd), logLevel=logging.DEBUG)

    #--  custom
    def received_names(self, channel, nick_list):
        self.channel_users[channel] = nick_list
        #self.say(channel, 'current users: {0!r}'.format(nick_list)

    #-- client cmds
    # join(self, channel, key=None)
    # leave(self, channel, reason=None)
    # kick(self, channel, user, reason=None)
    # invite(self, user, channel)
    # topic(self, channel, topic=None)
    # mode(self, chan, set, modes, limit = None, user = None, mask = None)
    # say(self, channel, message, length=None) #wtf is this?
    # msg(self, user, message, length=None)
    # notice(self, user, message)
    # away(self, message='')
    # back(self)
    # whois(self, nickname, server=None)
    # register(self, nickname, hostname='foo', servername='bar')
    # setNick(self, nickname)
    # quit(self, message = '')

    #-- user input commands, client-> client
    # describe(self, channel, action)
    #ping
    #dccSend
    #dccResume
    #dccAcceptResume

    #-- custom protocol stuff
    def names(self, channel):
        channel = channel.lower()
        self.sendLine('NAMES {0}'.format(channel))

    #-- lots hidden here... server->client
    def irc_PONG(self, prefix, params):
        """
        parse a server pong message
        we don't care about responses to our keepalive PINGS
        """
        log.msg('irc_PONG - prefix: {0!r}, params: {1!r}'.format(prefix, params), logLevel=logging.DEBUG)

    def irc_RPL_NAMREPLY(self, prefix, params):
        #log.msg('irc_RPL_NAMREPLY - prefix: {0!r}, {1!r}'.format(prefix, params), logLevel=logging.DEBUG)
        channel = params[2].lower()
        nicklist = []
        for name in params[3].split(' '):
            nicklist.append(name)

        self.received_names(channel, nicklist)

    def irc_RPL_ENDOFNAMES(self, prefix, params):
        channel = params[1].lower()
        if channel not in self.channel_users:
            return

        log.msg('names output {0!r}: {1!r}'.format(channel, self.channel_users[channel]), logLevel=logging.DEBUG)
        #self.received_names(channel, nicklist)
        #should fire here

    def irc_unknown(self, prefix, command, params):
        """ useful for debug'n weird irc data """
        log.msg('irc_unknown - prefix: {0!r}, cmd: {1!r}, params: {2!r}'.format(prefix, command, params),
                logLevel=logging.DEBUG)

    #-- BOTTE SPECIFIC
    def _botte_event(self, raw_event):
        if 'meta' in raw_event:
            if 'user' in raw_event['meta']:
                try:
                    username = raw_event['meta']['user'].split('!', 1)[0]
                except KeyError:
                    pass
                else:
                    raw_event['meta']['username'] = username

        raw_event['event_version'] = self.event_version or None

        # server info - protocol_name probably useles...
        server_info = {'protocol': self.__class__.__name__, 'hostname': self.hostname}
        #hostname gets changed on connection RPL_WELCOMEMSG
        try:
            server_info['addr'] = self.transport.addr[0]
        except Exception:
            server_info['addr'] = None
        try:
            server_info['port'] = self.transport.addr[1]
        except Exception:
            server_info['port'] = None

        raw_event['server_info'] = server_info

        #this needs to return a defered... should use maybedeferred?
        d = self.factory.new_event(raw_event)
        # if isinstance(d, defer.Deferred):
        #     #d.addErrback(catch_error)
        #     d.addCallback(self._botte_response) #<- attaches protocol response
        #     #d.callback(raw_event)

    def _botte_response(self, event):
        #TODO: rather than parsing through what we know is a queue, would be better to pass queue initially, or use other datatype
        while not event.response.empty():
            # if i want to rate limit these, i should group them so that sets get executed together...
            action = event.response.get()
            self._botte_parse_action(action)

    def _botte_parse_action(self, action):
        if action.type == 'msg':
            if 'msg' in action.meta and action.meta['msg'] is not None and len(action.meta['msg']):
                self.say(action.channel, action.meta['msg'])
        elif action.type == 'join':
            if 'key' in action.meta and action.meta['key'] is not None and len(action.meta['key']):
                key = action.meta['key']
            else:
                key = None
            self.join(action.channel, key=key)
        elif action.type == 'part':
            if 'msg' in action.meta and action.meta['msg'] is not None and len(action.meta['msg']):
                msg = action.meta['msg']
            else:
                msg = None
            self.leave(action.channel, msg)


class SimpleIrcBotProtocol(irc.IRCClient):
    """
    Handles basic bot activity on irc. generates events and fires
    """
    event_version = '1'

    def __init__(self):
        self.channel_users = {}
        #TODO: accept these as init vars
        self.hostname = 'brutal_bot'
        self.realname = 'brutal_bot'
        self.username = 'brutal_bot'

    @property
    def nickname(self):
        return self.factory.nickname

    @property
    def channels(self):
        return self.factory.channels

    def privmsg(self, user, channel, message):
        """
        handle a new msg on irc
        """
        log.msg('privmsg - user: {0!r}, channel: {1!r}, msg: {2!r}'.format(user, channel, message),
                logLevel=logging.DEBUG)

        nick, _, host = user.partition('!')
        message = message.strip()

        # parse if we're the owner / message was to bot directly
        if channel == self.nickname:
            event_data = {'type': 'message', 'scope': 'private', 'meta': {'from': user, 'body': message}}
        else:
            event_data = {'type': 'message', 'scope': 'public', 'channel': channel, 'meta': {'from': user,
                                                                                             'body': message}}

        self._bot_process_event(event_data)

    def action(self, user, channel, data):
        """
        handle a new msg on irc
        """
        log.msg('action - user: {0!r}, channel: {1!r}, data: {2!r}'.format(user, channel, data), logLevel=logging.DEBUG)

        nick, _, host = user.partition('!')
        data = data.strip()

        # parse if we're the owner / message was to bot directly
        if channel == self.nickname:
            event_data = {'type': 'message', 'scope': 'private', 'meta': {'from': user, 'body': data, 'emote': True}}
        else:
            event_data = {'type': 'message', 'scope': 'public', 'channel': channel, 'meta': {'from': user, 'body': data,
                                                                                             'emote': True}}

        self._bot_process_event(event_data)

    def signedOn(self):
        for channel in self.channels:
            if isinstance(channel, tuple):
                if len(channel) > 1:
                    try:
                        channel, key = channel
                    except ValueError:
                        log.err('unable to parse channel/key combo from: {0!r}'.format(channel))
                    else:
                        self.join(channel=channel, key=key)
                else:
                    self.join(channel=channel[0])
            else:
                self.join(channel)

    def irc_unknown(self, prefix, command, params):
        """
        useful for debug'n weird irc data
        """
        log.msg('irc_unknown - prefix: {0!r}, cmd: {1!r}, params: {2!r}'.format(prefix, command, params),
                logLevel=logging.DEBUG)

    #-- BOT SPECIFIC
    def _bot_process_event(self, raw_event):
        """
        passes raw data to bot
        """
        self.factory.new_event(raw_event)

    def _bot_process_action(self, action):
        log.msg('irc acting on {0!r}'.format(action), logLevel=logging.DEBUG)
        if action.action_type == 'message':
            body = action.meta.get('body')
            if body:
                dest = action.destination_room
                if dest:
                    if dest[0] == '#':
                        self.say(dest, body)
                    else:
                        self.msg(dest, body)


class IrcBotClient(protocol.ReconnectingClientFactory):
    protocol = SimpleIrcBotProtocol

    def __init__(self, channels, nickname, backend=None):
        self.channels = channels
        self.nickname = nickname
        self.backend = backend

        # this might be bad?
        self.current_conn = None

    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self

        # adding this
        self.current_conn = p

        return p

    def clientConnectionLost(self, connector, reason):
        self.current_conn = None
        log.msg('connection lost, reconnecting: ({0!r})'.format(reason), logLevel=logging.DEBUG)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.current_conn = None
        log.msg('connection failed: {0!r}'.format(reason), logLevel=logging.DEBUG)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def new_event(self, event):
        """
        Event! creates a deferred for the bot to append too....
        """
        if self.backend:
            self.backend.handle_event(event)

    def handle_action(self, action):
        if self.current_conn is not None:
            self.current_conn._bot_process_action(action)
        else:
            log.err('connection not active')


class IrcBackend(ProtocolBackend):
    """
    parses config options for irc protocol, responsible for handling events
    """
    protocol_name = 'irc'

    def configure(self, *args, **kwargs):
        #TODO: add log_traffic for IRC
        self.log_traffic = kwargs.get('log_traffic', False)
        self.server = kwargs.get('server', 'localhost')
        self.port = kwargs.get('port', IRC_DEFAULT_PORT)
        self.use_ssl = kwargs.get('use_ssl', False)

        self.nick = kwargs.get('nick')
        self.password = kwargs.get('password')

        self.rooms = kwargs.get('channels') or kwargs.get('rooms', [])

        self.client = IrcBotClient(self.rooms, nickname=self.nick, backend=self)

    def connect(self, *args, **kwargs):
        """
        starts connection on reactor
        """
        # if use_ssl:
        #     reactor.connectSSL
        log.msg('connecting to {0}:{1} with nick {2!r}'.format(self.server, self.port, self.nick),
                logLevel=logging.DEBUG)
        reactor.connectTCP(self.server, self.port, self.client)

    def handle_action(self, action):
        self.client.handle_action(action)