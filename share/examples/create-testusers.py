#!/usr/bin/python3
#
# create a bunch of testusers
# thomas@linuxmuster.net
# 20181005
#

import configparser
import constants
import getopt
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

def usage():
    print('Usage: create-testusers.py [options]')
    print(' [options] may be:')
    print(' -f, --force   : Ignore existing users.')
    print(' -h, --help    : Print this help.')

# get cli args
force = False
try:
    opts, args = getopt.getopt(sys.argv[1:], "fh", ["force", "help"])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)
for o, a in opts:
    if o in ("-f", "--force"):
        force = True
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"

# do not overwrite existing user files
if not force:
    if os.path.isfile(starget) or os.path.isfile(ttarget):
        print('There are already users on the system!')
        usage()
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
    students = os.popen("sophomorix-query --schoolbase default-school --student --user-minimal | grep [1-9]: | awk '{ print $2 }'").read().split('\n')
    teachers = os.popen("sophomorix-query --schoolbase default-school --teacher --user-minimal | grep [1-9]: | awk '{ print $2 }'").read().split('\n')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# change password to Muster!
pw = constants.ROOTPW
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
