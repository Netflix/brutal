from Queue import Queue

class Event(object):
    """
    Gets generated for every single event the bot _receives_.
    """

    def __init__(self, source_bot, channel, type, meta=None, server_info=None, version=None):
        #TODO: NOT GENERIC ENOUGH
        self.source_bot = source_bot
        # probably needs to know which protocol...

        self.channel = channel or '' #defaults to just the bots core log.
        self.type = type
        self.meta = meta or {}

        self.server_info = server_info or {}
        self.version = version or '1' #todo: figure out how to handle these...

        #TODO: this is temporary until i decide how i want to handle cmds
        self.cmd = self.parse_event_cmd()

        # this might be too heavy...
        self.response = Queue()

    def __repr__(self):
        return "<{0} {1}:{2}:{3}>".format(self.__class__.__name__, self.source_bot, self.type, self.channel)

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

    def parse_event_cmd(self, token=None):
        token = token or '!' #TODO: make this configurable
        cmd = None
        if 'msg' in self.meta and self.meta['msg'] is not None and type(self.meta['msg']) in (str, unicode):
            split = self.meta['msg'].split()
            if len(split):
                if split[0].startswith(token):
                    try:
                        cmd = split[0][1:]
                        args = split[1:]
                    except Exception:
                        pass
                    else:
                        self.meta['cmd'] = cmd
                        self.meta['args'] = args
        return cmd

    def add_response_action(self, action):
        if isinstance(action, Action):
            self.response.put(action)

#class ActionGroup

class Action(object):
    """
    used to define bot actions, mostly responses to incoming events
    possibly refactor due to similarities to events

    action types:
        msg
        join
        part
    """
    def __init__(self, destination_bot, channel=None, type=None, meta=None, server_info=None, version=None):
        #unsure
        self.destination_bot = destination_bot

        self.channel = channel
        self.type = type
        self.meta =  meta or {}

        self.server_info = server_info or {}
        self.version = version

    def __repr__(self):
        return "<{0} {1}:{2}:{3}>".format(self.__class__.__name__, self.destination_bot, self.type, self.channel)

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

    def msg(self, channel, msg):
        """
        send a msg to a channel
        """
        self.channel = channel
        self.type = 'msg'
        if msg is not None:
            self._add_to_meta('msg', msg)
        return self

    def join(self, channel, key=None):
        """
        if supported, join a chat channel
        """
        self.channel = channel
        self.type = 'join'
        if key is not None:
            self._add_to_meta('key', key)
        return self

    def part(self, channel, msg=None):
        """
        if supported, leave a chat channel the bot is currently in
        """
        self.channel = channel
        self.type = 'part'
        if msg is not None:
            self._add_to_meta('msg', msg)
        return self