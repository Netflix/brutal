import sys

from twisted.internet import reactor
from twisted.python import log

from brutal.core.bot import BotManager


def main(config):
    """
    this is the primary run loop, should probably catch quits here?
    """
    # TODO: move logging to BotManager, make configurable
    log.startLogging(sys.stdout, setStdout=0)

    bot_manager = BotManager(config)
    bot_manager.start()

    reactor.run()