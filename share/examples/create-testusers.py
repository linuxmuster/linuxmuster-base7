#!/usr/bin/python3
#
# create a bunch of testusers
# thomas@linuxmuster.net
# 20180225
#

import constants
import os
import sys

from functions import printScript
from functions import subProc
from functions import replaceInFile
from shutil import copyfile
from subprocess import Popen, PIPE, STDOUT

starget = constants.DEFAULTSCHOOL + '/students.csv'
ttarget = constants.DEFAULTSCHOOL + '/teachers.csv'

# do not overwrite existing user files
if os.path.isfile(starget) or os.path.isfile(ttarget):
    print('There are already users on the system!')
    sys.exit(1)

# copy example user files
ssource = constants.EXAMPLEDIR + '/students.csv'
tsource = constants.EXAMPLEDIR + '/teachers.csv'
copyfile(ssource, starget)
copyfile(tsource, ttarget)

# script header
filename = os.path.basename(__file__).replace('.py', '')
logfile = constants.LOGDIR + '/' + filename + '.log'

title = 'Creating test users for default-school'
printScript('', 'begin')
printScript(title)

msg = 'Logging to ' + logfile
printScript(msg)

# set password policy
msg = 'password policy setup '
printScript(msg, '', False, False, True)
try:
    replaceInFile(constants.SCHOOLCONF, 'RANDOM_PWD=yes', 'RANDOM_PWD=no')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# check
msg = 'sophomorix-check '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-check', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# add
msg = 'sophomorix-add '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-add', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# quota
msg = 'sophomorix-quota '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-quota', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

msg = 'All user passwords are set to: "LinuxMuster!" '
printScript(msg)
printScript('', 'end')
