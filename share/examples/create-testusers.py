#!/usr/bin/python3
#
# create a bunch of testusers
# thomas@linuxmuster.net
# 20251113
#

import configparser
import datetime
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
logfile = environment.LOGDIR + '/create-testusers.log'


def usage():
    print('Usage: create-testusers.py [options]')
    print(' [options] may be:')
    print(' -f, --force   : Ignore existing users.')
    print(' -h, --help    : Print this help.')


def run_with_log(cmd_list, cmd_desc):
    """Run command and log output to logfile"""
    with open(logfile, 'a') as log:
        log.write('-' * 78 + '\n')
        log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
        log.write('#### ' + cmd_desc + ' ####\n')
        log.flush()
        result = subprocess.run(cmd_list, stdout=log, stderr=subprocess.STDOUT, check=True)
    return result


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

# initialize logfile
with open(logfile, 'w') as log:
    log.write('-' * 78 + '\n')
    log.write('#### ' + os.path.basename(__file__) + ' started at '
              + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
    log.write('-' * 78 + '\n')

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
    run_with_log(['sophomorix-check'], 'sophomorix-check')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# add
msg = 'Running sophomorix-add '
printScript(msg, '', False, False, True)
try:
    run_with_log(['sophomorix-add'], 'sophomorix-add')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# quota
msg = 'Running sophomorix-quota '
printScript(msg, '', False, False, True)
try:
    run_with_log(['sophomorix-quota'], 'sophomorix-quota')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get usernames
msg = 'Get usernames '
printScript(msg, '', False, False, True)
try:
    with open(logfile, 'a') as log:
        log.write('-' * 78 + '\n')
        log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
        log.write('#### sophomorix-query --student --teacher ####\n')
        result = subprocess.run(
            ['sophomorix-query', '--schoolbase', 'default-school', '--student', '--teacher', '--user-minimal'],
            capture_output=True, text=True, check=True)
        log.write(result.stdout)
        if result.stderr:
            log.write(result.stderr)
        log.write('-' * 78 + '\n')
    users = [line.split()[1] for line in result.stdout.split('\n')
                if line and any(c.isdigit() for c in line) and ':' in line
                and 'SophomorixSchemaVersion' not in line
                and 'USERS' not in line]

    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# change password to Muster!
pw = environment.ROOTPW
msg = 'Setting user passwords to "' + pw + '" '
printScript(msg)
for user in users:
    if user == '':
        continue
    msg = ' * ' + user + ' '
    printScript(msg, '', False, False, True)
    try:
        run_with_log(['sophomorix-passwd', '--user', user, '--pass', pw],
                     'sophomorix-passwd --user ' + user)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))

msg = 'done! '
printScript(msg)

# finalize logfile
with open(logfile, 'a') as log:
    log.write('-' * 78 + '\n')
    log.write('#### ' + os.path.basename(__file__) + ' finished at '
              + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
    log.write('-' * 78 + '\n')

printScript('', 'end')
