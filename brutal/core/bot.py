import uuid
import logging

from twisted.internet import reactor
from twisted.internet import task, defer

from brutal.protocols.core import ProtocolBackend
from brutal.core.plugin import PluginManager
from brutal.core.models import Event, Action
# supported protocols - done for plugin access. kinda ugly
from brutal.protocols.irc import IrcBackend
from brutal.protocols.xmpp import XmppBackend
from brutal.protocols.testconsole import TestConsoleBackend

from brutal.core.constants import *


class Bot(object):
    def __init__(self, nick, connections, *args, **kwargs):
        """
        acts as a connection manager, middle man for incoming events, and processor of outgoing actions.
        """
        #TODO: maybe support a custom internal key to keep track of bots, not just by 'name'...
        #TODO: if we do it by name, make sure we don't have name dupes, even between networks :-/

        # bot id
        self.nick = nick
        self.id = str(uuid.uuid1())
        self.log = logging.getLogger('{0}.{1}.{2}'.format(self.__class__.__module__, self.__class__.__name__,
                                                          self.nick))
        self.log.info('starting bot')

        # list of all connections
        # TODO: create connection manager
        self.active_connections = {}

        #bot manager instance
        self.bot_manager = None

        # setup this bots event queue / consumer, action queue/consumer
        self.event_queue = defer.DeferredQueue()
        self._consume_events(self.event_queue)

        self.action_queue = defer.DeferredQueue()
        self._consume_actions(self.action_queue)

        # setup plugins
        self.enabled_plugins = kwargs.get('enabled_plugins')
        self.plugin_manager = PluginManager(bot=self)
        # self.manager.config.PLUGINS:

        # build connections
        self._parse_connections(connections)
        self.log.debug('connections on {0!r}: {1!r}'.format(self.nick, self.active_connections))

        # should have a 'ready' state that we should check before starting?
        self.state = OFF
        self.party_line = None

    def __repr__(self):
        return '<{0}: {1!r} ({2!s})>'.format(self.__class__.__name__, self.nick, self.id)

    def __str__(self):
        return repr(self)

    # CORE

    def start(self):
        #TODO: catch failures?
        #TODO: pass enabled plugins
        self.plugin_manager.start(self.enabled_plugins)

        self.connect()
        self.state = ON

    # review
    def stop(self):
        """
        TODO: placeholder
        """
        if self.state >= ON:
            self.state = OFF

    # review
    def pause(self):
        """
        placeholder
        """
        pass

    def default_destination(self):
        """
        if no destination room is defined, and no event triggered an action, determine where to send results

        NOTE: for now send everywhere...
        """
        pass

    # CONNECTIONS

    def _parse_connections(self, config_connections):
        if isinstance(config_connections, list):
            for conn_settings in config_connections:
                conn = self._build_connection(conn_settings)

                if conn is not None:
                    self.active_connections[conn.id] = conn
                else:
                    self.log.error('connection creation failed')
        else:
            self.log.error('invalid connection configuration, needs to be a list')

    def _build_connection(self, conn_settings):
        if not isinstance(conn_settings, dict):
            self.log.error('invalid conn_settings passed to build_connection: {0!r}'.format(conn_settings))
            return

        if 'nick' not in conn_settings:
            conn_settings['nick'] = self.nick

        protocol_name = conn_settings.get('protocol')
        if protocol_name is None:
            self.log.error('no protocol defined for connection: {0!r}'.format(conn_settings))
            return
        protocol_name = protocol_name.strip().lower()

        for protocol in ProtocolBackend.plugins:
            if protocol.protocol_name.lower() == protocol_name:
                #TODO: should probably try/except this
                try:
                    conn = protocol(bot=self)
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
        for conn_id, conn in self.active_connections.items():
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
                    self.log.exception('unable to parse data to Event, {0!r}: {1!r}'.format(event, e))
                    event = None

            if event is not None:
                self.log.debug('EVENT on {0!r} {1!r}'.format(self, event))
                #res = defer.maybeDeferred(self.plugin_manager.process_event, event)
                responses = self.plugin_manager.process_event(event)
                # this is going to be a list of deferreds
                for response in responses:
                    self.log.debug('adding response router')
                    response.addCallback(self.route_response, event)
                #self.log.debug('RESULT: {0!r}'.format(res))
                #for i in res:
                    #self.process_result(i, event)
                    # a = self.build_action(i, event=event)
                    # if a is not None:
                    #     self.log.debug('queuing action: {0}'.format(a))
                    #     self.action_queue.put(a)
                    # else:
                    #     self.log.debug('failed to build action')
                #res.addCallback(self.process_result, event)

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def new_event(self, event):
        """
        this is what protocol backends call when they get an event.
        """
        self.event_queue.put(event)

    def build_event(self, event_data):
        #todo: needs to be safe
        try:
            e = Event(source_bot=self, raw_details=event_data)
        except Exception as e:
            self.log.exception('failed to build event from {0!r}: {1!r}'.format(event_data, e))
        else:
            return e

    # ACTION QUEUE
    # default action consumer
    def _consume_actions(self, queue):
        def consumer(action):
            # check if Action, else try to make it one
            if not isinstance(action, Action):
                try:
                    action = self.build_action(action)
                except Exception as e:
                    self.log.exception('unable to build Action with {0!r}: {1!r}'.format(action, e))

            if action is not None:
                res = defer.maybeDeferred(self.process_action, action)

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def build_action(self, action_data, event=None):
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self, source_event=event).msg(action_data)
            except Exception as e:
                self.log.exception('failed to build action from {0!r}, for {1!r}: {2!r}'.format(action_data, event, e))
            else:
                return a

    # PLUGIN SYSTEM #################################################
    def route_response(self, response, event):
        self.log.debug('got {0!r} from {1!r}'.format(response, event))

    def process_action(self, action):
        self.log.debug('WAT! Routing response! {0}'.format(action))
        # for conn_id, conn in self.active_connections.items():
        #     if conn.id is not None and conn.id in action.destination_connections:
        #         conn.queue_action(action)


class BotManager(object):
    """
    Handles herding of all bottes, responsible for spinning up and shutting down
    """
    #TODO: fill this shit out, needs to read config or handle config object?
    def __init__(self, config=None):
        if config is None:
            raise AttributeError("No config passed to manager.")

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.config = config
        self.log.debug('config: {0!r}'.format(self.config))

        self.bots = {}
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
        return '<{0}: {1!r}>'.format(self.__class__.__name__, self.bots)

    def __str(self):
        return repr(self)

    def setup(self):
        bots = getattr(self.config, 'BOTS', None)

        self.log.debug('bots: {0!r}'.format(bots))

        if bots is not None and isinstance(bots, list):
            for bot_config in bots:
                if isinstance(bot_config, dict):
                    self.create_bot(**bot_config)
        else:
            self.log.warning('no bots found in configuration')

    def update(self):
        self.log.debug('manager loop called')
        pass

    def create_bot(self, *args, **kwargs):
        bot = Bot(*args, **kwargs)
        bot.bot_manager = self

        #todo: check if startup worked?
        self.bots[bot.nick] = {'bot': bot}

    def start_bots(self):
        for bot_id in self.bots:
            # dont like this. change.
            self.bots[bot_id]['bot'].start()

    def start(self):
        """
        starts the manager
        """
        self.start_bots()

        loop = task.LoopingCall(self.update)
        loop.start(30.0)

        reactor.run()