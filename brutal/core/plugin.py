import re
import logging
import inspect
import functools
from twisted.internet import reactor, task, defer, threads
from twisted.python.threadable import isInIOThread

from brutal.core.models import Action, Event
from brutal.conf import config

SRE_MATCH_TYPE = type(re.match("", ""))


def threaded(func=None):
    """
    tells bot to run function in a thread
    """
    def decorator(func):
        func.__brutal_threaded = True

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def cmd(func=None, command=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        func.__brutal_event_type = 'cmd'
        func.__brutal_trigger = None
        if command is not None and type(command) in (str, unicode):

            try:
                func.__brutal_trigger = re.compile(command)
            except Exception:
                logging.exception('failed to build regex for {0!r} from func {1!r}'.format(command, func.__name__))

        if func.__brutal_trigger is None:
            try:
                raw_name = r'^{0}$'.format(func.__name__)
                func.__brutal_trigger = re.compile(raw_name)
            except Exception:
                logging.exception('failing to build command from {0!r}'.format(func.__name__))
                func.__brutal_event = False

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


# def parser(func=None, thread=True):
#     """
#     this decorator makes the function look at _all_ lines and attempt to parse them
#     ex: logging
#     """
#     def decorator(func):
#         func.__brutal_parser = True
#
#         if thread is True:
#             func.__brutal_threaded = True
#
#         @functools.wraps(func)
#         def wrapper(*args, **kwargs):
#             return func(*args, **kwargs)
#         return wrapper
#
#     if func is None:
#         return decorator
#     else:
#         return decorator(func)


# make event_type required?
def event(func=None, event_type=None, thread=False):
    """
    this decorator is used to register an event parser that the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        if event_type is not None and type(event_type) in (str, unicode):
            func.__brutal_event_type = event_type

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


#TODO: maybe swap this to functools.partial
def match(func=None, regex=None, thread=False):
    """
    this decorator is used to create a command the bot will respond to.
    """
    def decorator(func):
        func.__brutal_event = True
        func.__brutal_event_type = 'message'
        func.__brutal_trigger = None
        if regex is not None and type(regex) in (str, unicode):
            try:
                func.__brutal_trigger = re.compile(regex)
            except Exception:
                logging.exception('failed to build regex for {0!r} from func {1!r}'.format(regex, func.__name__))

        if func.__brutal_trigger is None:
            try:
                raw_name = r'^{0}$'.format(func.__name__)
                func.__brutal_trigger = re.compile(raw_name)
            except Exception:
                logging.exception('failing to build match from {0!r}'.format(func.__name__))
                func.__brutal_event = False

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


#TODO: possibly abstract like this?
class Parser(object):
    def __init__(self, func, source=None):
        self.healthy = False

        self.source = source
        if inspect.isclass(source) is True:
            self.source_name = '{0}.{1}'.format(self.source.__module__, self.source.__name__)
        elif inspect.ismodule(source) is True:
            self.source_name = self.source.__name__
        else:
            try:
                test = isinstance(source, BotPlugin)
            except TypeError:
                self.source_name = 'UNKNOWN: {0!r}'.format(source)
            else:
                if test is True:
                    self.source_name = "{0}".format(self.__class__.__name__)
                else:
                    self.source_name = 'UNKNOWN instance: {0!r}'.format(source)

        self.func = func
        self.func_name = self.func.__name__

        self.event_type = None
        self.regex = None
        self.threaded = getattr(self.func, '__brutal_threaded', False)
        self.parse_bot_events = False

        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))

        # future use:
        #self.stop_parsing = False  # if true, wont run any more parsers after this.
        #self.parent = None
        #elf.children = None

        #TODO: check if healthy
        self.event_type = getattr(self.func, '__brutal_event_type', None)
        if self.event_type in ['cmd', 'message']:
            self.regex = getattr(self.func, '__brutal_trigger', None)

            if self.regex is None:
                self.log.error('failed to get compiled regex from func for {0}'.format(self))
                self.healthy = False
            else:
                # should probably check that its a compiled re
                self.healthy = True
        else:
            self.healthy = True

        self.log.debug('built parser - event_type: {0!r}, source: {1!r}, func: {2!r}'.format(self.event_type,
                                                                                             self.source_name,
                                                                                             self.func_name))

    def __repr__(self):
        return '<{0} {1}:{2}>'.format(self.__class__.__name__, self.source_name, self.func_name)

    def __str__(self):
        return repr(self)

    def matches(self, event):
        if not isinstance(event, Event):
            self.log.error('invalid event passed to parser')
            return

        if event.event_type == self.event_type:
            if event.event_type == 'cmd':
                if event.cmd is not None and self.regex is not None:
                    try:
                        match = self.regex.match(event.cmd)
                    except Exception:
                        self.log.exception('invalid regex match attempt on {0!r}, {1!r}'.format(event.cmd, self))
                    else:
                        return match
                else:
                    self.log.error('invalid event passed in')
            elif event.event_type == 'message' and isinstance(event.meta, dict) and 'body' in event.meta:
                body = event.meta['body']
                #TODO: HERE, make this smarter.
                if self.regex is not None and type(body) in (str, unicode):
                    try:
                        match = self.regex.match(body)
                    except Exception:
                        self.log.exception('invalid regex match attempt on {0!r}, {1!r}'.format(body, self))
                    else:
                        return match
                else:
                    self.log.error('message contains no body to regex match against')
            else:
                return True
        else:
            self.log.debug('event_parser not meant for this event type')

    @classmethod
    def build_parser(cls, func, source):
        if getattr(func, '__brutal_event', False):
            return cls(func, source)


class PluginManager(object):
    def __init__(self, bot):
        self.log = logging.getLogger('{0}.{1}'.format(self.__class__.__module__, self.__class__.__name__))
        self.bot = bot
        self.event_parsers = {None: [], }

        self.plugin_modules = {}
        self.plugin_instances = {}

        self.status = None

        # possibly track which bot this PM is assigned to?
        # should track which module it came from for easy unloading

    # def start(self):
    #     installed_plugins = getattr(config, PLUGINS)

    def start(self, enabled_plugins=None):
        if enabled_plugins is not None and not type(enabled_plugins) in (list, dict):
            self.log.error('improper plugin config, list or dictionary required')
            return

        installed_plugins = getattr(config, 'PLUGINS')

        if installed_plugins is None:
            self.log.error('error getting INSTALLED_PLUGINS')
            return

        # find enabled plugin modules and instantiate classes of every BotPlugin within modules
        for plugin_module in installed_plugins:
            if enabled_plugins is not None:
                if plugin_module.__name__ not in enabled_plugins:
                    continue

            self.plugin_modules[plugin_module] = plugin_module.__name__

            # get classes
            for class_name, class_object in inspect.getmembers(plugin_module, inspect.isclass):
                if issubclass(class_object, BotPlugin):
                    try:
                        instance = class_object(bot=self.bot)
                    except Exception:
                        self.log.exception('failed to load plugin {0!r} from {1!r}'.format(class_name,
                                                                                           plugin_module.__name__))
                    else:
                        try:
                            instance.setup()
                        except Exception:
                            self.log.exception('failed to setup plugin {0!r} from {1!r}'.format(class_name,
                                                                                                plugin_module.__name))
                        else:
                            self.plugin_instances[instance] = plugin_module.__name__

        self._register_plugins(self.plugin_modules, self.plugin_instances)

    def _register_plugins(self, plugin_modules, plugin_instances):
        """
        TODO: add default plugins

        for this bot, load all the plugins
        - find event handlers and register them
        """
        for module in plugin_modules:
            self._register_plugin_functions(module)

        for plugin_instance in plugin_instances:
            self._register_plugin_class_methods(plugin_instance)

    def remove_plugin(self, plugin_module):
        #TODO: fill out
        pass

    def _register_plugin_functions(self, plugin_module):
        module_name = plugin_module.__name__
        self.log.debug('loading plugins from module {0!r}'.format(module_name))

        # step through all functions in module
        for func_name, func in inspect.getmembers(plugin_module, inspect.isfunction):
            try:
                parser = Parser.build_parser(func=func, source=plugin_module)
            except Exception:
                self.log.exception('failed to build parser from {0} ({1})'.format(func_name, module_name))
                continue
            else:
                if parser is not None:
                    if parser.event_type in self.event_parsers:
                        self.event_parsers[parser.event_type].append(parser)
                    else:
                        self.event_parsers[parser.event_type] = [parser, ]

    def _register_plugin_class_methods(self, plugin_instance):
        #TODO: should wrap this...
        class_name = plugin_instance.__class__.__name__
        self.log.debug('loading plugins from instance of {0!r}'.format(class_name))

        for func_name, func in inspect.getmembers(plugin_instance, inspect.ismethod):
            try:
                parser = Parser.build_parser(func=func, source=plugin_instance)
            except Exception:
                self.log.exception('failed to build parser from {0} ({1})'.format(func_name, class_name))
                continue
            else:
                if parser is not None:
                    if parser.event_type in self.event_parsers:
                        self.event_parsers[parser.event_type].append(parser)
                    else:
                        self.event_parsers[parser.event_type] = [parser, ]

    # event processing
    @defer.inlineCallbacks
    def _run_event_processor(self, event_parser, event, *args):
        run = True
        response = None
        # TODO: make this check if from_bot == _this_ bot
        if event.from_bot is True:
            if event_parser.parse_bot_events is not True:
                self.log.info('ignoring event from bot: {0!r}'.format(event))
                run = False

        if run is True:
            if event_parser.threaded is True:
                self.log.debug('executing event_parser {0!r} in thread'.format(event_parser))
                response = yield threads.deferToThread(event_parser.func, event, *args)
            else:
                self.log.debug('executing event_parser {0!r}'.format(event_parser))
                #try:
                response = yield event_parser.func(event, *args)

        defer.returnValue(response)

    def process_event(self, event):
        #TODO: this needs some love

        # this will keep track of all the responses we get
        responses = []

        # TODO: wrap everything in try/except
        if not isinstance(event, Event):
            self.log.error('invalid event, ignoring: {0!r}'.format(event))
            raise

        self.log.debug('processing {0!r}'.format(event))

        # run only processors of this event_type
        if event.event_type is not None and event.event_type in self.event_parsers:
            self.log.debug('detected event_type {0!r}'.format(event.event_type))
            for event_parser in self.event_parsers[event.event_type]:
                # check if match
                match = event_parser.matches(event)
                response = None
                if match is True:
                    self.log.debug('running event_parser {0!r}'.format(event_parser))
                    response = self._run_event_processor(event_parser, event)
                elif isinstance(match, SRE_MATCH_TYPE):
                    self.log.debug('running event_parser {0!r} with regex results {1!r}'.format(event_parser,
                                                                                                match.groups()))
                    response = self._run_event_processor(event_parser, event, *match.groups())

                if response is not None:
                    responses.append(response)

        # default 'all' parsers
        for event_parser in self.event_parsers[None]:
            self.log.debug('running event_parser {0!r}'.format(event_parser))
            # response = yield self._run_event_processor(event_parser, event)
            response = self._run_event_processor(event_parser, event)

            if response is not None:
                responses.append(response)

        for response in responses:
            response.addCallback(self.process_result, event)

        return responses
        #defer.returnValue(responses)

    # def emit_action() - out of band action to the bot.

    def process_result(self, response, event):
        if response is not None:
            self.log.debug('RESPONSE: {0!r}'.format(response))
            if isinstance(response, Action):
                return response
                #self.bot.action_queue.put(response)
            else:
                # a = self.build_action(response, event)
                return self.build_action(response, event)

                # if a is not None:
                #     self.bot.action_queue.put(a)

    def build_action(self, action_data, event=None):
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self.bot, source_event=event).msg(action_data)
            except Exception as e:
                self.log.exception('failed to build action from {0!r}, for {1!r}: {2!r}'.format(action_data, event, e))
            else:
                return a


#TODO: completely changed, need to rework this...
class BotPlugin(object):
    """
    base plugin class

    """
    event_version = '1'
    built_in = False  # is this a packaged plugin

    #TODO: make a 'task' decorator...
    def __init__(self, bot=None):
        """
        don't touch me. plz?

        each bot that spins up, loads its own plugin instance

        TODO: move the stuff in here to a separate func and call it after we initialize the instance.
            that way they can do whatever they want in init
        """
        self.bot = bot

        self.log = logging.getLogger('{0}.{1}'.format(self.__module__, self.__class__.__name__))

        self._active = False  # is this instance active?
        self._delayed_tasks = []  # tasks scheduled to run in the future
        self._looping_tasks = []

    # Tasks

    def _clear_called_tasks(self):
        # yes.
        self._delayed_tasks[:] = [d for d in self._delayed_tasks if d.called()]

    def _handle_task_response(self, response, *args, **kwargs):
        self.log.debug('PLUGIN TASK RESULTS: {0!r}'.format(response))
        self.log.debug('TASK ARGS: {0!r}'.format(args))
        self.log.debug('TASK KWARGS: {0!r}'.format(kwargs))
        # hacking this in for now:
        event = kwargs.get('event')
        try:
            a = self.build_action(action_data=response, event=event)
        except Exception:
            self.log.exception('failed to build action from plugin task {0!r}, {1!r}, {2!r}'.format(response, args,
                                                                                                    kwargs))
        else:
            self.log.debug('wat: {0!r}'.format(a))
            if a is not None:
                self._queue_action(a, event)

    def build_action(self, action_data, event=None):
        #TODO this is hacky - fix it.
        if type(action_data) in (str, unicode):
            try:
                a = Action(source_bot=self.bot, source_event=event).msg(action_data)
            except Exception:
                logging.exception('failed to build action from {0!r}, for {1!r}'.format(action_data, event))
            else:
                return a


    @defer.inlineCallbacks
    def _plugin_task_runner(self, func, *args, **kwargs):
        try:
            if getattr(func, '__brutal_threaded', False):
                self.log.debug('executing plugin task in thread')  # add func details
                response = yield threads.deferToThread(func, *args, **kwargs)
            else:
                self.log.debug('executing plugin task')  # add func details
                response = yield func(*args, **kwargs)

            yield self._handle_task_response(response, *args, **kwargs)
            # defer.returnValue(response)
        except Exception as e:
            self.log.error('_plugin_task_runner failed: {0!r}'.format(e))

    def delay_task(self, delay, func, *args, **kwargs):
        if inspect.isfunction(func) or inspect.ismethod(func):
            self.log.debug('scheduling task {0!r} to run in {1} seconds'.format(func.__name__, delay))
            # trying this.. but should probably just use callLater
            d = task.deferLater(reactor, delay, self._plugin_task_runner, func, *args, **kwargs)
            self._delayed_tasks.append(d)

    def loop_task(self, loop_time, func, *args, **kwargs):
        if inspect.isfunction(func) or inspect.ismethod(func):
            self.log.debug('scheduling task {0!r} to run every {1} seconds'.format(func.__name__, loop_time))
            now = kwargs.pop('now', True)
            #event = kwargs.pop('event', None)
            t = task.LoopingCall(self._plugin_task_runner, func, *args, **kwargs)
            t.start(loop_time, now)
            self._looping_tasks.append(t)

    # Actions

    def _queue_action(self, action, event=None):
        if isinstance(action, Action):
            if isInIOThread():
                self.bot.route_response(action, event)
            else:
                reactor.callFromThread(self.bot.route_response, action, event)
        else:
            self.log.error('tried to queue invalid action: {0!r}'.format(action))

    def msg(self, msg, room=None, event=None):
        a = Action(source_bot=self.bot, source_event=event).msg(msg, room=room)
        self._queue_action(a, event)

    # internal

    def enable(self):
        self.log.info('enabling plugin on {0!r}: {1!r}'.format(self.bot, self.__class__.__name__))

        # eh. would like to be able to resume... but that's :effort:
        self._delayed_tasks = []
        self._looping_tasks = []
        # set job to clear task queue
        self.loop_task(15, self._clear_called_tasks, now=False)
        self._active = True

    def disable(self):
        self.log.info('disabling plugin on {0!r}: {1!r}'.format(self.bot, self.__class__.__name__))
        self._active = False

        for func in self._delayed_tasks:
            if func.called is False:
                func.cancel()

        for func in self._looping_tasks:
            if func.running:
                func.stop()

        self._delayed_tasks = []
        self._looping_tasks = []

#     def handle_event(self, event):
#         if isinstance(event, Event):
#             if self._version_matches(event):
# #                if self._is_match(event):
#                 self._parse_event(event)
#
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