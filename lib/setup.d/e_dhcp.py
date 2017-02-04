#!/usr/bin/python3
#
# e_dhcp.py
# thomas@linuxmuster.net
# 20160915
#

import configparser
import constants
import os
import re

from functions import setupComment
from functions import backupCfg

print ('### ' + os.path.basename(__file__))

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
iface = i.get('setup', 'iface')

# configuration file
configfile = '/etc/default/isc-dhcp-server'

# read configfile
try:
    with open(configfile, 'r') as infile:
        filedata = infile.read()
except:
    print('Cannot read ' + configfile + '!')
    exit(1)

# replace old setup comment
filedata = re.sub(r'# modified by linuxmuster-setup.*\n', '', filedata)

# add newline at the end
if not filedata[-1] == '\n':
    filedata = filedata + '\n'

# set INTERFACES to value from inifile
filedata = re.sub(r'\nINTERFACES=.*\n', '\nINTERFACES="' + iface + '"\n', filedata)

# set comment
filedata = setupComment() + filedata

# backup original configfile and write changes finally without dummy section in first line
try:
    backupCfg(configfile)
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
except:
    print('Cannot write ' + configfile + '!')
    exit(1)

# restart dhcp service
os.system('service isc-dhcp-server stop')
os.system('service isc-dhcp-server start')
