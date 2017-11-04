#!/usr/bin/python3
#
# network setup
# thomas@linuxmuster.net
# 20170816
#

import constants
import os
import sys
import configparser

from dialog import Dialog
from functions import getDefaultIface
from functions import isValidHostIpv4
from functions import printScript
from functions import subProc
from IPy import IP

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    iface_default = setup.get('setup', 'iface')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get network interfaces
iface_list, iface_default = getDefaultIface()

# begin dialog
title = 'Network Setup'
dialog = Dialog(dialog="dialog")
dialog.set_background_title('linuxmuster.net 7: ' + title)
button_names = {dialog.OK:     "OK",
                dialog.CANCEL: "Cancel"}

# network interface to use
ititle = title + ': Interface'
if iface_default == '' or iface_default == None:
    # create items for dialog
    choices = []
    for item in iface_list:
        choices.append((item, ''))
    rc, iface = dialog.menu('Select the network interface to use:', choices=choices, title=ititle)
else:
    iface = iface_default

print('Iface: ' + iface)
setup.set('setup', 'iface', iface)

# serverip
ititle = title + ': Server IP'
while True:
    rc, serveripnet = dialog.inputbox('Enter the server ip address with appended bitmask or netmask (e.g.  10.0.0.1/16 or 10.0.0.1/255.255.0.0):', title=ititle, height=16, width=64, init=setup.get('setup', 'serverip') + '/' + setup.get('setup', 'bitmask'))
    if rc == 'cancel':
        sys.exit(1)
    try:
        n = IP(serveripnet, make_net=True)
        break
    except ValueError:
        print("Invalid entry!")

serverip = serveripnet.split('/')[0]
network = IP(n).strNormal(0)
bitmask = IP(n).strNormal(1).split('/')[1]
netmask = IP(n).strNormal(2).split('/')[1]
broadcast = IP(n).strNormal(3).split('-')[1]

print('Server-IP: ' + serverip)
print('Network: ' + network)
print('Bitmask: ' + bitmask)
print('Netmask: ' + netmask)
print('Broadcast: ' + broadcast)
setup.set('setup', 'serverip', serverip)
setup.set('setup', 'bitmask', bitmask)
setup.set('setup', 'network', network)
setup.set('setup', 'netmask', netmask)
setup.set('setup', 'broadcast', broadcast)

# gatewayip
ititle = title + ': Gateway IP'
try:
    gatewayip=setup.get('setup', 'gatewayip')
except:
    gatewayip = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.254'
while True:
    rc, gatewayip = dialog.inputbox('Enter the ip address of the gateway:', title=ititle, height=16, width=64, init=gatewayip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(gatewayip):
        break
print('Gateway ip: ' + gatewayip)
setup.set('setup', 'gatewayip', gatewayip)

# dns forwarder
ititle = title + ': DNS IP'
try:
    dnsforwarder=setup.get('setup', 'dnsforwarder')
except:
    dnsforwarder = gatewayip
if not isValidHostIpv4(dnsforwarder):
    dnsforwarder = gatewayip
while True:
    rc, dnsforwarder = dialog.inputbox('Enter the ip address of the dns forwarder:', title=ititle, height=16, width=64, init=dnsforwarder)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(dnsforwarder):
        break
print('DNS forwarder: ' + dnsforwarder)
setup.set('setup', 'dnsforwarder', dnsforwarder)

# write INIFILE
msg = 'Writing input to setup ini file '
printScript(msg, '', False, False, True)
try:
    with open(constants.SETUPINI, 'w') as INIFILE:
        setup.write(INIFILE)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
