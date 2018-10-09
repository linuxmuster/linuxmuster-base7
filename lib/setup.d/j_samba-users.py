#!/usr/bin/python3
#
# create samba users
# thomas@linuxmuster.net
# 20181009
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
    binduserpw = randomPassword(16)
    with open(constants.BINDUSERSECRET, 'w') as secret:
        secret.write(binduserpw)
    subProc('chmod 400 ' + constants.SECRETDIR + '/*', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# samba backup
msg = 'Backing up samba '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-samba --backup-samba without-users', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# renew sophomorix configs
os.system('rm -f ' + constants.SCHOOLCONF)
os.system('rm -f ' + constants.SOPHOSYSDIR + '/sophomorix.conf')
subProc('sophomorix-postinst', logfile)

# create default-school share
schoolname = os.path.basename(constants.DEFAULTSCHOOL)
defaultpath = constants.SCHOOLSSHARE + '/' + schoolname
shareopts = constants.SCHOOLSSHAREOPTS
msg = 'Creating share for ' + schoolname
printScript(msg, '', False, False, True)
try:
    subProc('net conf addshare ' + schoolname + ' ' + defaultpath + ' ' + shareopts, logfile)
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
msg = 'Creating ou for ' + schoolname
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-school --create --school ' + schoolname, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
