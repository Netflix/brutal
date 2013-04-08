import uuid
import logging
from twisted.internet.defer import DeferredQueue

from brutal.core.utils import PluginRoot
from brutal.core.models import Event, Action


def catch_error(failure):
    """ used for errbacks
    """
    return failure.getErrorMessage()


class ProtocolBackend(object):
    """
    all protocol backends will inherit from this.
    """
    __metaclass__ = PluginRoot
    protocol_name = None

    def __init__(self, bot):
        if self.protocol_name is None:
            raise NotImplementedError

        self.id = str(uuid.uuid1())
        self.bot = bot
        self.rooms = None

        self.action_queue = DeferredQueue()
        self.consume_actions(self.action_queue)

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

    def __repr__(self):
        return '<{0} {1!s}>'.format(self.__class__.__name__, self.id)

    def __str__(self):
        return repr(self)

    @property
    def default_room(self):
        if self.rooms is not None:
            for i in self.rooms:
                return i
        self.log.error('unable to get default room from {0!r} on {1!r}'.format(self.rooms, self))

    def handle_event(self, event):
        """
        takes events, tags them with the current backend, and places them on bot event_queue
        """
        if isinstance(event, Event):
            event.source_client = self
            event.source_client_id = self.id
            self.bot.new_event(event)
        elif isinstance(event, dict):
            event['client'] = self
            event['client_id'] = self.id
            self.bot.new_event(event)
        else:
            self.log.error('invalid Event passed to {0}')

    def queue_action(self, action):
        if isinstance(action, Action):
            self.action_queue.put(action)
        else:
            self.log.error('invalid object handed to protocol action queue: {0!r}'.format(action))

    def consume_actions(self, queue):
        """
        responsible for reading actions given to this connection
        """
        def consumer(action):
            if isinstance(action, Action):
                self.handle_action(action)
            else:
                self.log.warning('invalid action put in queue: {0!r}'.format(action))

            queue.get().addCallback(consumer)
        queue.get().addCallback(consumer)

    def handle_action(self, action):
        """
        should take an action and act on it
        """
        raise NotImplementedError

    def configure(self, *args, **kwargs):
        """
        should read in the config options and setup client
        """
        raise NotImplementedError

    def connect(self, *args, **kwargs):
        """
        should connect the client
        """
        #TODO: find a way to delay connections (have it be user definable in the config) reactor.callLater
        raise NotImplementedError
