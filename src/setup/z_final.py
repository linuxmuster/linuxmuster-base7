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

from functions import getSetupValue, mySetupLogfile, printScript, readTextfile, \
    waitForFw, writeTextfile
from setup.helpers import runWithLog

logfile = mySetupLogfile(__file__)

# Constants for file permissions and timeouts
NETPLAN_PERMISSIONS = 0o600  # Netplan files should be readable only by root
FIREWALL_WAIT_TIMEOUT = 30   # Seconds to wait for firewall to become ready

# Clean up temporary setup files from /tmp
# This removes the temporary copy created during setup
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
# Netplan files may contain sensitive network credentials and should not be world-readable
for file in glob.glob('/etc/netplan/*.yaml*'):
    os.chmod(file, NETPLAN_PERMISSIONS)

# Disable isc-dhcp-server6.service
# IPv6 DHCP is not used in linuxmuster.net, so we stop, disable and mask the service
# to prevent it from starting and consuming resources
msg = 'Disabling isc-dhcp-server6 service '
printScript(msg, '', False, False, True)
try:
    for item in ['stop', 'disable', 'mask']:
        runWithLog(['systemctl', item, 'isc-dhcp-server6.service'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    # Non-critical: Continue even if dhcpv6 disable fails

# Restart apparmor to apply new security profiles
# AppArmor profiles for services like dhcpd and ntpd were updated during setup
# and need to be reloaded to take effect
msg = 'Restarting apparmor service '
printScript(msg, '', False, False, True)
try:
    runWithLog(['systemctl', 'restart', 'apparmor.service'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Write school name to sophomorix configuration
# The school long name is displayed in various places in the web UI and reports
# We use regex instead of configparser because sophomorix config files use
# shell-style KEY=VALUE format without sections
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
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Import devices from devices.csv into system (DHCP, DNS, LINBO configuration)
# This creates DHCP host declarations, DNS entries, and PXE boot configurations
# for all devices defined in /etc/linuxmuster/sophomorix/default-school/devices.csv
msg = 'Starting device import '
printScript(msg, '', False, False, True)
try:
    runWithLog(['linuxmuster-import-devices'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Wait for firewall to become ready after configuration
# The firewall may need time to restart services and become fully operational
# after the previous configuration steps
skipfw = getSetupValue('skipfw')
if not skipfw:
    try:
        waitForFw(wait=FIREWALL_WAIT_TIMEOUT)
    except Exception as error:
        printScript(f'Firewall wait timeout: {error}')
        sys.exit(1)

# Import subnet configuration to firewall and network
# This configures DHCP subnets, firewall routes, static routes in netplan,
# and NTP configuration based on /etc/linuxmuster/subnets.csv
msg = 'Starting subnets import '
printScript(msg, '', False, False, True)
try:
    runWithLog(['linuxmuster-import-subnets'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Create Kerberos keytab for web proxy SSO authentication
# This enables transparent authentication for users accessing the internet through
# the OPNsense web proxy (squid). The keytab allows the proxy to authenticate users
# via Kerberos without prompting for credentials
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
# The global admin password is no longer needed after setup completion
# and should not be stored in plain text. We blank it out to reduce security risk.
# Note: The password is still stored in Samba's password database
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
