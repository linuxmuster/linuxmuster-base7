#!/usr/bin/python3
#
# k_cups.py
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

# read constants
ssldir = constants.SSLDIR

# read cups config
msg = 'Reading cups configuration '
printScript(msg, '', False, False, True)
configfile = '/etc/cups/cups-files.conf'
try:
    with open(configfile, 'r') as infile:
        filedata = infile.read()
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

msg = 'Modifying cups configuration '
printScript(msg, '', False, False, True)
try:
    # replace old setup comment
    filedata = re.sub(r'# modified by linuxmuster-setup.*\n', '', filedata)
    # needed entries
    certkw = 'ServerCertificate'
    certline = certkw + ' ' + ssldir + '/server.crt\n'
    keykw = 'ServerKey'
    keyline = keykw + ' ' + ssldir + '/server.key\n'
    # remove old entries
    if not filedata[-1] == '\n':
        filedata = filedata + '\n'
    filedata = re.sub(r'\n' + certkw + '.*\n', '\n', filedata)
    filedata = re.sub(r'\n' + keykw + '.*\n', '\n', filedata)
    # add entries
    filedata = filedata + certline + keyline
    # add setup comment
    filedata = setupComment() + filedata
    # backup original file
    backupCfg(configfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# write config back
msg = 'Writing back cups configuration '
printScript(msg, '', False, False, True)
try:
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# service restart
msg = 'Restarting cups services '
printScript(msg, '', False, False, True)
try:
    subProc('service cups restart', logfile)
    subProc('service cups-browsed restart', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
