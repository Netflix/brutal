import inspect
from Queue import Queue
from twisted.internet import reactor, task, defer, threads

from brutal.protocols.irc import IrcBotteFactory
from brutal.core.plugin import BotPlugin
from brutal.core.models import Event, Action

OFF = 0
ON = 1
DISCONNECTED = 20
CONNECTED = 30

class Bot(object):
    def __init__(self, name='test_bot', network=None, port=None, channels=None):
        #TODO: maybe support a custom internal key to keep track of bots, not just by 'name'...
        #TODO: if we do it by name, make sure we dont have name dupes, even between networks :-/

        self.name = name

        self.protocol_backend = None
        #todo: remove this, its only used in connect and str, useless, stops from having multiple connections
        self.type = 'irc'

        self.channels = channels or []
        # make this support multiple networks?
        self.network = network #(have networks read from a queue and use the origin bot to send)
        self.port = port # should have a check in here to default the port

        self.log = None

        #twisted factory
        self.factories = []

        #bot manager instance
        self.manager = None

        self.active_plugins = []
        self.state = OFF
        self.party_line = None

        self.commands = {}
        self.event_parsers = {}

    def new_action(self):
        a = Action(destination_bot=self)
        return a

    def build_event(self, event_data):
        #todo: needs to be safe
        channel = event_data['channel']
        type = event_data['type']
        meta = event_data['meta']

        server_info = event_data['server_info']
        event_version = event_data['event_version']

        e = Event(source_bot=self, channel=channel, type=type, meta=meta, server_info=server_info, version=event_version)
        return e

    def new_event(self, raw_event):
        if self.state >= ON:
            event = self.build_event(raw_event)
            d = self.handle_event(event)
            #event_deferred.pause()
            return d

    @defer.inlineCallbacks
    def handle_event(self, event):
        response = yield threads.deferToThread(self.process_event, event)
        defer.returnValue(event)


    def process_event(self, event):
        #run through event parsers
        for name, event_parser in self.event_parsers.items():
            response = event_parser(event)
            if type(response) in (str, unicode):
                a = self.new_action().msg(event.channel, response)
                event.add_response_action(a)

        #check cmds
        if event.cmd is not None and event.cmd in self.commands:
            #fix this...
            response = self.commands[event.cmd](event)
            if type(response) in (str, unicode):
                a = self.new_action().msg(event.channel, response)
                event.add_response_action(a)

        return event


#    def process_plugins(self, event):
#        if event.cmd:
#            if event.cmd in self.commands:
#                res = self.commands[event.cmd]()
#                print res
##        for plugin in self.active_plugins:
##            plugin.handle_event(event)
#        return event

    def start(self):
        self.state = ON
        self.build_plugins()
        #print 'enabled plugins:\n{0}'.format(repr(self.active_plugins))
        self.find_brutal_functions()
        #print 'LOADED COMMANDS:'
        #print repr(self.commands)
        #print 'LOADED EVENT PARSERS:'
        #print repr(self.event_parsers)
        self.connect()


    def find_brutal_functions(self):
        #load freestanding functions
        for module in self.manager.config.PLUGINS:
            self._register_brutal_plugin_functions(module)

        #load plugin class cmd methods
        for plugin_instance in self.active_plugins:
            self._register_brutal_plugin_class_functions(plugin_instance)

    def _register_brutal_plugin_functions(self, plugin_module):
        module_name = plugin_module.__name__
        for func_name, func in inspect.getmembers(plugin_module, inspect.isfunction):
            if getattr(func, '__brutal_cmd', False):
                command = (getattr(func, '__brutal_cmd_trigger', None) or func_name).lower()

                if command in self.commands:
                    command = module_name + '.' + command

                    if command in self.commands:
                        continue #fail better here...
                self.commands[command] = func
            elif getattr(func, '__brutal_parser', False):
                parser = func_name.lower()
                if parser in self.event_parsers:
                    parser = module_name + '.' + parser

                    if parser in self.event_parsers:
                        continue
                self.event_parsers[parser] = func

    def _register_brutal_plugin_class_functions(self, plugin_instance):
        class_name = plugin_instance.__class__.__name__.lower()
        for func_name, func in inspect.getmembers(plugin_instance, inspect.ismethod):
            if getattr(func, '__brutal_cmd', False):
                command = (getattr(func, '__brutal_cmd_command', None) or func_name).lower()

                if command in self.commands:
                    command = class_name + '.' + command

                    if command in self.commands:
                        continue #fail better here...
                self.commands[command] = func
            elif getattr(func, '__brutal_parser', False):
                parser = class_name + '.' + func_name.lower()
                if parser in self.event_parsers:
                    continue
                self.event_parsers[parser] = func

    def build_plugins(self):
        for plugin in BotPlugin.plugins:
            instance = plugin(self)
            instance.setup()
            self.active_plugins.append(instance)

    def connect(self): #master_event_handler):
        #maybe i should just remove the ability to pass in master_event_handler...
        if self.type == 'irc':
            self.factory = IrcBotteFactory(self.channels, nickname=self.name, bot=self)

        if self.factory is not None and self.network is not None and self.port is not None:
            reactor.connectTCP(self.network, self.port, self.factory)
            #connectSSL for ssl connections...

    def stop(self):
        """
        TODO: uh.... wut
        """
        if self.state >= ON:
            self.state = OFF

    def __str__(self):
        return '<Bot: {0}, {1}, {2}, {3}>'.format(self.name, self.type, self.network, self.port)

class BotManager(object):
    """
    Handles all bottes, responsible for spinning up and shutting down
    """
    #TODO: fill this shit out, needs to read config or handle config object?
    def __init__(self, config=None):
        if config is None:
            raise AttributeError, "No config passed to manager."
        self.config = config

        self.bottes = []
        # bot -> {partyline:,othershit?}
        # NETWORKED PARTY LINES WOULD BE HOT FIRE

        self.tasks = Queue()
        self.event_handler = None
        self.setup()

        self.delete_this = 0

    def setup(self):
        #self.event_handler = EventHandler()

        #check these, parse
        # this needs to change with support of multipe bots
        name = getattr(self.config, 'BOT_NAME')
        network = getattr(self.config, 'BOT_NETWORK')
        channels = getattr(self.config, 'BOT_CHANNELS')

        self.create_bot(name, network=network, port=6667, channels=channels)

    def update(self):
        #print 'manager loop called'
        pass


    def create_bot(self, *args, **kwargs):
        bot = Bot(*args, **kwargs)
        bot.manager = self
        # fire it up!
        bot.start()
        #todo: check if startup worked?
        self.bottes.append(bot)

    def start(self):
        """
        starts the manager
        """
        loop = task.LoopingCall(self.update)
        loop.start(30.0)
