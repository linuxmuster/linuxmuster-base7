#!/usr/bin/python3
#
# patch fstab with mount options
# thomas@linuxmuster.net
# 20220105
#

"""
Setup module e_fstab: Configure filesystem mount options in /etc/fstab.

This module:
- Reads /etc/fstab configuration
- Modifies mount options for root (/) and /srv filesystems
- Applies mount options from environment.ROOTMNTOPTS (typically includes user_xattr, acl)
- Remounts filesystems with new options immediately
- Logs all mount operations

Mount options are critical for proper ACL and extended attribute support
needed by Samba and other services.
"""

import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import os
import reconfigure
import sys

from functions import mySetupLogfile, printScript
from reconfigure.configs import FSTabConfig
from reconfigure.items.fstab import FilesystemData
import subprocess
import datetime

logfile = mySetupLogfile(__file__)

# Load and modify /etc/fstab to set proper mount options
config = FSTabConfig(path='/etc/fstab')
config.load()
c = 0
mountpoints = ['/', '/srv']  # Filesystems that need ACL and xattr support
while True:
    # Iterate through all fstab entries
    try:
        for i in mountpoints:
            # Check if current entry matches one of our target mountpoints
            if config.tree.filesystems[c].mountpoint == i:
                msg = 'Modifying mount options for ' + i + ' '
                printScript(msg, '', False, False, True)
                try:
                    # Apply mount options from environment (user_xattr, acl, etc.)
                    config.tree.filesystems[c].options = environment.ROOTMNTOPTS
                    # Write updated fstab
                    config.save()
                    printScript(' Success!', '', True, True, False, len(msg))
                except Exception as error:
                    printScript(f' Failed: {error}', '', True, True, False, len(msg))
                    sys.exit(1)

                # Remount filesystem immediately to apply new options
                msg = 'Remounting ' + i + ' '
                printScript(msg, '', False, False, True)
                try:
                    result = subprocess.run(['mount', '-o', 'remount', i], capture_output=True, text=True, check=False)
                    # Log mount command output if any
                    if logfile and (result.stdout or result.stderr):
                        with open(logfile, 'a') as log:
                            log.write('-' * 78 + '\n')
                            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
                            log.write('#### mount -o remount ' + i + ' ####\n')
                            if result.stdout:
                                log.write(result.stdout)
                            if result.stderr:
                                log.write(result.stderr)
                            log.write('-' * 78 + '\n')
                    printScript(' Success!', '', True, True, False, len(msg))
                except Exception as error:
                    printScript(f' Failed: {error}', '', True, True, False, len(msg))
                    sys.exit(1)
        # Move to next fstab entry
        c += 1
    # Exit loop when all entries have been processed
    except Exception as error:
        break
