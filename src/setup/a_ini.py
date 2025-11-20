#!/usr/bin/python3
#
# process setup ini files
# thomas@linuxmuster.net
# 20251114
#

"""
Setup module a_ini: Process and validate setup configuration files.

This module:
- Reads and merges multiple INI configuration files (defaults, prep, setup, custom)
- Validates domain name, server name, and network configuration
- Derives additional values from primary configuration (realm, basedn, netmask, etc.)
- Calculates DHCP range based on network configuration
- Generates global binduser password
- Writes final setup.ini file
- Cleans up temporary configuration files

The configuration cascade: defaults.ini < prep.ini < setup.ini < custom.ini
"""

import configparser
import datetime
import os
import subprocess
import sys

sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from IPy import IP
from functions import isValidHostname, isValidDomainname, isValidHostIpv4
from functions import mySetupLogfile, printScript, randomPassword
from setup.helpers import runWithLog, buildIp, getNetworkPrefix, splitIpOctets
from setup.helpers import DHCP_RANGE_START_SUFFIX, DHCP_RANGE_END_SUFFIX
from setup.helpers import DHCP_RANGE_START_LARGE_NET, DHCP_RANGE_END_LARGE_NET

logfile = mySetupLogfile(__file__)

# Read and merge INI configuration files in priority order
# Files are read in cascade: each file can override values from previous ones
setup = configparser.RawConfigParser(delimiters=('='))
for item in [environment.DEFAULTSINI, environment.PREPINI, environment.SETUPINI, environment.CUSTOMINI]:
    # Skip non-existent files (e.g., custom.ini may not exist)
    if not os.path.isfile(item):
        continue
    # Read and merge configuration values
    msg = 'Reading ' + item + ' '
    printScript(msg, '', False, False, True)
    try:
        setup.read(item)
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)

# Validate and process domain name
# Domain name is the primary identifier from which other values are derived
msg = '* Domainname '
printScript(msg, '', False, False, True)
try:
    domainname = setup.get('setup', 'domainname')
    if not isValidDomainname(domainname):
        printScript(' ' + domainname + ' is not valid!',
                    '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + domainname, '', True, True, False, len(msg))
except Exception as error:
    printScript(f' not set: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Derive Samba/LDAP values from domain name
# Realm: uppercase version of domain (e.g., LINUXMUSTER.LAN)
setup.set('setup', 'realm', domainname.upper())
# Samba domain: first part of domain in uppercase (e.g., LINUXMUSTER)
setup.set('setup', 'sambadomain', domainname.split('.')[0].upper())
# Base DN: LDAP distinguished name (e.g., DC=linuxmuster,DC=lan)
basedn = ''
for item in domainname.split('.'):
    basedn = basedn + 'DC=' + item + ','
setup.set('setup', 'basedn', basedn[:-1])

# Validate and process server name
# Accept either 'servername' or legacy 'hostname' parameter
msg = '* Servername '
printScript(msg, '', False, False, True)
servername = '_'
if 'servername' in setup['setup']:
    servername = setup.get('setup', 'servername')
elif 'hostname' in setup['setup']:
    servername = setup.get('setup', 'hostname')
if not isValidHostname(servername):
    printScript(' servername ' + servername + ' is not valid!',
                '', True, True, False, len(msg))
    sys.exit(1)
printScript(' ' + servername, '', True, True, False, len(msg))
setup.set('setup', 'servername', servername)

# Derive NetBIOS name from server name (uppercase version)
setup.set('setup', 'netbiosname', servername.upper())

# Validate server IP address
msg = '* Server-IP '
printScript(msg, '', False, False, True)
try:
    serverip = setup.get('setup', 'serverip')
    if not isValidHostIpv4(serverip):
        printScript(' ' + serverip + ' is not valid!',
                    '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + serverip, '', True, True, False, len(msg))
except Exception as error:
    printScript(f' not set: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Validate bitmask and create IP network object
msg = '* Bitmask '
printScript(msg, '', False, False, True)
try:
    bitmask = setup.get('setup', 'bitmask')
    ip = IP(serverip + '/' + bitmask, make_net=True)
except Exception as error:
    printScript(f' {bitmask} is not valid: {error}',
                '', True, True, False, len(msg))
    sys.exit(1)
printScript(' ' + bitmask, '', True, True, False, len(msg))

# Derive network parameters from bitmask
# Netmask in dotted notation (e.g., 255.255.0.0)
setup.set('setup', 'netmask', ip.netmask().strNormal(0))
# Network address (e.g., 10.0.0.0)
setup.set('setup', 'network', IP(ip).strNormal(0))
# Broadcast address (e.g., 10.0.255.255)
setup.set('setup', 'broadcast', ip.broadcast().strNormal(0))

# Calculate DHCP range
# If not provided or invalid, calculate based on network size
msg = '* DHCP range '
printScript(msg, '', False, False, True)
try:
    dhcprange = setup.get('setup', 'dhcprange')
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    if not isValidHostIpv4(dhcprange1) and not isValidHostIpv4(dhcprange2):
        dhcprange = ''
except Exception as error:
    dhcprange = ''
if dhcprange == '':
    try:
        octets = splitIpOctets(serverip)
        # Large networks (/16 or smaller): use wider range in 3rd octet
        if int(bitmask) <= 16:
            dhcprange1 = buildIp([octets[0], octets[1], *DHCP_RANGE_START_LARGE_NET.split('.')])
            dhcprange2 = buildIp([octets[0], octets[1], *DHCP_RANGE_END_LARGE_NET.split('.')])
        # Smaller networks: use range in 4th octet
        else:
            prefix = getNetworkPrefix(serverip)
            dhcprange1 = buildIp([*prefix.split('.'), str(DHCP_RANGE_START_SUFFIX)])
            dhcprange2 = buildIp([*prefix.split('.'), str(DHCP_RANGE_END_SUFFIX)])
        dhcprange = dhcprange1 + ' ' + dhcprange2
        setup.set('setup', 'dhcprange', dhcprange)
    except Exception as error:
        printScript(f' failed to set: {error}', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + dhcprange1 + '-' + dhcprange2,
            '', True, True, False, len(msg))

# Validate firewall IP address
msg = '* Firewall IP '
printScript(msg, '', False, False, True)
try:
    firewallip = setup.get('setup', 'firewallip')
    if not isValidHostIpv4(firewallip):
        printScript(' ' + firewallip + ' is not valid!',
                    '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + firewallip, '', True, True, False, len(msg))
except Exception as error:
    printScript(f' not set: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Create global binduser password for LDAP authentication
# This password is used by various services (dhcpd, etc.) to bind to LDAP
msg = 'Creating global binduser secret '
printScript(msg, '', False, False, True)
try:
    binduserpw = randomPassword(16)
    with open(environment.BINDUSERSECRET, 'w') as secret:
        secret.write(binduserpw)
    runWithLog(['chmod', '440', environment.BINDUSERSECRET], logfile, checkErrors=False)
    runWithLog(['chgrp', 'dhcpd', environment.BINDUSERSECRET], logfile, checkErrors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Write final setup.ini file with all computed and validated values
msg = 'Writing setup ini file '
printScript(msg, '', False, False, True)
try:
    with open(environment.SETUPINI, 'w') as outfile:
        setup.write(outfile)
    runWithLog(['chmod', '600', environment.SETUPINI], logfile, checkErrors=False)
    # Create temporary setup.ini for transferring to additional VMs
    # Include binduser password but clear admin password for security
    setup.set('setup', 'binduserpw', binduserpw)
    setup.set('setup', 'adminpw', '')
    with open('/tmp/setup.ini', 'w') as outfile:
        setup.write(outfile)
    runWithLog(['chmod', '600', '/tmp/setup.ini'], logfile, checkErrors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Clean up obsolete temporary configuration files
for item in [environment.CUSTOMINI, environment.PREPINI]:
    if os.path.isfile(item):
        os.unlink(item)
