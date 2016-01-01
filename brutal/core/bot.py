import uuid
import logging

from twisted.internet import reactor
from twisted.internet import task, defer
from brutal.core.connections import ConnectionManager

from brutal.core.plugin import PluginManager
from brutal.core.models import Event, Action

from brutal.core.constants import *


class Bot(object):
    def __init__(self, nick, connections, command_token='!', *args, **kwargs):
        """
        acts as a connection manager, middle man for incoming events, and processor of outgoing actions.
        """
        #TODO: maybe support a custom internal key to keep track of bots, not just by 'name'...
        #TODO: if we do it by name, make sure we don't have name dupes, even between networks :-/

        # bot id
        self.nick = nick
        self.id = str(uuid.uuid1())
        self.command_token = command_token
        self.log = logging.getLogger('{0}.{1}.{2}'.format(self.__class__.__module__, self.__class__.__name__,
                                                          self.nick))
        self.log.info('starting bot')

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
        # TODO: create connection manager
        self.connection_manager = ConnectionManager(config=connections, bot=self)
        self.log.debug('connections on {0!r}: {1!r}'.format(self.nick, self.connection_manager))

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
        self.connection_manager.connect()
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
                responses = self.plugin_manager.process_event(event)
                # this is going to be a list of deferreds,
                # TODO: should probably do this differently
                #self.log.debug('HERE: {0!r}'.format(responses))
                for response in responses:
                    #self.log.debug('adding response router')
                    response.addCallback(self.route_response, event)

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
        if response is not None:
            self.log.debug('got {0!r} from {1!r}'.format(response, event))
            #TODO: update to actually route to correct bot, for now we just assume its ours
            if isinstance(response, Action):
                self.action_queue.put(response)
            else:
                self.log.error('got invalid response type')

    def process_action(self, action):
        #self.log.debug('routing response: {0}'.format(action))
        self.connection_manager.route_action(action)
        # for client_id, client in self.connection_manager..items():
        #     if conn.id is not None and conn.id in action.destination_connections:
        #         conn.queue_action(action)


class BotManager(object):
    """
    Handles herding of all bottes, responsible for spinning up and shutting down
    """
    #TODO: fill this out, needs to read config or handle config object?
    def __init__(self, config=None):
        if config is None:
            raise AttributeError("No config passed to manager.")

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        self.config = config
        self.log.debug('config: {0!r}'.format(self.config))

        self.bots = {}
        # not sure about this...
        # {'bot_name': {'connections':[], ....}, }
        # bot -> {partyline:_, otherstuff?}
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
