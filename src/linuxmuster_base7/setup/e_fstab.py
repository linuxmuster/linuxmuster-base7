#!/usr/bin/python3
#
# patch fstab with mount options
# thomas@linuxmuster.net
# 20220105
#

import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import os
import reconfigure
import sys

from linuxmuster_base7.functions import mySetupLogfile, printScript, subProc
from reconfigure.configs import FSTabConfig
from reconfigure.items.fstab import FilesystemData

logfile = mySetupLogfile(__file__)

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
                    # get mount options from environment
                    config.tree.filesystems[c].options = environment.ROOTMNTOPTS
                    # save fstab
                    config.save()
                    printScript(' Success!', '', True, True, False, len(msg))
                except Exception as error:
                    printScript(f' Failed: {error}', '', True, True, False, len(msg))
                    sys.exit(1)
                msg = 'Remounting ' + i + ' '
                printScript(msg, '', False, False, True)
                # try to remount filesystem with new options
                try:
                    subProc('mount -o remount ' + i, logfile)
                    printScript(' Success!', '', True, True, False, len(msg))
                except Exception as error:
                    printScript(f' Failed: {error}', '', True, True, False, len(msg))
                    sys.exit(1)
        # next entry
        c += 1
    # break if entries ran out
    except Exception as error:
        break
