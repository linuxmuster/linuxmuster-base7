#!/usr/bin/python3
#
# c_fstab.py
# thomas@linuxmuster.net
# 20170212
#

import constants
import os
import reconfigure

from reconfigure.configs import FSTabConfig
from reconfigure.items.fstab import FilesystemData
from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# patch fstab with mount options
config = FSTabConfig(path='/etc/fstab')
config.load()
c = 0
while True:
    if config.tree.filesystems[c].mountpoint == '/':
        msg = 'Modifying mount options for / '
        printScript(msg, '', False, False, True)
        try:
            config.tree.filesystems[c].options = constants.ROOTMNTOPTS
            config.save()
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)
        msg = 'Remounting / '
        printScript(msg, '', False, False, True)
        try:
            subProc('mount -o remount /', logfile)
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)
        break
    c += 1
