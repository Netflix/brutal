import sys

from twisted.internet import reactor
from twisted.python import log


def main(config):
    from brutal.core.bot import BotManager
    bot_manager = BotManager(config)
    bot_manager.start()

    log.startLogging(sys.stdout)

    reactor.run()

