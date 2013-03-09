from brutal.core.plugin import BotPlugin, cmd


@cmd
def ping(event):
    return 'pong, got {0!r}'.format(event)


@cmd(thread=True)
def sleep(event):
    import time
    time.sleep(5)
    return 'im sleepy...'


class TestPlugin(BotPlugin):
    @cmd
    def boss(self, event):
        return '2pro4u from class! got {0!r}'.format(event)
