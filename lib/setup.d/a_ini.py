#!/usr/bin/python3
#
# process setup ini files
# thomas@linuxmuster.net
# 20180129
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
from functions import readTextfile
from functions import writeTextfile
from functions import subProc
from IPy import IP

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read ini files
setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
for i in [constants.DEFAULTSINI, constants.SETUPINI, constants.PREPINI, constants.CUSTOMINI]:
    # skip non existant file
    if not os.path.isfile(i):
        continue
    # reading setup values
    msg = 'Reading ' + i + ' '
    printScript(msg, '', False, False, True)
    try:
        setup.read(i)
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

# samba realm
msg = '* realm '
printScript(msg, '', False, False, True)
try:
    realm = setup.get('setup', 'realm')
except:
    realm = ''
if realm == '' or realm == None:
    realm = domainname.upper()
    try:
        setup.set('setup', 'realm', realm)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + realm, '', True, True, False, len(msg))

# sambadomain
msg = '* sambadomain '
printScript(msg, '', False, False, True)
try:
    sambadomain = setup.get('setup', 'sambadomain')
except:
    sambadomain = ''
if sambadomain == '' or sambadomain == None:
    sambadomain = domainname.split('.')[0].upper()
    try:
        setup.set('setup', 'sambadomain', sambadomain)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + sambadomain, '', True, True, False, len(msg))

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
msg = '* netbiosname '
printScript(msg, '', False, False, True)
try:
    netbiosname = setup.get('setup', 'netbiosname')
except:
    netbiosname = ''
if not isValidHostname(netbiosname):
    netbiosname = servername.upper()
    try:
        setup.set('setup', 'netbiosname', netbiosname)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + netbiosname, '', True, True, False, len(msg))

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

# netmask
msg = '* Bitmask '
printScript(msg, '', False, False, True)
try:
    bitmask = setup.get('setup', 'bitmask')
    n = IP(serverip + '/' + bitmask, make_net=True)
except:
    printScript(' ' + bitmask + ' is not valid!', '', True, True, False, len(msg))
    sys.exit(1)
printScript(' ' + bitmask, '', True, True, False, len(msg))

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
        dhcprange1 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '100'
        dhcprange2 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '200'
        dhcprange = dhcprange1 + ' ' + dhcprange2
        setup.set('setup', 'dhcprange', dhcprange)
    except:
        printScript(' failed to set!', '', True, True, False, len(msg))
        sys.exit(1)
printScript(' ' + dhcprange1 + '-' + dhcprange2, '', True, True, False, len(msg))

# firewallip
msg = '* Firewall IP '
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

# dockerip
msg = '* Dockerhost IP '
printScript(msg, '', False, False, True)
try:
    dockerip = setup.get('setup', 'dockerip')
    printScript(' ' + dockerip, '', True, True, False, len(msg))
except:
    dockerip = ''
    printScript(' not set', '', True, True, False, len(msg))

# mailip
msg = '* Mailserver IP '
printScript(msg, '', False, False, True)
try:
    mailip = setup.get('setup', 'mailip')
    printScript(' ' + mailip, '', True, True, False, len(msg))
except:
    mailip = ''
    printScript(' not set', '', True, True, False, len(msg))

# dnsforwarder
msg = '* DNS forwarder '
printScript(msg, '', False, False, True)
try:
    dnsforwarder = setup.get('setup', 'dnsforwarder')
except:
    dnsforwarder = ''
if not isValidHostIpv4(dnsforwarder):
    try:
        dnsforwarder = firewallip
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
    iface_list, iface = getDefaultIface()
if iface == '':
    printScript(' not set!', '', True, True, False, len(msg))
try:
    setup.set('setup', 'iface', iface)
except:
    printScript(' failed to set!', '', True, True, False, len(msg))
    sys.exit(1)
printScript(' ' + iface, '', True, True, False, len(msg))

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

# delete temporary ini files
if os.path.isfile(constants.CUSTOMINI):
    os.unlink(constants.CUSTOMINI)
if os.path.isfile(constants.PREPINI):
    os.unlink(constants.PREPINI)
