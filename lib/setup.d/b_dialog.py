#!/usr/bin/python3
#
# b_dialog.py
# thomas@linuxmuster.net
# 20170212
#

import constants
import os
import sys
import configparser

from dialog import Dialog
from functions import detectedInterfaces
from functions import isValidHostname
from functions import isValidDomainname
from functions import isValidHostIpv4
from functions import isValidPassword
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
    setup = configparser.ConfigParser()
    setup.read(setupini)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get network interfaces
iface_list, iface_default = detectedInterfaces()

# begin dialog
dialog = Dialog(dialog="dialog")
dialog.set_background_title("linuxmuster.net 7")
button_names = {dialog.OK:     "OK",
                dialog.CANCEL: "Cancel"}

"""
# schoolname
rc, schoolname = dialog.inputbox('Bitte geben Sie den Schulnamen ein:', height=16, width=64, init=setup.get('setup', 'schoolname'))
if rc == 'cancel':
    sys.exit(1)

print('Schulname: ' + schoolname)
setup.set('setup', 'schoolname', schoolname )

# location
rc, location = dialog.inputbox('Bitte geben Sie den Schulort ein:', height=16, width=64, init=setup.get('setup', 'location'))
if rc == 'cancel':
    sys.exit(1)

print('Schulort: ' + location)
setup.set('setup', 'location', location )

# country
rc, country = dialog.inputbox('Bitte geben Sie das Land in Kurzform ein:', height=16, width=64, init=setup.get('setup', 'country'))
if rc == 'cancel':
    sys.exit(1)
country = country.upper()[0:2]
print('Land: ' + country)
setup.set('setup', 'country', country )

# state
rc, state = dialog.inputbox('Bitte geben Sie das Bundesland ein:', height=16, width=64, init=setup.get('setup', 'state'))
if rc == 'cancel':
    sys.exit(1)

print('Bundesland: ' + state)
setup.set('setup', 'state', state )
"""

# servername
while True:
    rc, servername = dialog.inputbox('Enter the hostname of the main server:', height=16, width=64, init=setup.get('setup', 'servername'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostname(servername):
        break

print('Server hostname: ' + servername)
setup.set('setup', 'servername', servername)

# domainname
while True:
    rc, domainname = dialog.inputbox('Enter the internet domain name:', height=16, width=64, init=setup.get('setup', 'domainname'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidDomainname(domainname):
        break

print('Domain name: ' + domainname)
setup.set('setup', 'domainname', domainname)
basedn = 'DC=' + domainname.replace('.', ',DC=')
setup.set('setup', 'basedn', basedn)

# sambadomain
while True:
    rc, sambadomain = dialog.inputbox('Enter the samba domain name:', height=16, width=64, init=setup.get('setup', 'sambadomain'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidDomainname(sambadomain):
        break

print('Samba domain: ' + sambadomain)
setup.set('setup', 'sambadomain', sambadomain.upper())

# serverip
while True:
    rc, serveripnet = dialog.inputbox('Enter the server ip address with appended netmask (e.g. 10.0.0.1/255.255.0.0):', height=16, width=64, init=setup.get('setup', 'serverip') + '/' + setup.get('setup', 'netmask'))
    if rc == 'cancel':
        sys.exit(1)
    try:
        n = IP(serveripnet, make_net=True)
        break
    except ValueError:
        print("Invalid entry!")

serverip = serveripnet.split('/')[0]
network = IP(n).strNormal(0)
netmask = IP(n).strNormal(2).split('/')[1]
broadcast = IP(n).strNormal(3).split('-')[1]

print('Server-IP: ' + serverip)
print('Network: ' + network)
print('Netmask: ' + netmask)
print('Broadcast: ' + broadcast)
setup.set('setup', 'serverip', serverip)
setup.set('setup', 'network', network)
setup.set('setup', 'netmask', netmask)
setup.set('setup', 'broadcast', broadcast)

# dhcprange
dhcprange1 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '100'
dhcprange2 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '200'
dhcprange = dhcprange1 + ' ' + dhcprange2
while True:
    rc, dhcprange = dialog.inputbox('Enter the two ip addresses for the free dhcp range (space separated):', height=16, width=64, init=dhcprange)
    if rc == 'cancel':
        sys.exit(1)
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    if isValidHostIpv4(dhcprange1) and isValidHostIpv4(dhcprange2):
        break
print('DHCP range: ' + dhcprange)
setup.set('setup', 'dhcprange', dhcprange)

# firewallip
try:
    firewallip=setup.get('setup', 'firewallip')
except:
    firewallip = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.254'
while True:
    rc, firewallip = dialog.inputbox('Enter the ip address of the firewall:', height=16, width=64, init=firewallip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(firewallip):
        break
print('Firewall ip: ' + firewallip)
setup.set('setup', 'firewallip', firewallip)

# gatewayip
try:
    gatewayip=setup.get('setup', 'gatewayip')
except:
    gatewayip = firewallip
while True:
    rc, gatewayip = dialog.inputbox('Enter the ip address of the gateway:', height=16, width=64, init=gatewayip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(gatewayip):
        break
print('Gateway ip: ' + gatewayip)
setup.set('setup', 'gatewayip', gatewayip)

# dns forwarder
try:
    dnsforwarder=setup.get('setup', 'dnsforwarder')
except:
    dnsforwarder = gatewayip
if not isValidHostIpv4(dnsforwarder):
    dnsforwarder = gatewayip
while True:
    rc, dnsforwarder = dialog.inputbox('Enter the ip address of the dns forwarder:', height=16, width=64, init=dnsforwarder)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(dnsforwarder):
        break
print('DNS forwarder: ' + dnsforwarder)
setup.set('setup', 'dnsforwarder', dnsforwarder)

# opsi
try:
    opsiip=setup.get('setup', 'opsiip')
except:
    opsiip = ''
while True:
    rc, opsiip = dialog.inputbox('Enter the ip address of the opsi server (optional):', height=16, width=64, init=opsiip)
    if rc == 'cancel':
        sys.exit(1)
    if opsiip == '' or isValidHostIpv4(opsiip):
        break
print('Opsi ip: ' + opsiip)
setup.set('setup', 'opsiip', opsiip)

# smtprelay
while True:
    rc, smtprelay = dialog.inputbox('Enter the ip address of the smtp relay server (optional):', height=16, width=64, init=setup.get('setup', 'smtprelay'))
    if rc == 'cancel':
        sys.exit(1)
    if ('smtprelay' not in locals() or smtprelay == ''):
        smtprelay = ''
        break
    if (isValidHostIpv4(smtprelay) or isValidDomainname(smtprelay) or isValidHostIpv4(smtprelay)):
        break

print('SMTP relay ip: ' + smtprelay)
setup.set('setup', 'smtprelay', smtprelay)

# network interface to use
if iface_default == '':
    # create items for dialog
    choices = []
    for item in iface_list:
        choices.append((item, ''))
    rc, iface = dialog.menu('Select the network interface to use:', choices=choices)
else:
    iface = iface_default

print('Iface: ' + iface)
setup.set('setup', 'iface', iface)

# global admin password
while True:
    rc, adminpw = dialog.passwordbox('Enter the password to use for the global-admin (Note: Input will be unvisible!):')
    if rc == 'cancel':
        sys.exit(1)
    if isValidPassword(adminpw):
        break
while True:
    rc, adminpw_repeated = dialog.passwordbox('Re-enter the global-admin password:')
    if rc == 'cancel':
        sys.exit(1)
    if adminpw == adminpw_repeated:
        break

print('Admin password: ' + adminpw)
setup.set('setup', 'adminpw', adminpw)

# firewall root password
while True:
    rc, firewallpw = dialog.passwordbox('Enter the firewall root password:')
    if rc == 'cancel':
        sys.exit(1)
    if firewallpw == '':
        continue
    else:
        rc, firewallpw_repeated = dialog.passwordbox('Re-enter the firewall root password:')
        if rc == 'cancel':
            sys.exit(1)
    if firewallpw == firewallpw_repeated:
        break

print('Firewall root password: ' + firewallpw)
setup.set('setup', 'firewallpw', firewallpw)

# opsi root password
if isValidHostIpv4(opsiip):
    while True:
        rc, opsipw = dialog.passwordbox('Enter the opsi root password:')
        if rc == 'cancel':
            sys.exit(1)
        if opsipw == '':
            continue
        else:
            rc, opsipw_repeated = dialog.passwordbox('Re-enter the opsi root password:')
            if rc == 'cancel':
                sys.exit(1)
        if opsipw == opsipw_repeated:
            break

print('Opsi root password: ' + opsipw)
setup.set('setup', 'opsipw', opsipw)

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
