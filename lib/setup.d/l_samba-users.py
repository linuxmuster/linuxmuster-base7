#!/usr/bin/python3
#
# create samba users
# thomas@linuxmuster.net
# 20170812
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
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    adminpw = setup.get('setup', 'adminpw')
    domainname = setup.get('setup', 'domainname')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create sophomorix admin user
msg = 'Calculating random passwords '
printScript(msg, '', False, False, True)
try:
    sophadminpw = randomPassword(16)
    with open(constants.SOPHADMINSECRET, 'w') as secret:
        secret.write(sophadminpw)
    binduserpw = randomPassword(16)
    with open(constants.BINDUSERSECRET, 'w') as secret:
        secret.write(binduserpw)
    subProc('chmod 400 ' + constants.SECRETDIR + '/*', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

msg = 'Creating samba account for sophomorix-admin '
printScript(msg, '', False, False, True)
try:
    subProc('samba-tool user create sophomorix-admin "' + sophadminpw + '"', logfile)
    subProc('samba-tool group addmembers "Domain Admins" sophomorix-admin', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global-admin
msg = 'Creating samba account for global-admin '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create-global-admin global-admin --password ' + adminpw, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global bind user
msg = 'Creating samba account for global-binduser '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create-global-binduser global-binduser --password ' + binduserpw, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)


# no expiry for Administrator password
msg = 'No expiry for administrative passwords '
printScript(msg, '', False, False, True)
try:
    for i in ['Administrator', 'global-admin', 'sophomorix-admin', 'global-binduser']:
        subProc('samba-tool user setexpiry ' + i + ' --noexpiry', logfile)
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
