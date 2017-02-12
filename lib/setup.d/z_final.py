#!/usr/bin/python3
#
# z_final.py
# thomas@linuxmuster.net
# 20170212
#

import constants
import os
import sys

from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# import devices
msg = 'Starting device import '
printScript(msg, '', False, False, True)
try:
    subProc('linuxmuster-import-devices.py', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
