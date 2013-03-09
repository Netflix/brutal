import uuid
import inspect
import logging

from twisted.internet import reactor, task, defer, threads
from twisted.python import log

from brutal.protocols.core import ProtocolBackend
from brutal.core.plugin import BotPlugin
from brutal.core.models import Event, Action
from brutal.protocols.irc import IrcBotProtocol
#from brutal.protocols.jabber import

from brutal.core.constants import *


class Bot(object):
    def __init__(self, nick, connections, *args, **kwargs):
        #TODO: maybe support a custom internal key to keep track of bots, not just by 'name'...
        #TODO: if we do it by name, make sure we dont have name dupes, even between networks :-/

        self.id = str(uuid.uuid1())
        log.msg('starting bot with nick: {0!r}'.format(nick), logLevel=logging.DEBUG)
        self.nick = nick
        self.connections = []

        #bot manager instance
        self.manager = None

        # setup this bots event queue / consumer
        self.event_queue = defer.DeferredQueue()
        self._consume_events(self.event_queue)

        # build connections
        self._parse_connections(connections)
        log.msg('connections on {0!r}: {1!r}'.format(self.nick, self.connections))

        self.active_plugins = []
        self.state = OFF
        self.party_line = None

        self.commands = {}
        self.event_parsers = {}

    def __repr__(self):
        return '<{0}: {1!r} ({2!s})>'.format(self.__class__.__name__, self.nick, self.id)

    def __str__(self):
        return repr(self)

    # CORE

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

    # review
    def stop(self):
        """
        TODO: uh.... wut
        """
        if self.state >= ON:
            self.state = OFF

    # review
    def pause(self):
        """
        placeholder
        """
        pass

    # CONNECTIONS

    def _parse_connections(self, config_connections):
        if isinstance(config_connections, list):
            for conn_settings in config_connections:
                conn = self._build_connection(conn_settings)

                if conn is not None:
                    self.connections.append(conn)
                else:
                    log.err('connection creation failed')
        else:
            log.err('invalid connection configuration, needs to be a list')

    def _build_connection(self, conn_settings):
        if not isinstance(conn_settings, dict):
            log.err('invalid conn_settings passed to build_connection: {0!r}'.format(conn_settings))
            return

        if 'nick' not in conn_settings:
            conn_settings['nick'] = self.nick

        protocol_name = conn_settings.get('protocol')
        if protocol_name is None:
            log.err('no protocol defined for connection: {0!r}'.format(conn_settings))
            return
        protocol_name = protocol_name.strip().lower()

        for protocol in ProtocolBackend.plugins:
            if protocol.protocol_name.lower() == protocol_name:
                #TODO: should probably try/except this
                try:
                    conn = protocol(bot=self)
                    conn.configure(**conn_settings)
                except Exception as e:
                    log.err('failed to build protocol: {0!r}'.format(e))
                else:
                    return conn
            else:
                log.err('unsupported protocol given: {0!r}'.format(protocol_name))

    def connect(self):
        """
        connect the actual connections to the reactor
        """
        for conn in self.connections:
            conn.connect()

    def disconnect(self):
        """
        placeholder
        """
        pass

    # EVENT QUEUE
    # default event consumer queue.
    def _consume_events(self, queue):
        def consumer(event):
            # check if Event, else try to make it one
            if not isinstance(event, Event):
                try:
                    event = self.build_event(event)
                except Exception as e:
                    log.err('unable to parse data to Event, {0!r}: {1!r}'.format(event, e))
                    event = None

            if event is not None:
                log.msg('EVENT on {0!r}: {1!r}'.format(self, event), logLevel=logging.DEBUG)
                res = defer.maybeDeferred(self.process_event, event)
                # res.addCallback(process_result)

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def new_event(self, event):
        """
        this is what protocol backends call when they get an event.
        """
        self.event_queue.put(event)

    # PLUGIN SYSTEM #################################################

    def build_plugins(self):
        """
        instantiates each plugin for this bot.
        """
        for plugin in BotPlugin.plugins:
            instance = plugin(self)
            instance.setup()
            self.active_plugins.append(instance)

    def find_brutal_functions(self):
        """
        TODO: add default plugins

        for this bot, load all the plugins
        - find commands
        - find event handlers
        - register both.
        """

        #load freestanding functions
        for module in self.manager.config.PLUGINS:
            self._register_brutal_plugin_functions(module)

        #load plugin class cmd methods
        for plugin_instance in self.active_plugins:
            self._register_brutal_plugin_class_functions(plugin_instance)

    def _register_brutal_plugin_functions(self, plugin_module):
        module_name = plugin_module.__name__

        # step through all functions in module
        for func_name, func in inspect.getmembers(plugin_module, inspect.isfunction):
            if getattr(func, '__brutal_cmd', False):
                # function has been decorated with @cmd, register trigger or pull function name
                log.msg('register cmd {0!r} from module {1!r}'.format(func_name, module_name), logLevel=logging.DEBUG)
                command = (getattr(func, '__brutal_cmd_trigger', None) or func_name).lower()

                if command in self.commands:
                    command = module_name + '.' + command

                    if command in self.commands:
                        log.err('command already registered with this trigger: {0!r}'.format(command))
                        continue  # fail better here...

                # keeps track of all registered commands
                self.commands[command] = func

            # parse all the event parsers
            #TODO: read the type and put in the proper queue, change event_parsers to a dict?
            # confirm event_type is a string? do this in the decorator?
            elif getattr(func, '__brutal_event', False):
                event_parser = func_name.lower()
                if event_parser in self.event_parsers:
                    event_parser = module_name + '.' + event_parser

                    if event_parser in self.event_parsers:
                        continue
                log.msg('registering event parser {0!r} from module {1!r}'.format(func_name, module_name),
                        logLevel=logging.DEBUG)
                self.event_parsers[event_parser] = func

    def _register_brutal_plugin_class_functions(self, plugin_instance):
        class_name = plugin_instance.__class__.__name__.lower()
        for func_name, func in inspect.getmembers(plugin_instance, inspect.ismethod):
            if getattr(func, '__brutal_cmd', False):
                log.msg('registering cmd {0!r} from class {1!r}'.format(func_name, class_name), logLevel=logging.DEBUG)
                command = (getattr(func, '__brutal_cmd_command', None) or func_name).lower()

                if command in self.commands:
                    command = class_name + '.' + command

                    if command in self.commands:
                        continue  # fail better here...
                self.commands[command] = func
            elif getattr(func, '__brutal_event', False):
                parser = class_name + '.' + func_name.lower()
                if parser in self.event_parsers:
                    continue
                log.msg('registering event parser {0!r} from class {1!r}'.format(func_name, class_name),
                        logLevel=logging.DEBUG)
                self.event_parsers[parser] = func

    # OLD

    def new_action(self):
        a = Action(destination_bot=self)
        return a

    def build_event(self, event_data):
        #todo: needs to be safe
        # this should probably be moved into the model

        #{'connection_id': '9ee03700-8869-11e2-a78f-406c8f1e1202',
        # 'connection': <IrcBackend 9ee03700-8869-11e2-a78f-406c8f1e1202>,
        # 'meta': {'body': '!ping',
        #          'from': 'cbertram!~cbertram@dc1-corp.netflix.com'},
        # 'scope': 'public',
        # 'type': 'message',
        # 'channel': '#wat'

        # source:
        #   <connection>
        #   <room>
        # type: <message>
        # scope: <public>
        # meta: <meta>

        e = Event(source_bot=self, raw_details=event_data)
        # channel=channel, type=event_type, meta=metadata, server_info=server_info,#version=event_version)
        return e

    # @defer.inlineCallbacks
    # # old & busted.
    # def handle_event(self, event):
    #     response = yield threads.deferToThread(self.process_event, event)
    #     defer.returnValue(event)

    # DAT NEW HOT FIRE CMD EXECUTION
    @defer.inlineCallbacks
    def process_event(self, event):
        #TODO: this needs some love
        # wrap everything in try/except
        if not isinstance(event, Event):
            log.err('invalid event, ignoring: {0!r}'.format(event))
            raise

        #run through event parsers
        for name, event_parser in self.event_parsers.items():
            if getattr(event_parser, '__brutal_threaded', False):
                log.msg('executing event_parser {0!r} in thread'.format(name), logLevel=logging.DEBUG)
                response = yield event_parser(event)
            else:
                log.msg('executing event_parser {0!r}'.format(name), logLevel=logging.DEBUG)
                #try:
                response = yield event_parser(event)
                #except

            if type(response) in (str, unicode):
                a = self.new_action().msg(event.channel, response)
                ## event.add_response_action(a)

        #check cmds
        if event.cmd is not None and event.cmd in self.commands:
            # IM HERE. i need to make sure event.cmd is filled in, and a bunch of other shit. test this out first.
            cmd_func = self.commands[event.cmd]
            if getattr(cmd_func, '__brutal_threaded', False):
                log.msg('executing cmd {0!r} on event {1!r} in thread'.format(event.cmd, event), logLevel=logging.DEBUG)
                response = yield cmd_func(event)
            else:
                log.msg('executing cmd {0!r} on event {1!r}'.format(event.cmd, event), logLevel=logging.DEBUG)
                response = yield cmd_func(event)

            log.msg('RESPONSE: {0!r}'.format(response), logLevel=logging.DEBUG)
            # if type(response) in (str, unicode):
            #     a = self.new_action().msg(event.channel, response)
                ## event.add_response_action(a)

        # do we actually want to return the event?
        defer.returnValue(event)

class BotManager(object):
    """
    Handles herding of all bottes, responsible for spinning up and shutting down
    """
    #TODO: fill this shit out, needs to read config or handle config object?
    def __init__(self, config=None):
        if config is None:
            raise AttributeError("No config passed to manager.")
        self.config = config

        self.bottes = []
        # not sure about this...
        # {'bot_name': {'connections':[], ....}, }
        # bot -> {partyline:,othershit?}
        # NETWORKED PARTY LINES WOULD BE HOT FIRE

        #self.tasks = Queue()
        self.event_handler = None

        # build bottes from config
        self.setup()

        self.delete_this = 0

    def __repr__(self):
        return '<{0}: {1!r}>'.format(self.__class__.__name__, self.bottes)

    def __str(self):
        return repr(self)

    def setup(self):
        bots = getattr(self.config, 'BOTS', None)

        if bots is not None and isinstance(bots, list):
            for bot_config in bots:
                if isinstance(bot_config, dict):
                    self.create_bot(**bot_config)
                    # for connection in bots_config[bot_name]:
                    #     if isinstance(connection, dict):
                    #         self.create_bot(bot_name, **connection)

        #self.event_handler = EventHandler()

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