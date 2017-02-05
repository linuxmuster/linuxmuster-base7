#!/usr/bin/python3
#
# k_cups.py
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
from functions import printScript

printScript('', 'begin')
printScript(os.path.basename(__file__))

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
ssldir = constants.SSLDIR

configfile = '/etc/cups/cups-files.conf'

# read config
try:
    with open(configfile, 'r') as infile:
        filedata = infile.read()
except:
    print('Cannot read ' + configfile + '!')
    sys.exit(1)

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

# write config back
try:
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
except:
    print('Cannot write ' + configfile + '!')
    sys.exit(1)

# service restart
os.system('service cups restart')
os.system('service cups-browsed restart')
