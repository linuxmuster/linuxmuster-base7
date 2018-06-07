#!/usr/bin/python3
#
# process setup ini files
# thomas@linuxmuster.net
# 20180604
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
for item in [constants.DEFAULTSINI, constants.SETUPINI, constants.CUSTOMINI, constants.PREPINI]:
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
        printScript(' ' + domainname + ' is not valid!', '', True, True, False, len(msg))
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
try:
    servername = setup.get('setup', 'hostname')
    if not isValidHostname(servername):
        printScript(' ' + servername + ' is not valid!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + servername, '', True, True, False, len(msg))
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)
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
        printScript(' ' + serverip + ' is not valid!', '', True, True, False, len(msg))
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
    printScript(' ' + bitmask + ' is not valid!', '', True, True, False, len(msg))
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
            dhcprange1 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.255.1'
            dhcprange2 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.255.254'
        else:
            dhcprange1 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '201'
            dhcprange2 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '250'
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
    if not isValidHostIpv4(firewallip):
        printScript(' ' + firewallip + ' is not valid!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' ' + firewallip, '', True, True, False, len(msg))
except:
    printScript(' not set!', '', True, True, False, len(msg))
    sys.exit(1)

# dockerip
msg = '* Dockerhost IP '
printScript(msg, '', False, False, True)
try:
    dockerip = setup.get('setup', 'dockerip')
    if dockerip == '':
        printScript(' not set!', '', True, True, False, len(msg))
    else:
        if isValidHostIpv4(dockerip):
            printScript(' ' + dockerip, '', True, True, False, len(msg))
        else:
            printScript(' ' + dockerip + ' is not valid!', '', True, True, False, len(msg))
            sys.exit(1)
except:
    setup.set('setup', 'dockerip', '')
    printScript(' not set!', '', True, True, False, len(msg))

# mailip
msg = '* Mailserver IP '
printScript(msg, '', False, False, True)
try:
    mailip = setup.get('setup', 'mailip')
    if mailip == '':
        printScript(' not set!', '', True, True, False, len(msg))
    else:
        if isValidHostIpv4(mailip):
            printScript(' ' + mailip, '', True, True, False, len(msg))
        else:
            printScript(' ' + mailip + ' is not valid!', '', True, True, False, len(msg))
            sys.exit(1)
except:
    setup.set('setup', 'mailip', '')
    printScript(' not set!', '', True, True, False, len(msg))

# Network interface
# msg = '* Default network interface '
# printScript(msg, '', False, False, True)
# try:
#     iface = setup.get('setup', 'iface')
# except:
#     iface = ''
# if iface == '' or iface == None:
#     iface_list, iface = getDefaultIface()
# if iface == '':
#     printScript(' not set!', '', True, True, False, len(msg))
# try:
#     setup.set('setup', 'iface', iface)
# except:
#     printScript(' failed to set!', '', True, True, False, len(msg))
#     sys.exit(1)
# printScript(' ' + iface, '', True, True, False, len(msg))

# write inifile finally
msg = 'Writing setup ini file '
printScript(msg, '', False, False, True)
try:
    with open(constants.SETUPINI, 'w') as outfile:
        setup.write(outfile)
    subProc('chmod 600 ' + constants.SETUPINI, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# delete temporary ini files
for item in [constants.CUSTOMINI, constants.PREPINI]:
    if os.path.isfile(item):
        os.unlink(item)
