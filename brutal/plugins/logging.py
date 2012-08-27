from datetime import datetime
from brutal.conf import config
from brutal.core.plugin import BotPlugin, parser

#TODO: have this fail cleanly, when a bot stops responding / disconnects, have it drop itself from the logging of a channel?

class LoggingPlugin(BotPlugin):
    # _don't_ do this; i'm being clever.
    # for jabber 'channel' == 'botname:chat'
    loggers = {}
    event_version = '1'

    #TODO: move to settings
    action_line_prefix = '-!-'
    storage = getattr(config, 'BRUTAL_LOG_STORAGE', '/tmp/')

    def setup(self, *args, **kwargs):
        self.current_dt = None
        self.channels = [] #make it possible to define certain channels to log
        #self.register_all()
        #self.global_continue()

    def _is_match(self, event):
        parse = False
        if len(self.channels):
            #check if channel is in our channels watch list
            if event.channel in self.channels:
                parse = True
        else:
            #attempt to log all events
            parse = True
        return parse

    @parser
    def _parse_event(self, event):
        if not self._is_match(event):
            return
        #update time
        self.current_dt = datetime.now()
        #check if other bot already logging this

        if 'addr' in event.server_info:
            network = event.server_info['addr']
        elif 'hostname' in event.server_info:
            network = event.server_info['hostname']
        else:
            network = event.source_bot.network
        channel = event.channel

        log_this = False
        log_file = None

        #TODO: wow what the fuck was i doing here. fix this logic
        if network in self.loggers:
            if channel in self.loggers[network]:
                if self.loggers[network][channel][0] == self.bot:
                    log_this = True
                    log_file = self.loggers[network][channel][1]
                    log_file = self._check_file(log_file, channel)
                #else another bot is handling it, dont log
            else:
                #channel not in
                log_this = True
                log_file = self._check_file(None, channel)
                self.loggers[network][channel] = [self.bot, log_file]
        else:
            #network not in
            log_this = True
            log_file = self._check_file(None, channel)
            self.loggers[network] = {channel:[self.bot, log_file]}

        if log_this is True and log_file is not None:
            #write! - needs to be rewritten using twisteds 'nonblocking writes' (lol?)
            line = self._get_line(event)
            self._write_line(line, log_file)
            #if ret is

    # -- internal --
    def _check_file(self, logfile, channel): #shoudl realy take in network too
        if isinstance(logfile, file):
            if self._needs_new_log_file(logfile.name):
                logfile.close()
                new_file_path = self._new_file_path(channel)
                logfile = open(new_file_path, 'a+')
            else:
                if logfile.closed:
                    logfile = open(logfile.name, 'a+')
        elif logfile is None:
            new_file_path = self._new_file_path(channel)
            logfile = open(new_file_path, 'a+')

        return logfile

    def _new_file_path(self, channel):
        file_date = self.current_dt.strftime('%m_%d_%Y')
        # all of these should really read from the event...
        #uh, what the fuck was i thinking.. use os.path.join
        file_path = '{0}{1}__{2}__{3}{4}.log'.format(self.storage, self.bot.network, self.bot.name, channel + '__' if len(channel) > 0 else '',file_date)
        return file_path

    def _needs_new_log_file(self, file_path):
        x = None
        try:
            x = file_path[file_path.rfind('__')+2:].replace('.log','')
        except Exception:
            pass

        if x is not None:
            try:
                existing_date = datetime.strptime(x, '%m_%d_%Y')
            except Exception:
                pass
            else:
                if self.current_dt.date() > existing_date.date():
                    return True

        return False

    def _write_line(self, line, log_file):
        if isinstance(line, str):
            if self.current_dt is not None and isinstance(log_file, file) and log_file.closed is False:
                timestamp = self.current_dt.strftime("[%H:%M:%S]")
                try:
                    log_file.write('{0} {1}\n'.format(timestamp, line))
                    log_file.flush()
                except Exception:
                    return False
                else:
                    return True
        return False

    def _get_line(self, event):
        line = None
        if event.source_bot.type == 'irc':
            if event.type == 'priv_msg':
                #should do some error checking on these...
                username = event.meta['username']
                msg = event.meta['msg']
                line = '<{0}> {1}'.format(username, msg)

        return line