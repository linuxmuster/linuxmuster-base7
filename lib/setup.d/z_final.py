#!/usr/bin/python3
#
# final tasks
# thomas@linuxmuster.net
# 20200416
#

import constants
import os
import sys

from functions import getSetupValue
from functions import printScript
from functions import subProc
from functions import waitForFw

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# remove temporary files
if os.path.isfile('/tmp/setup.ini'):
    os.unlink('/tmp/setup.ini')

# disable unwanted services
unwanted = ['iscsid', 'dropbear', 'lxcfs']
for item in unwanted:
    msg = 'Disabling service ' + item + ' '
    printScript(msg, '', False, False, True)
    try:
        subProc('systemctl stop ' + item + '.service', logfile)
        subProc('systemctl disable ' + item + '.service', logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' not installed!', '', True, True, False, len(msg))

# restart apparmor service
msg = 'Restarting apparmor service '
printScript(msg, '', False, False, True)
try:
    subProc('systemctl restart apparmor.service', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# import devices
msg = 'Starting device import '
printScript(msg, '', False, False, True)
try:
    subProc('linuxmuster-import-devices', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# wait for fw
skipfw = getSetupValue('skipfw')
if skipfw == 'False':
    try:
        waitForFw(wait=30)
    except:
        sys.exit(1)

# import subnets
msg = 'Starting subnets import '
printScript(msg, '', False, False, True)
try:
    subProc('linuxmuster-import-subnets', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create web proxy sso keytab
msg = 'Creating web proxy sso keytab '
printScript(msg, '', False, False, True)
try:
    subProc(constants.FWSHAREDIR + '/create-keytab.py -v', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
