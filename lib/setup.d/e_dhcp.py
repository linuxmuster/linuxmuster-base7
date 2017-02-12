#!/usr/bin/python3
#
# e_dhcp.py
# thomas@linuxmuster.net
# 20170212
#

import configparser
import constants
import os
import re
import sys

from functions import setupComment
from functions import backupCfg
from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup.ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser()
    setup.read(setupini)
    iface = setup.get('setup', 'iface')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# read configfile
msg = 'Reading dhcp configuration '
printScript(msg, '', False, False, True)
configfile = '/etc/default/isc-dhcp-server'
try:
    with open(configfile, 'r') as infile:
        filedata = infile.read()
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# modify config data
msg = 'Modifying dhcp configuration '
printScript(msg, '', False, False, True)
try:
    # replace old setup comment
    filedata = re.sub(r'# modified by linuxmuster-setup.*\n', '', filedata)
    # add newline at the end
    if not filedata[-1] == '\n':
        filedata = filedata + '\n'
    # set INTERFACES to value from inifile
    filedata = re.sub(r'\nINTERFACES=.*\n', '\nINTERFACES="' + iface + '"\n', filedata)
    # set comment
    filedata = setupComment() + filedata
    # backup original configfile
    backupCfg(configfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

 # write changes
msg = 'Writing back dhcp configuration '
printScript(msg, '', False, False, True)
try:
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# restart dhcp service
msg = 'Restarting dhcp service '
printScript(msg, '', False, False, True)
try:
    subProc('service isc-dhcp-server stop', logfile)
    subProc('service isc-dhcp-server start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
