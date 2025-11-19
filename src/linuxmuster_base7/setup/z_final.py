#!/usr/bin/python3
#
# final tasks
# thomas@linuxmuster.net
# 20251119

"""
Setup module z_final: Perform final setup tasks and cleanup.

This module (executed last in setup sequence):
- Removes temporary setup files
- Fixes netplan file permissions for security
- Restarts apparmor service
- Writes school name to sophomorix configuration
- Imports devices from devices.csv into system
- Waits for firewall to be ready (if not skipped)
- Imports subnet configuration
- Creates web proxy SSO keytab for authentication
- Removes admin password from setup.ini for security

This is the last module in the setup chain and finalizes the installation.
"""

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
from linuxmuster_base7.setup.helpers import runWithLog

logfile = mySetupLogfile(__file__)

# Clean up temporary setup files from /tmp
if os.path.isfile('/tmp/setup.ini'):
    os.unlink('/tmp/setup.ini')

# Read admin password from setup configuration
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    adminpw = getSetupValue('adminpw')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Secure netplan configuration files (should be readable only by root)
for file in glob.glob('/etc/netplan/*.yaml*'):
    os.chmod(file, 0o600)

# disable isc-dhcp-server6.service
msg = 'Disabling isc-dhcp-server6 service '
printScript(msg, '', False, False, True)
try:
    for item in ['stop', 'disable', 'mask']:
        subProc('systemctl ' + item + ' isc-dhcp-server6.service', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))

# Restart apparmor to apply new security profiles
msg = 'Restarting apparmor service '
printScript(msg, '', False, False, True)
try:
    runWithLog(['systemctl', 'restart', 'apparmor.service'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Write school name to sophomorix configuration
msg = 'Writing school name to school.conf '
printScript(msg, '', False, False, True)
try:
    schoolname = getSetupValue('schoolname')
    rc, content = readTextfile(environment.SCHOOLCONF)
    # Use regex because sophomorix config files don't comply with INI standard
    content = re.sub(r'SCHOOL_LONGNAME=.*\n',
                     'SCHOOL_LONGNAME=' + schoolname + '\n', content)
    rc = writeTextfile(environment.SCHOOLCONF, content, 'w')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# Import devices from devices.csv into system (DHCP, DNS, etc.)
msg = 'Starting device import '
printScript(msg, '', False, False, True)
try:
    runWithLog(['linuxmuster-import-devices'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Wait for firewall to become ready after configuration
skipfw = getSetupValue('skipfw')
if not skipfw:
    try:
        waitForFw(wait=30)
    except Exception as error:
        print(error)
        sys.exit(1)

# Import subnet configuration to firewall
msg = 'Starting subnets import '
printScript(msg, '', False, False, True)
try:
    runWithLog(['linuxmuster-import-subnets'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Create Kerberos keytab for web proxy SSO authentication
if not skipfw:
    msg = 'Creating web proxy sso keytab '
    printScript(msg, '', False, False, True)
    try:
        runWithLog([environment.FWSHAREDIR + '/create-keytab.py', '-v', '-a', adminpw],
                logfile, checkErrors=False, maskSecrets=[adminpw])
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)

# Remove admin password from setup.ini for security
# Password is no longer needed after setup completion
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
