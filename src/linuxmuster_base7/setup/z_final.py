#!/usr/bin/python3
#
# final tasks
# thomas@linuxmuster.net
# 20250422

import configparser
import datetime
import glob
import os
import re
import shlex
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import getSetupValue, mySetupLogfile, printScript, readTextfile, \
    waitForFw, writeTextfile

logfile = mySetupLogfile(__file__)

# Helper function to run command with logging
def run_with_log(cmd_string, logfile, check_errors=False):
    """Execute command with output captured to logfile."""
    cmd_args = shlex.split(cmd_string) if isinstance(cmd_string, str) else cmd_string
    result = subprocess.run(cmd_args, capture_output=True, text=True, check=False, shell=False)
    if logfile and (result.stdout or result.stderr):
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
            log.write('#### ' + (cmd_string if isinstance(cmd_string, str) else ' '.join(cmd_args)) + ' ####\n')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
    if check_errors and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd_args, result.stdout, result.stderr)
    return result


# remove temporary files
if os.path.isfile('/tmp/setup.ini'):
    os.unlink('/tmp/setup.ini')

# get various setup values
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    adminpw = getSetupValue('adminpw')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# fix netplan file permissions
for file in glob.glob('/etc/netplan/*.yaml*'):
    os.chmod(file, 0o600)

# restart apparmor service
msg = 'Restarting apparmor service '
printScript(msg, '', False, False, True)
try:
    run_with_log(['systemctl', 'restart', 'apparmor.service'], logfile, check_errors=True)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
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
    run_with_log('linuxmuster-import-devices', logfile, check_errors=True)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
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
    run_with_log('linuxmuster-import-subnets', logfile, check_errors=True)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create web proxy sso keytab
msg = 'Creating web proxy sso keytab '
printScript(msg, '', False, False, True)
try:
    run_with_log(environment.FWSHAREDIR + "/create-keytab.py -v -a '" + adminpw + "'", logfile, check_errors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# admin password not more needed in setup.ini
msg = 'Removing admin password from setup.ini '
printScript(msg, '', False, False, True)
setupini = environment.SETUPINI
try:
    setup = configparser.RawConfigParser(delimiters=('='))
    setup.read(setupini)
    setup.set('setup', 'adminpw', '')
    with open(setupini, 'w') as INIFILE:
        setup.write(INIFILE)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
