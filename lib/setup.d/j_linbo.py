#!/usr/bin/python3
#
# j_linbo.py
# thomas@linuxmuster.net
# 20170426
#

import configparser
import constants
import os
import re
import sys

from functions import setupComment
from functions import backupCfg
from functions import readTextfile
from functions import writeTextfile
from functions import printScript
from functions import modIni
from functions import isValidPassword
from functions import enterPassword
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read INIFILE, get schoolname
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    serverip = setup.get('setup', 'serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# test adminpw
try:
    adminpw = setup.get('setup', 'adminpw')
except:
    adminpw=''
if not isValidPassword(adminpw):
    printScript('There is no admin password!')
    adminpw = enterPassword('admin', True)
    if not isValidPassword(adminpw):
        printScript('No valid admin password! Aborting!')
        sys.exit(1)
    else:
        msg = 'Saving admin password to setup.ini '
        printScript(msg, '', False, False, True)
        rc = modIni(constants.SETUPINI, 'setup', 'adminpw', adminpw)
        if rc == True:
            printScript(' Success!', '', True, True, False, len(msg))
        else:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

# write linbo auth data to rsyncd.secrets
msg = 'Creating rsync secrets file '
printScript(msg, '', False, False, True)
configfile = '/etc/rsyncd.secrets'
filedata = setupComment() + '\n' + 'linbo:' + adminpw + '\n'
try:
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
    # set permissions
    subProc('chmod 600 ' + configfile, logfile)
    # enable rsync service
    subProc('systemctl enable rsync.service', logfile)
    # restart rsync service
    subProc('service rsync stop', logfile)
    subProc('service rsync start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# set serverip in default start.conf
startconf = constants.LINBODIR + '/start.conf'
msg = 'Writing server ip to default start.conf '
printScript(msg, '', False, False, True)
try:
    s = configparser.ConfigParser(strict=False)
    s.read(startconf)
    s.set('LINBO', 'Server', serverip)
    with open(startconf, 'w') as config:
        s.write(config)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# bittorrent service
msg = 'Activating bittorrent tracker '
printScript(msg, '', False, False, True)
try:
    defaultconf = '/etc/default/bittorrent'
    rc, content = readTextfile(defaultconf)
    content = re.sub(r'\nSTART_BTTRACK=.*\n', '\nSTART_BTTRACK=1\n', content, re.IGNORECASE)
    content = re.sub(r'\n[#]*ALLOWED_DIR=.*\n', '\nALLOWED_DIR=' + constants.LINBODIR + '\n', content, re.IGNORECASE)
    writeTextfile(defaultconf, content, 'w')
    subProc('service bittorrent stop', logfile)
    subProc('service bittorrent start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# linbo-bittorrent service
msg = 'Activating linbo-bittorrent service '
printScript(msg, '', False, False, True)
try:
    defaultconf = '/etc/default/linbo-bittorrent'
    rc, content = readTextfile(defaultconf)
    content = re.sub(r'\nSTART_BITTORRENT=.*\n', '\nSTART_BITTORRENT=1\n', content, re.IGNORECASE)
    writeTextfile(defaultconf, content, 'w')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# linbofs update
msg = 'Starting update-linbofs '
printScript(msg, '', False, False, True)
try:
    subProc('update-linbofs', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
