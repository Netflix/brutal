"""
Examples of brutal plugins. Primarily used for testing.
"""

import time
from brutal.core.plugin import BotPlugin, cmd, event, match, threaded


@cmd
def ping(event):
    return 'pong, got {0!r}'.format(event)


@cmd
def testargs(event):
    return 'you passed in args: {0!r}'.format(event.args)


#@event(thread=True)
def sleepevent(event):
    time.sleep(7)
    return 'SOOOOOO sleepy'


@cmd(thread=True)
def sleep(event):
    time.sleep(5)
    return 'im sleepy...'


#@event
def test_event_parser(event):
    return 'EVENT!!! {0!r}'.format(event)

# @match(regex=r'^hi$')
# def matcher(event):
#     return 'Hello to you!'


class TestPlugin(BotPlugin):
    def setup(self, *args, **kwargs):
        self.log.debug('SETUP CALLED')
        self.count = 0
        self.loop_task(5, self.test_loop, now=False)
        self.delay_task(10, self.future_task)

    def future_task(self):
        self.log.info('testing future task')
        return 'future!'

    @threaded
    def test_loop(self):
        self.log.info('testing looping task')
        return 'loop!'

    def say_hi(self, event=None):
        self.msg('from say_hi: {0!r}'.format(event), event=event)
        return 'hi'

    @threaded
    def say_delayed_hi(self, event=None):
        self.msg('from say_hi_threaded, sleeping for 5: {0!r}'.format(event), event=event)
        time.sleep(5)
        return 'even more delayed hi'

    @cmd
    def runlater(self, event):
        self.delay_task(5, self.say_hi, event=event)
        self.delay_task(5, self.say_delayed_hi, event=event)
        return 'will say hi in 5 seconds'

    @cmd
    def count(self, event):
        self.count += 1
        return 'count {1!r} from class! got {0!r}'.format(event, self.count)

    @cmd(thread=True)
    def inlinemsg(self, event):
        self.msg('sleeping for 5 seconds!', event=event)
        time.sleep(5)
        return 'done sleeping!'
