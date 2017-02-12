#!/usr/bin/python3
#
# a_ini.py
# thomas@linuxmuster.net
# 20170212
#

import configparser
import constants
import os
import sys
from functions import detectedInterfaces
from functions import printScript
from functions import isValidHostname
from functions import isValidDomainname
from functions import isValidHostIpv4
from functions import getDefaultIface
from functions import subProc
from IPy import IP

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# custom or default setup ini file
if os.path.isfile(constants.CUSTOMINI):
    setupini = constants.CUSTOMINI
    ini = 'custom'
else:
    setupini = constants.DEFAULTSINI
    ini = 'default'

# reading setup values
msg = 'Reading ' + ini + ' ini '
printScript(msg, '', False, False, True)
try:
    setup = configparser.ConfigParser()
    setup.read(setupini)
    if ini == 'custom':
        subProc('rm ' + constants.CUSTOMINI, logfile)
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
        printScript(' ' + domainname + ' is not valid!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + domainname, '', True, True, False, len(msg))
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)

# samba REALM
msg = '* REALM '
printScript(msg, '', False, False, True)
try:
    REALM = setup.get('setup', 'REALM')
except:
    REALM = ''
if REALM == '' or REALM == None:
    REALM = domainname.upper()
    try:
        setup.set('setup', 'REALM', REALM)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + REALM, '', True, True, False, len(msg))

# basedn
msg = '* BaseDN '
printScript(msg, '', False, False, True)
try:
    basedn = setup.get('setup', 'basedn')
except:
    basedn = ''
if basedn == '' or basedn == None:
    try:
        for i in domainname.split('.'):
            basedn = basedn + 'DC=' + i + ','
        setup.set('setup', 'basedn', basedn[:-1])
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + basedn, '', True, True, False, len(msg))

# servername
msg = '* Servername '
printScript(msg, '', False, False, True)
try:
    servername = setup.get('setup', 'servername')
    if not isValidHostname(servername):
        printScript(' ' + servername + ' is not valid!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + servername, '', True, True, False, len(msg))
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)

# samba netbios name
msg = '* NETBIOSNAME '
printScript(msg, '', False, False, True)
try:
    NETBIOSNAME = setup.get('setup', 'NETBIOSNAME')
except:
    NETBIOSNAME = ''
if not isValidHostname(NETBIOSNAME):
    NETBIOSNAME = servername.upper()
    try:
        setup.set('setup', 'NETBIOSNAME', NETBIOSNAME)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + NETBIOSNAME, '', True, True, False, len(msg))

# serverip
msg = '* Server-IP '
printScript(msg, '', False, False, True)
try:
    serverip = setup.get('setup', 'serverip')
    if not isValidHostIpv4(serverip):
        printScript(' ' + serverip + ' is not valid!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + serverip, '', True, True, False, len(msg))
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)

# netmask
msg = '* Netmask '
printScript(msg, '', False, False, True)
try:
    netmask = setup.get('setup', 'netmask')
    n = IP(serverip + '/' + netmask, make_net=True)
except:
    printScript(' ' + netmask + ' is not valid!', '', True, True, False, len(msg))
    sys.exit(1)
printScript(' ' + netmask, '', True, True, False, len(msg))

# network address
msg = '* Network '
printScript(msg, '', False, False, True)
try:
    network = IP(n).strNormal(0)
    setup.set('setup', 'network', network)
    printScript(' ' + network, '', True, True, False, len(msg))
except:
    printScript(' failed to set!', '', True, True, False, len(msg))
    sys.exit(1)

# broadcast address
msg = '* Broadcast '
printScript(msg, '', False, False, True)
try:
    broadcast = IP(n).strNormal(3).split('-')[1]
    setup.set('setup', 'broadcast', broadcast)
    printScript(' ' + broadcast, '', True, True, False, len(msg))
except:
    printScript(' failed to set!', '', True, True, False, len(msg))
    sys.exit(1)

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
        dhcprange1 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + '100'
        dhcprange2 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + '200'
        dhcprange = dhcprange1 + ' ' + dhcprange2
        setup.set('setup', 'dhcprange', dhcprange)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + dhcprange1 + '-' + dhcprange2, '', True, True, False, len(msg))

# firewallip
msg = '* Firewall-IP '
printScript(msg, '', False, False, True)
try:
    firewallip = setup.get('setup', 'firewallip')
except:
    firewallip = ''
if not isValidHostIpv4(firewallip):
    try:
        firewallip = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.254'
        setup.set('setup', 'firewallip', firewallip)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + firewallip, '', True, True, False, len(msg))

# gatewayip
msg = '* Gatewayip-IP '
printScript(msg, '', False, False, True)
try:
    gatewayip = setup.get('setup', 'gatewayip')
except:
    gatewayip = ''
if not isValidHostIpv4(gatewayip):
    try:
        gatewayip = firewallip
        setup.set('setup', 'gatewayip', gatewayip)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + gatewayip, '', True, True, False, len(msg))

# dnsforwarder
msg = '* DNS forwarder '
printScript(msg, '', False, False, True)
try:
    dnsforwarder = setup.get('setup', 'dnsforwarder')
except:
    dnsforwarder = ''
if not isValidHostIpv4(dnsforwarder):
    try:
        dnsforwarder = gatewayip
        setup.set('setup', 'dnsforwarder', dnsforwarder)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + dnsforwarder, '', True, True, False, len(msg))

# Network interface
msg = '* Default network interface '
printScript(msg, '', False, False, True)
try:
    iface = setup.get('setup', 'iface')
except:
    iface = ''
if iface == '' or iface == None:
    iface = getDefaultIface()
if iface == None:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)
try:
    setup.set('setup', 'iface', iface)
except:
    printScript(' failed to set!', '', True, True, False, len(msg))
    sys.exit(1)
printScript(' ' + iface, '', True, True, False, len(msg))

# add missing setup options with default values
if ini == 'custom':
    msg = 'Adding missing setup values '
    printScript(msg, '', False, False, True)
    try:
        defaults = configparser.ConfigParser()
        defaults.read(constants.DEFAULTSINI)
        for option in defaults.options('setup'):
            if not option in setup.options('setup'):
                value = defaults.get('setup', option)
                setup.set('setup', option, value)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# write inifile finally
msg = 'Writing setup ini file '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    with open(setupini, 'w') as outfile:
        setup.write(outfile)
    subProc('chmod 600 ' + setupini, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
