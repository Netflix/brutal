__title__ = 'brutal'
__version__ = '0.3.0'
__author__ = 'Corey Bertram'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2013 Corey Bertram'

# Set default logging handler
import logging

# python < 2.7 compatibility
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())