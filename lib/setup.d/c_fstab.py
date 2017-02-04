#!/usr/bin/python3
#
# c_fstab.py
# thomas@linuxmuster.net
# 20160915
#

import constants
import os
import reconfigure

from reconfigure.configs import FSTabConfig
from reconfigure.items.fstab import FilesystemData

print ('### ' + os.path.basename(__file__))

# patch fstab with mount options
config = FSTabConfig(path='/etc/fstab')
config.load()
c = 0
while True:
    if config.tree.filesystems[c].mountpoint == '/':
        print ('Modifying mount options for / ...')
        config.tree.filesystems[c].options = constants.ROOTMNTOPTS
        config.save()
        print ('Remounting / ...')
        os.system('mount -o remount /')
        break
    c += 1

