import uuid
from twisted.internet.defer import DeferredQueue
from twisted.python import log
from brutal.core.utils import PluginRoot
from brutal.core.models import Event


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
        self.action_queue = DeferredQueue()
        self.consume_actions(self.action_queue)

    def __repr__(self):
        return '<{0} {1!s}>'.format(self.__class__.__name__, self.id)

    def __str__(self):
        return repr(self)

    def handle_event(self, event):
        """
        takes events, tags them with the current backend, and places them on bot event_queue
        """
        if isinstance(event, Event):
            event.connection = self
            event.connection_id = self.id
            self.bot.new_event(event)
        elif isinstance(event, dict):
            event['connection'] = self
            event['connection_id'] = self.id
            self.bot.new_event(event)
        else:
            log.err('invalid Event passed to {0}')

    def consume_actions(self, queue):
        """
        responsible for reading actions given to this connection
        """
        def consumer(action):
            self.handle_action(action)
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
