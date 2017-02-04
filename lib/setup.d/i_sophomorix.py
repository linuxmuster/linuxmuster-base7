#!/usr/bin/python3
#
# i_sophomorix.py
# thomas@linuxmuster.net
# 20170128
#

import configparser
import constants
import os
import re

from functions import setupComment
from functions import backupCfg

print ('### ' + os.path.basename(__file__))

# read INIFILE, get schoolname
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
schoolname = i.get('setup', 'schoolname')

# configuration file
schoolconf = constants.SCHOOLCONF

# read configfile
try:
    with open(schoolconf, 'r') as infile:
        filedata = infile.read()
except:
    print('Cannot read ' + schoolconf + '!')
    quit()

# replace old setup comment
filedata = re.sub(r'# modified by linuxmuster-setup.*\n', '', filedata)

# add newline at the end
if not filedata[-1] == '\n':
    filedata = filedata + '\n'

# set schoolname to value from inifile
filedata = re.sub(r'\n$SCHOOL_NAME=.*\n', '\n$SCHOOL_NAME="' + schoolname + '";\n', filedata)

# set comment
filedata = setupComment() + filedata

# backup and write configfile
try:
    backupCfg(schoolconf)
    with open(schoolconf, 'w') as outfile:
        outfile.write(filedata)
except:
    print('Cannot write ' + schoolconf + '!')
    quit()
