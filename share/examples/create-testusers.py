#!/usr/bin/python3
#
# create a bunch of testusers
# thomas@linuxmuster.net
# 20180504
#

import configparser
import constants
import os
import sys

from functions import printScript
from functions import sambaTool
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

# get password from setup.ini
msg = 'Reading password '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    # setup.ini
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    pw = setup.get('setup', 'adminpw')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# set password policy
msg = 'Password policy setup '
printScript(msg, '', False, False, True)
try:
    replaceInFile(constants.SCHOOLCONF, 'RANDOM_PWD=yes', 'RANDOM_PWD=no')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# check
msg = 'Running sophomorix-check '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-check', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# add
msg = 'Running sophomorix-add '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-add', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# quota
msg = 'Running sophomorix-quota '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-quota', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get usernames
msg = 'Get usernames '
printScript(msg, '', False, False, True)
try:
    students = os.popen("sophomorix-query --schoolbase default-school --student --user-minimal | grep ^' ' | awk '{ print $2 }'").read().split('\n')
    teachers = os.popen("sophomorix-query --schoolbase default-school --teacher --user-minimal | grep ^' ' | awk '{ print $2 }'").read().split('\n')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# change password to Muster!
msg = 'Setting user passwords to "' + pw + '" '
printScript(msg)
for user in students + teachers:
    if user == '':
        continue
    msg = ' * ' + user + ' '
    printScript(msg, '', False, False, True)
    try:
        sambaTool('user setpassword ' + user + ' --newpassword="' + pw + '"')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))

msg = 'done! '
printScript(msg)
printScript('', 'end')
