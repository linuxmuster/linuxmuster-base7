#!/usr/bin/python3
#
# linbo setup
# thomas@linuxmuster.net
# 20300311
#

import configparser
import constants
import os
import re
import subprocess
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
    setup = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
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
msg = 'Providing server ip to linbo start.conf files '
# default start.conf
conffiles = [constants.LINBODIR + '/start.conf']
# collect example start.conf files
for item in os.listdir(constants.LINBODIR + '/examples'):
    if not item.startswith('start.conf.'):
        continue
    conffiles.append(constants.LINBODIR + '/examples/' + item)
printScript(msg, '', False, False, True)
try:
    for startconf in conffiles:
        rc, content = readTextfile(startconf)
        rc = writeTextfile(startconf, content.replace('10.16.1.1', serverip), 'w')
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
msg = 'Reconfiguring linbo (forking to background) '
printScript(msg, '', False, False, True)
try:
    subProc('rm -f ' + constants.SYSDIR + '/linbo/*key*', logfile)
    subprocess.call('dpkg-reconfigure linuxmuster-linbo7 >> ' + logfile + ' 2>&1 &', shell=True)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
