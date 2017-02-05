#!/usr/bin/python3
#
# j_linbo.py
# thomas@linuxmuster.net
# 20170205
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

printScript('', 'begin')
printScript(os.path.basename(__file__))

# read INIFILE, get schoolname
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
adminpw = i.get('setup', 'adminpw')
serverip = i.get('setup', 'serverip')

# rsyncd secrets
configfile = '/etc/rsyncd.secrets'

# create filedata
filedata = setupComment() + '\n' + 'linbo:' + adminpw + '\n'

# write configfile
try:
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
except:
    print('Cannot write ' + configfile + '!')
    sys.exit(1)

# permissions
os.system('chmod 600 ' + configfile)

# restart services
os.system('service rsync restart')

# default start.conf
startconf = constants.LINBODIR + '/start.conf'
s = configparser.ConfigParser(strict=False)
s.read(startconf)
s.set('LINBO', 'Server', serverip)
with open(startconf, 'w') as config:
    s.write(config)

# bittorrent service
defaultconf = '/etc/default/bittorrent'
rc, content = readTextfile(defaultconf)
if rc == False:
    exit(1)
content = re.sub(r'\nSTART_BTTRACK=.*\n', '\nSTART_BTTRACK=1\n', content, re.IGNORECASE)
content = re.sub(r'\n[#]*ALLOWED_DIR=.*\n', '\nALLOWED_DIR=' + constants.LINBODIR + '\n', content, re.IGNORECASE)
rc = writeTextfile(defaultconf, content, 'w')
if rc == False:
    sys.exit(1)
os.system('service bittorrent stop')
os.system('service bittorrent start')

# linbo-bittorrent service
defaultconf = '/etc/default/linbo-bittorrent'
rc, content = readTextfile(defaultconf)
if rc == False:
    sys.exit(1)
content = re.sub(r'\nSTART_BITTORRENT=.*\n', '\nSTART_BITTORRENT=1\n', content, re.IGNORECASE)
rc = writeTextfile(defaultconf, content, 'w')
if rc == False:
    sys.exit(1)

# linbofs update
os.system('update-linbofs')
