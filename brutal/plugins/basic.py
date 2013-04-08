from brutal.core.plugin import cmd

@cmd
def help(event):
    return 'no...'

@cmd(thread=True)
def sleep(event):
    import time
    time.sleep(5)
    return 'im sleepy...'