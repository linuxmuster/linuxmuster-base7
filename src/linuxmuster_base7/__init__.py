"""
linuxmuster-base7 - Core Python library for linuxmuster.net 7.x

This package provides the core functionality for linuxmuster.net 7.x,
including setup scripts, command-line tools, and utility functions.

Authors: thomas@linuxmuster.net
License: GPL-3.0
"""

__version__ = "7.3.29"
__author__ = "thomas@linuxmuster.net"

# Make commonly used functions available at package level
from .functions import (
    sambaTool,
    adSearch,
    readTextfile,
    writeTextfile,
    modIni,
    isValidHostIpv4,
    isValidHostname,
)

__all__ = [
    'sambaTool',
    'adSearch',
    'readTextfile',
    'writeTextfile',
    'modIni',
    'isValidHostIpv4',
    'isValidHostname',
]
