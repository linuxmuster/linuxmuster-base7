#!/usr/bin/python3
#
# final tasks
# thomas@linuxmuster.net
# 20250422

import configparser
import environment
import glob
import os
import re
import sys

from functions import getSetupValue, mySetupLogfile, printScript, readTextfile, \
    subProc, waitForFw, writeTextfile

logfile = mySetupLogfile(__file__)

# remove temporary files
if os.path.isfile('/tmp/setup.ini'):
    os.unlink('/tmp/setup.ini')

# get various setup values
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    adminpw = getSetupValue('adminpw')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# fix netplan file permissions
for file in glob.glob('/etc/netplan/*.yaml*'):
    os.chmod(file, 0o600)

# restart apparmor service
msg = 'Restarting apparmor service '
printScript(msg, '', False, False, True)
try:
    subProc('systemctl restart apparmor.service', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# write schoolname to sophomorix school.conf
msg = 'Writing school name to school.conf '
printScript(msg, '', False, False, True)
try:
    schoolname = getSetupValue('schoolname')
    rc, content = readTextfile(environment.SCHOOLCONF)
    # need to use regex because sophomorix config files do not do not comply with the ini file standard
    content = re.sub(r'SCHOOL_LONGNAME=.*\n',
                     'SCHOOL_LONGNAME=' + schoolname + '\n', content)
    rc = writeTextfile(environment.SCHOOLCONF, content, 'w')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# import devices
msg = 'Starting device import '
printScript(msg, '', False, False, True)
try:
    subProc('linuxmuster-import-devices', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# wait for fw
skipfw = getSetupValue('skipfw')
if not skipfw:
    try:
        waitForFw(wait=30)
    except Exception as error:
        print(error)
        sys.exit(1)

# import subnets
msg = 'Starting subnets import '
printScript(msg, '', False, False, True)
try:
    subProc('linuxmuster-import-subnets', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# create web proxy sso keytab
msg = 'Creating web proxy sso keytab '
printScript(msg, '', False, False, True)
try:
    subProc(environment.FWSHAREDIR + "/create-keytab.py -v -a '" + adminpw + "'", logfile, True)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# admin password not more needed in setup.ini
msg = 'Removing admin password from setup.ini '
printScript(msg, '', False, False, True)
setupini = environment.SETUPINI
try:
    setup = configparser.RawConfigParser(
        delimiters=('='), inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    setup.set('setup', 'adminpw', '')
    with open(setupini, 'w') as INIFILE:
        setup.write(INIFILE)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
