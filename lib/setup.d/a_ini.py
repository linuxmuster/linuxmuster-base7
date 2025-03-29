#!/usr/bin/python3
#
# process setup ini files
# thomas@linuxmuster.net
# 20220105
#

import configparser
import environment
import os
import sys

from functions import isValidHostname, isValidDomainname, isValidHostIpv4
from functions import mySetupLogfile, printScript, randomPassword, subProc
from IPy import IP

logfile = mySetupLogfile(__file__)

# read ini files
setup = configparser.RawConfigParser(
    delimiters=('='), inline_comment_prefixes=('#', ';'))
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
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
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
except:
    printScript(' not set!', '', True, True, False, len(msg))
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
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)

# netmask
msg = '* Bitmask '
printScript(msg, '', False, False, True)
try:
    bitmask = setup.get('setup', 'bitmask')
    ip = IP(serverip + '/' + bitmask, make_net=True)
except:
    printScript(' ' + bitmask + ' is not valid!',
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
except:
    dhcprange = ''
if dhcprange == '':
    try:
        if int(bitmask) <= 16:
            dhcprange1 = serverip.split(
                '.')[0] + '.' + serverip.split('.')[1] + '.255.1'
            dhcprange2 = serverip.split(
                '.')[0] + '.' + serverip.split('.')[1] + '.255.254'
        else:
            dhcprange1 = serverip.split('.')[
                                        0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '201'
            dhcprange2 = serverip.split('.')[
                                        0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '250'
        dhcprange = dhcprange1 + ' ' + dhcprange2
        setup.set('setup', 'dhcprange', dhcprange)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
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
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)

# create global binduser password
msg = 'Creating global binduser secret '
printScript(msg, '', False, False, True)
try:
    binduserpw = randomPassword(16)
    with open(environment.BINDUSERSECRET, 'w') as secret:
        secret.write(binduserpw)
    subProc('chmod 440 ' + environment.BINDUSERSECRET, logfile)
    subProc('chgrp dhcpd ' + environment.BINDUSERSECRET, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# write setup.ini finally
msg = 'Writing setup ini file '
printScript(msg, '', False, False, True)
try:
    with open(environment.SETUPINI, 'w') as outfile:
        setup.write(outfile)
    subProc('chmod 600 ' + environment.SETUPINI, logfile)
    # temporary setup.ini for transfering it later to additional vms
    setup.set('setup', 'binduserpw', binduserpw)
    setup.set('setup', 'adminpw', '')
    with open('/tmp/setup.ini', 'w') as outfile:
        setup.write(outfile)
    subProc('chmod 600 /tmp/setup.ini', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# delete obsolete ini files
for item in [environment.CUSTOMINI, environment.PREPINI]:
    if os.path.isfile(item):
        os.unlink(item)
