import logging
from os import linesep

from twisted.internet import stdio
from twisted.protocols import basic

from brutal.protocols.core import ProtocolBackend


class TestConsoleClient(basic.LineReceiver):
    delimiter = linesep
    #delimiter = '\n'  # unix terminal style newlines

    def __init__(self, backend):
        # ugh old style classes
        #basic.LineReceiver.__init__(self)

        self.backend = backend

        self.log = logging.getLogger('brutal.protocol.{0}'.format(self.__class__.__name__))

    def connectionMade(self):
        self.log.debug('connected!')
        self.sendLine('>>> brutal bot test console connected')

        #from twisted.internet import task
        #loop = task.LoopingCall(self.print_loop)
        #loop.start(2.0)

    def lineReceived(self, line):
        # ignore blank lines
        if not line:
            return

        self.log.debug('line received: {0!r}'.format(line))
        msg = line
        if self.backend.rooms is not None:
            room = self.backend.rooms[0]
        else:
            room = 'test_console'

        event_data = {'type': 'message', 'scope': 'public', 'room': room, 'meta': {'from': 'console', 'body': msg}}
        #self.sendLine('GOT! {0!r}'.format(line))
        self._bot_process_event(event_data)

    def _bot_process_event(self, raw_event):
        self.backend.handle_event(raw_event)

    def bot_process_action(self, action):
        #self.sendLine('>>> got action! {0!r}'.format(action))
        if action.action_type == 'message':
            body = action.meta.get('body')
            if body:
                for dest in action.destination_rooms:
                    self.sendLine('>>> {0}: {1}'.format(dest, body))

    def print_loop(self):
        self.sendLine('>>> loop')


class TestConsoleBackend(ProtocolBackend):
    protocol_name = 'testconsole'

    def configure(self, *args, **kwargs):
        self.log.debug('configuring {0}'.format(self))
        self.log_traffic = kwargs.get('log_traffic', True)

        self.nick = kwargs.get('nick')
        self.rooms = ['ROOM', ]

        self.client = TestConsoleClient(backend=self)

    def connect(self, *args, **kwargs):
        self.log.debug('connecting {0}'.format(self))
        stdio.StandardIO(self.client)

    def handle_action(self, action):
        self.client.bot_process_action(action)