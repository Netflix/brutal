import functools
from brutal.core.utils import PluginRoot
from brutal.core.models import Event, Action

#plugin.respond_to_bots?
#plugin.respond_to_self?


def cmd(func=None, command=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_cmd = True
        if thread is True:
            func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def parser(func=None, thread=True):
    """
    this decorator makes the function look at _all_ lines and attempt to parse them
    ex: logging
    """
    def decorator(func):
        func.__brutal_parser = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


# make event_type required?
def event(func=None, event_type=None, thread=True):
    """
    this decorator is used to register an event parser that the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


#TODO: completely changed, need to rework this...
class BotPlugin(object):
    """
    base plugin class, maintains list of all plugins

    """
    __metaclass__ = PluginRoot
    event_version = '1'

    #TODO: make a 'task' decorator...
    def __init__(self, bot=None):
        """
        don't touch me. plz?

        each bot that spins up, loads its own plugin instance

        TODO: move the stuff in here to a separate func and call it after we initialize the instance.
            that way they can do whatever they want in init
        """
        self.bot = bot
        self.active = False  # is this instance active?

    def action(self):
        if self.bot is not None:
            a = self.bot.new_action()
            return a

    def handle_event(self, event):
        if isinstance(event, Event):
            if self._version_matches(event):
#                if self._is_match(event):
                self._parse_event(event)

    #min_version
    #max_version
    def _version_matches(self, event):
        #TODO: ugh.. figure out what i want to do here...
        if event.version == self.event_version:
            return True
        return False

    def setup(self, *args, **kwargs):
        """
        use this to do any one off actions needed to initialize the bot once its active
        """
        pass
        #raise NotImplementedError

    def _is_match(self, event):
        """
        returns t/f based if the plugin should parse the event
        """
        return True
        #raise NotImplementedError

    def _parse_event(self, event):
        """
        takes in an event object and does whatever the plugins supposed to do...
        """
        raise NotImplementedError

