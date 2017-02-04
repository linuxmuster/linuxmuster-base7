#!/usr/bin/python3
#
# b_dialog.py
# thomas@linuxmuster.net
# 20170128
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
from IPy import IP

print ('### ' + os.path.basename(__file__))

# get network interfaces
iface_list, iface_default = detectedInterfaces()

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)

# begin dialog
d = Dialog(dialog="dialog")
d.set_background_title("linuxmuster.net 7")
button_names = {d.OK:     "OK",
                d.CANCEL: "Cancel"}

"""
# schoolname
rc, schoolname = d.inputbox('Bitte geben Sie den Schulnamen ein:', init=i.get('setup', 'schoolname'))
if rc == 'cancel':
    sys.exit(1)

print('Schulname: ' + schoolname)
i.set('setup', 'schoolname', schoolname )

# location
rc, location = d.inputbox('Bitte geben Sie den Schulort ein:', init=i.get('setup', 'location'))
if rc == 'cancel':
    sys.exit(1)

print('Schulort: ' + location)
i.set('setup', 'location', location )

# country
rc, country = d.inputbox('Bitte geben Sie das Land in Kurzform ein:', init=i.get('setup', 'country'))
if rc == 'cancel':
    sys.exit(1)
country = country.upper()[0:2]
print('Land: ' + country)
i.set('setup', 'country', country )

# state
rc, state = d.inputbox('Bitte geben Sie das Bundesland ein:', init=i.get('setup', 'state'))
if rc == 'cancel':
    sys.exit(1)

print('Bundesland: ' + state)
i.set('setup', 'state', state )
"""

# servername
while True:
    rc, servername = d.inputbox('Bitte geben Sie den Servernamen ein:', init=i.get('setup', 'servername'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostname(servername):
        break

print('Servername: ' + servername)
i.set('setup', 'servername', servername)

# domainname
while True:
    rc, domainname = d.inputbox('Bitte geben Sie den Internet-Domänennamen ein:', init=i.get('setup', 'domainname'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidDomainname(domainname):
        break

print('Domainname: ' + domainname)
i.set('setup', 'domainname', domainname)
basedn = 'dc=' + domainname.replace('.', ',dc=')
i.set('setup', 'basedn', basedn)

# sambadomain
while True:
    rc, sambadomain = d.inputbox('Bitte geben Sie den Samba-Domänennamen ein:', init=i.get('setup', 'sambadomain'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidDomainname(sambadomain):
        break

print('sambadomain: ' + sambadomain)
i.set('setup', 'sambadomain', sambadomain.upper())

# serverip
while True:
    rc, serveripnet = d.inputbox('Bitte geben Sie die IP-Adresse des Servers mit Netzmaske ein:', init=i.get('setup', 'serverip') + '/' + i.get('setup', 'netmask'))
    if rc == 'cancel':
        sys.exit(1)
    try:
        n = IP(serveripnet, make_net=True)
        break
    except ValueError:
        print("Ungültige Eingabe!")

serverip = serveripnet.split('/')[0]
network = IP(n).strNormal(0)
netmask = IP(n).strNormal(2).split('/')[1]
broadcast = IP(n).strNormal(3).split('-')[1]

print('Serverip: ' + serverip)
print('Network: ' + network)
print('Netmask: ' + netmask)
print('Broadcast: ' + broadcast)
i.set('setup', 'serverip', serverip)
i.set('setup', 'network', network)
i.set('setup', 'netmask', netmask)
i.set('setup', 'broadcast', broadcast)

# gatewayip
gatewayip = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.254'
while True:
    rc, gatewayip = d.inputbox('Bitte geben Sie die IP-Adresse des Gateways ein:', init=gatewayip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(gatewayip):
        break

print('Gatewayip: ' + gatewayip)
i.set('setup', 'gatewayip', gatewayip)

# firewallip
while True:
    rc, firewallip = d.inputbox('Bitte geben Sie die IP-Adresse der Firewall ein:', init=gatewayip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(firewallip):
        break

print('Firewallip: ' + firewallip)
i.set('setup', 'firewallip', firewallip)

# smtprelay
while True:
    rc, smtprelay = d.inputbox('Bitte geben Sie die Adresse des SMTP-Relays ein (optional):', init=i.get('setup', 'smtprelay'))
    if rc == 'cancel':
        sys.exit(1)
    if ('smtprelay' not in locals() or smtprelay == ''):
        smtprelay = ''
        break
    if (isValidHostIpv4(smtprelay) or isValidDomainname(smtprelay) or isValidHostIpv4(smtprelay)):
        break

print('Smtprelay: ' + smtprelay)
i.set('setup', 'smtprelay', smtprelay)

# network interface to use
if iface_default == '':
    # create items for dialog
    choices = []
    for item in iface_list:
        choices.append((item, ''))
    rc, iface = d.menu('Wählen Sie das zu verwendende Netzwerkinterface aus:', choices=choices)
else:
    iface = iface_default

print('Iface: ' + iface)
i.set('setup', 'iface', iface)

# global admin password
while True:
    rc, adminpw = d.passwordbox('Bitte geben Sie das Administratorpasswort ein:')
    if rc == 'cancel':
        sys.exit(1)
    if isValidPassword(adminpw):
        break
while True:
    rc, adminpw_repeated = d.passwordbox('Bitte geben Sie das Administratorpasswort nochmal ein:')
    if rc == 'cancel':
        sys.exit(1)
    if adminpw == adminpw_repeated:
        break

print('Adminpw: ' + adminpw)
i.set('setup', 'adminpw', adminpw)

# firewall root password
while True:
    rc, firewallpw = d.passwordbox('Bitte geben Sie das Passwort ein, dass Sie für den Benutzer root auf der Firewall vergeben haben:')
    if rc == 'cancel':
        sys.exit(1)
    if firewallpw == '':
        continue
    else:
        rc, firewallpw_repeated = d.passwordbox('Bitte geben Sie das Firewallpasswort nochmal ein:')
        if rc == 'cancel':
                sys.exit(1)
    if firewallpw == firewallpw_repeated:
        break

print('Firewallpw: ' + firewallpw)
i.set('setup', 'firewallpw', firewallpw)

# write INIFILE
with open(constants.SETUPINI, 'w') as INIFILE:
    i.write(INIFILE)
