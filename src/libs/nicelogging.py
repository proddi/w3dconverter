# -*- coding: utf-8 -*-
#
# color-ref: http://ascii-table.com/ansi-escape-sequences.php
#

import sys, logging, time, logging.handlers, logging.config
from logging import *

__version__ = "1.2"

# root logger configuration
def config(level=INFO, levels={}, format='%(levelicon)s %(c)s%(message)s%(nc)s'):
    handler = logging.StreamHandler(StdErrStreamWrapper())
    handler.addFilter(NiceFilter())
    handler.setFormatter(NiceFormatter(format))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)

    logging.captureWarnings(True)


# configure file handler (shortcut)
def configFileHandler(*args, **kwargs):
    return configHandler(logging.handlers.RotatingFileHandler, args=args, **kwargs)


# configure file handler (shortcut)
def configTimedRotatingFileHandler(*args, **kwargs):
    return configHandler(logging.handlers.TimedRotatingFileHandler, args=args, **kwargs)


# confugure custom handler
def configHandler(Klass, format=None, loggers=[""], level=None, filters=[], args=[], **kwargs):
    handler = Klass(*args, **kwargs)
    handler.setFormatter(NiceFormatter(format))
    if level:
        handler.setLevel(level)
    for filt in filters:
        handler.addFilter(filt)
    for name in loggers:
        logging.getLogger(name).addHandler(handler)
    return handler


class NiceFormatter(logging.Formatter):

    def format(self, record):
        record.message = record.getMessage()
        if "%(asctime)" in self._fmt:
            record.asctime = self.formatTime(record, self.datefmt)
        if record.exc_info:
            if record.message[-1] != "\n":
                record.message += "\n"
            record.message += self.formatException(record.exc_info)
        return (self._fmt % record.__dict__).replace("\n", "\n  | ")


class StdErrStreamWrapper(object):
    def __init__(self):
        self.encoding = getattr(sys.stderr, 'encoding', None)

    def flush(self):
        sys.stderr.flush()

    def write(self, msg):
        sys.stderr.write(msg)


class NiceFilter(logging.Filter):

    _levelShorts = {
        CRITICAL : ('#', u'\x1b[31m'),  # red
        ERROR : ('!', u'\x1b[31m'),  # red
        WARNING : ('*', u'\x1b[33m'),  # yellow
        INFO : ('-', u'\x1b[1m'),
        DEBUG : ('~', u'\x1b[37m'),
        NOTSET : ('?', 'c'),
    }
    _startTime = time.time()

    def __init__(self):
        pass

    def filter(self, record):
        record.levelicon, record.c = self._levelShorts.get(record.levelno, ("?",""))
        record.nc = u'\x1b[0m'
        record.runtime = record.created - self._startTime
        return True


class RelativePathnameFilter(logging.Filter):
    def __init__(self, *paths):
        self.paths = paths
    def filter(self, record):
        pathname = record.pathname
        for path in self.paths:
            if pathname.startswith(path):
                record.pathname = pathname[len(path)+1:]
                break
        return True
