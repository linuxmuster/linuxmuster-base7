#!/usr/bin/python3
#
# e_samba-users.py
# thomas@linuxmuster.net
# 20170324
#

import configparser
import constants
import os
import sys
from functions import randomPassword
from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser()
    setup.read(setupini)
    adminpw = setup.get('setup', 'adminpw')
    domainname = setup.get('setup', 'domainname')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create sophomorix admin user
msg = 'Calculating random password for sophomorix-admin '
printScript(msg, '', False, False, True)
try:
    sophadminpw = randomPassword(16)
    with open(constants.SOPHADMINSECRET, 'w') as secret:
        secret.write(sophadminpw)
    subProc('chmod 600 ' + constants.SOPHADMINSECRET, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

msg = 'Creating samba account for sophomorix-admin '
printScript(msg, '', False, False, True)
try:
    subProc('samba-tool user create sophomorix-admin "' + sophadminpw + '"', logfile)
    subProc('samba-tool user setexpiry sophomorix-admin --noexpiry', logfile)
    subProc('samba-tool group addmembers "Domain Admins" sophomorix-admin', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global-admin
msg = 'Creating samba account for global-admin '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create global-admin --school global --password ' + adminpw, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create default-school, no connection to ad
msg = 'Creating ou for default-school '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-school --create --school default-school', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
