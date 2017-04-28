#!/usr/bin/python3
#
# c_fstab.py
# thomas@linuxmuster.net
# 20170428
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
mountpoints = ['/', '/srv']
while True:
    # try all fstab entries
    try:
        for i in mountpoints:
            # if mountpoint matches change mount options
            if config.tree.filesystems[c].mountpoint == i:
                msg = 'Modifying mount options for ' + i + ' '
                printScript(msg, '', False, False, True)
                try:
                    # get mount options from constants
                    config.tree.filesystems[c].options = constants.ROOTMNTOPTS
                    # save fstab
                    config.save()
                    printScript(' Success!', '', True, True, False, len(msg))
                except:
                    printScript(' Failed!', '', True, True, False, len(msg))
                    sys.exit(1)
                msg = 'Remounting ' + i + ' '
                printScript(msg, '', False, False, True)
                # try to remount filesystem with new options
                try:
                    subProc('mount -o remount ' + i, logfile)
                    printScript(' Success!', '', True, True, False, len(msg))
                except:
                    printScript(' Failed!', '', True, True, False, len(msg))
                    sys.exit(1)
        # next entry
        c += 1
    # break if entries ran out
    except:
        break
