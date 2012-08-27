from twisted.internet import protocol, defer
from twisted.python import log
from twisted.words.protocols import irc

#from brutal.protocols.core import catch_error

class IrcBotte(irc.IRCClient):
    """
    Handles basic bot activity on irc. generates events and fires
    """
    protocol_name = 'irc'
    event_version = '1'

    def __init__(self):
        self.state_handler = None
        self.timer = None
        self.channel_users = {}
        self.hostname = 'trolololol' # <- nothing
        self.realname = 'brutal_bot' # <- ircname
        self.username = 'brutal' # <- ~____@...

    @property
    def nickname(self):
        return self.factory.nickname

    #-- server info
    def created(self, when):
        log.msg("created: %s" % when)

    def yourHost(self, info):
        log.msg("your host: %s" % info)

    def myInfo(self, servername, version, umodes, cmodes):
        log.msg("my info:\n\tservername: %s\n\tversion: %s\n\tumodes: %s\n\tcmodes: %s" % (servername, version, umodes, cmodes))

    def luserClient(self, info):
        log.msg("luserclient: %s" % info)

    def bounce(self, info):
        log.msg("bounce: %s" % info)

    def isupport(self, options):
        log.msg("isupport: %s" % options)
        log.msg("\n\nINTERNAL SUPPORTED._FEATURES:\n%r\n\n" % self.supported._features)

    def luserChannels(self, channels):
        log.msg('luserchannels: %r' % channels)

    def luserOp(self, ops):
        log.msg('luserop: %s' % ops)

    def luserMe(self, info):
        log.msg('luserme: %s' % info)

    #-- methods involving dis bot
    def privmsg(self, user, channel, message):
        """
        handle a new msg on irc
        """
        log.msg("privmsg:\n\tuser: %s\n\tchannel: %s\n\tmsg: %s" % (user, channel, message))

        nick, _, host = user.partition('!')
        message = message.strip()

        #command, sep, rest = message.lstrip('!').partition(' ')

        event_data = {'type':'priv_msg', 'channel':channel, 'meta':{'user':user, 'msg':message}}
        self._botte_event(event_data)

        #event = Event(self, self, 'msg', {'user':user, 'source':channel, 'msg':message})
        #self._botte_event(event)
#        if self.nickname in message:
#            self.msg(channel, "no :E")
#            log.msg("whois'n %s" % user)
#            log.msg(repr(user))
#            log.msg('derp:')
#            self.whois(user)

    def joined(self, channel):
        log.msg("joined %s" % channel)
        #self.say(channel, "hi guys!")# %s" % channel)
        #self.sendLine("NAMES %s" % channel)

    def left(self, channel):
        log.msg('left %s' % channel)

    def noticed(self, user, channel, message):
        # automatic replies MUST NEVER be sent in response to a NOTICE message
        log.msg("noticed:\n\tuser: %s\n\tchannel: %s\n\tmsg: %s" % (user, channel, message))

    def modeChanged(self, user, channel, set, modes, args):
        log.msg("mode changed:\n\tuser: %s\n\tchannel: %s\n\tset: %s\n\tmodes: %s\n\targs: %r" % (user, channel, set, modes, args))

    #pong

    def signedOn(self):
        for channel in self.factory.channels:
            self.join(channel)

    def kickedFrom(self, channel, kicker, message):
        log.msg("kicked from:\n\tchannel: %s\n\tkicker: %s\n\tmsg: %s" % (channel, kicker, message))

    #nickChanged

    #-- observed actions of others in a channel
    def userJoined(self, user, channel):
        log.msg("user joined:\n\tuser: %s\n\tchannel: %s" % (user, channel))

    def userLeft(self, user, channel):
        log.msg("user left:\n\tuser: %s\n\tchannel: %s" % (user, channel))

    def userQuit(self, user, quitMessage):
        log.msg("user quit:\n\tuser: %s\n\tquit msg: %s" % (user, quitMessage))

    def userKicked(self, kickee, channel, kicker, message):
        log.msg("user kicked:\n\tuser: %s\n\tchannel: %s\n\tkicker: %s\n\tmsg: %s" % (kickee, channel, kicker, message))

    def action(self, user, channel, data):
        log.msg("action:\n\tuser: %s\n\tchannel: %s\n\tdata: %r" % (user, channel, data))

    def topicUpdated(self, user, channel, newTopic):
        log.msg("topic update:\n\tuser: %s\n\tchannel: %s\n\ttopic: %s" % (user, channel, newTopic))

    def userRenamed(self, oldname, newname):
        log.msg("user renamed - old:%s new:%s" % (oldname, newname))

    #-- recv server info
    def receivedMOTD(self, motd):
        log.msg("server MOTD:\n%s" % "\n".join(motd))

    #--  custom
    def received_names(self, channel, nick_list):
        self.channel_users[channel] = nick_list
        #self.say(channel, "current users: %s" % ' '.join(nick_list))

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
        self.sendLine("NAMES %s" % channel)

    #-- lots hidden here... server->client
    def irc_PONG(self, prefix, params):
        """
        parse a server pong message
        we don't care about responses to our keepalive PINGS
        """
        #log.msg('PONG received:\n\tprefix: %r\n\t%r' % (prefix, params) )
        pass

    def irc_RPL_NAMREPLY(self, prefix, params):
        channel = params[2].lower()
        nicklist = []
        for name in params[3].split(' '):
            nicklist.append(name)
            #log.msg('\n\nNAMES RAW:\n\n%r\n\n%r' % (prefix, params)) #debug'n
        self.received_names(channel, nicklist)

    def irc_RPL_ENDOFNAMES(self, prefix, params):
        channel = params[1].lower()
        if channel not in self.channel_users:
            return

        log.msg('names output for %r:\n\t%r' % (channel, self.channel_users[channel])) #debug'n
        #self.received_names(channel, nicklist)
        #should fire here

    def irc_unknown(self, prefix, command, params):
        """ useful for debug'n weird irc data """
        log.msg('UNKNOWN RAW:\n\tprefix: %r\n\tcmd: %r\n\tparams: %r' % (prefix, command, params))

    #-- BOTTE SPECIFIC
    def _botte_event(self, raw_event):
        if 'meta' in raw_event:
            if 'user' in raw_event['meta']:
                try:
                    username = raw_event['meta']['user'].split('!', 1)[0]
                except Exception:
                    pass
                else:
                    raw_event['meta']['username'] = username

        raw_event['event_version'] = self.event_version or None

        # server info - protocol_name probably useles...
        server_info = {'protocol': self.protocol_name, 'hostname': self.hostname}
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
        if isinstance(d, defer.Deferred):
            #d.addErrback(catch_error)
            d.addCallback(self._botte_response) #<- attaches protocol response
            #d.callback(raw_event)

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


class IrcBotteFactory(protocol.ReconnectingClientFactory):
    protocol = IrcBotte

    def __init__(self, channels, nickname="brutalbot", bot=None):
        self.channels = channels
        self.nickname = nickname
        self.bot = bot

    def clientConnectionLost(self, connector, reason):
        log.msg("lost connection (%s): reconnecting" % reason)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.msg("connection failed (%s)" % reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def new_event(self, raw_event):
        """
        Event! creates a deferred for the bot to append too....
        """
        return self.bot.new_event(raw_event)
