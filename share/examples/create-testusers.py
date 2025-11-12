#!/usr/bin/python3
#
# create a bunch of testusers
# thomas@linuxmuster.net
# 20251112
#

import configparser
import environment
import getopt
import os
import subprocess
import sys

from linuxmuster_base7.functions import printScript
from linuxmuster_base7.functions import sambaTool
from linuxmuster_base7.functions import replaceInFile
from shutil import copyfile

starget = environment.DEFAULTSCHOOL + '/students.csv'
ttarget = environment.DEFAULTSCHOOL + '/teachers.csv'


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
    print(err)  # will print something like "option -a not recognized"
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
ssource = environment.EXAMPLEDIR + '/students.csv'
tsource = environment.EXAMPLEDIR + '/teachers.csv'
copyfile(ssource, starget)
copyfile(tsource, ttarget)

# script header
filename = os.path.basename(__file__).replace('.py', '')

title = 'Creating test users for default-school'
printScript('', 'begin')
printScript(title)

# set password policy
msg = 'Password policy setup '
printScript(msg, '', False, False, True)
try:
    replaceInFile(environment.SCHOOLCONF, 'RANDOM_PWD=yes', 'RANDOM_PWD=no')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# check
msg = 'Running sophomorix-check '
printScript(msg, '', False, False, True)
try:
    subprocess.run(['sophomorix-check'], check=True)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# add
msg = 'Running sophomorix-add '
printScript(msg, '', False, False, True)
try:
    subprocess.run(['sophomorix-add'], check=True)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# quota
msg = 'Running sophomorix-quota '
printScript(msg, '', False, False, True)
try:
    subprocess.run(['sophomorix-quota'], check=True)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get usernames
msg = 'Get usernames '
printScript(msg, '', False, False, True)
try:
    result = subprocess.run(
        ['sophomorix-query', '--schoolbase', 'default-school', '--student', '--user-minimal'],
        capture_output=True, text=True, check=True)
    students = [line.split()[1] for line in result.stdout.split('\n')
                if line and any(c.isdigit() for c in line) and ':' in line]

    result = subprocess.run(
        ['sophomorix-query', '--schoolbase', 'default-school', '--teacher', '--user-minimal'],
        capture_output=True, text=True, check=True)
    teachers = [line.split()[1] for line in result.stdout.split('\n')
                if line and any(c.isdigit() for c in line) and ':' in line]
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# change password to Muster!
pw = environment.ROOTPW
msg = 'Setting user passwords to "' + pw + '" '
printScript(msg)
for user in students + teachers:
    if user == '':
        continue
    msg = ' * ' + user + ' '
    printScript(msg, '', False, False, True)
    try:
        subprocess.run(['sophomorix-passwd', '--user', user, '--pass', pw], check=True)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))

msg = 'done! '
printScript(msg)
printScript('', 'end')
