#!/usr/bin/python3
#
# process setup ini files
# thomas@linuxmuster.net
# 20251114
#

import configparser
import datetime
import os
import subprocess
import sys

sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from IPy import IP
from linuxmuster_base7.functions import isValidHostname, isValidDomainname, isValidHostIpv4
from linuxmuster_base7.functions import mySetupLogfile, printScript, randomPassword
from linuxmuster_base7.setup.helpers import runWithLog, buildIp, getNetworkPrefix, splitIpOctets
from linuxmuster_base7.setup.helpers import DHCP_RANGE_START_SUFFIX, DHCP_RANGE_END_SUFFIX
from linuxmuster_base7.setup.helpers import DHCP_RANGE_START_LARGE_NET, DHCP_RANGE_END_LARGE_NET

logfile = mySetupLogfile(__file__)

# read ini files
setup = configparser.RawConfigParser(delimiters=('='))
for item in [environment.DEFAULTSINI, environment.PREPINI, environment.SETUPINI, environment.CUSTOMINI]:
    # skip non existant file
    if not os.path.isfile(item):
        continue
    # reading setup values
    msg = 'Reading ' + item + ' '
    printScript(msg, '', False, False, True)
    try:
        setup.read(item)
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)

# compute missing values
# from domainname
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

# derive values from domainname
# realm
setup.set('setup', 'realm', domainname.upper())
# sambadomain
setup.set('setup', 'sambadomain', domainname.split('.')[0].upper())
# basedn
basedn = ''
for item in domainname.split('.'):
    basedn = basedn + 'DC=' + item + ','
setup.set('setup', 'basedn', basedn[:-1])

# servername
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

# derive values from servername
# netbiosname
setup.set('setup', 'netbiosname', servername.upper())

# serverip
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

# netmask
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

# derive values from bitmask
# netmask
setup.set('setup', 'netmask', ip.netmask().strNormal(0))
# network address
setup.set('setup', 'network', IP(ip).strNormal(0))
# broadcast address
setup.set('setup', 'broadcast', ip.broadcast().strNormal(0))

# dhcprange
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
        if int(bitmask) <= 16:
            dhcprange1 = buildIp([octets[0], octets[1], *DHCP_RANGE_START_LARGE_NET.split('.')])
            dhcprange2 = buildIp([octets[0], octets[1], *DHCP_RANGE_END_LARGE_NET.split('.')])
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

# firewallip
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

# create global binduser password
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

# write setup.ini finally
msg = 'Writing setup ini file '
printScript(msg, '', False, False, True)
try:
    with open(environment.SETUPINI, 'w') as outfile:
        setup.write(outfile)
    runWithLog(['chmod', '600', environment.SETUPINI], logfile, checkErrors=False)
    # temporary setup.ini for transfering it later to additional vms
    setup.set('setup', 'binduserpw', binduserpw)
    setup.set('setup', 'adminpw', '')
    with open('/tmp/setup.ini', 'w') as outfile:
        setup.write(outfile)
    runWithLog(['chmod', '600', '/tmp/setup.ini'], logfile, checkErrors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# delete obsolete ini files
for item in [environment.CUSTOMINI, environment.PREPINI]:
    if os.path.isfile(item):
        os.unlink(item)
