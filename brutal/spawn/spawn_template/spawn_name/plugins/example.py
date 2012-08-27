from brutal.core.plugin import BotPlugin, cmd

@cmd
def ping(event):
    return 'pong'

@cmd
def sleep(event):
    import time
    time.sleep(5)
    return 'im sleepy...'

class TestPlugin(BotPlugin):
    @cmd
    def classping(self, event):
        return 'pong from class!'
