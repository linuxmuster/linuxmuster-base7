#!/usr/bin/python3
#
# general setup
# thomas@linuxmuster.net
# 20170814
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

import gettext
t = gettext.translation('linuxmuster-base')
_ = t.gettext


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
    serverip = setup.get('setup', 'serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get network interfaces
iface_list, iface_default = detectedInterfaces()

# begin dialog
title = 'General Setup'
dialog = Dialog(dialog="dialog")
dialog.set_background_title('linuxmuster.net 7: ' + title)
button_names = {dialog.OK:     _("OK"),
                dialog.CANCEL: _("Cancel")}

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
ititle = title + ': Servername'
while True:
    rc, servername = dialog.inputbox(_('Enter the hostname of the main server:'), title=ititle, height=16, width=64, init=setup.get('setup', 'servername'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostname(servername):
        break

print('Server hostname: ' + servername)
setup.set('setup', 'servername', servername)

# domainname
ititle = title + ': Domainname'
while True:
    rc, domainname = dialog.inputbox(_('Note that the first part of the domain name is used automatically as samba domain. Enter the internet domain name:'), title=ititle, height=16, width=64, init=setup.get('setup', 'domainname'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidDomainname(domainname):
        break

print('Domain name: ' + domainname)
setup.set('setup', 'domainname', domainname)
basedn = 'DC=' + domainname.replace('.', ',DC=')
print('BaseDN: ' + basedn)
setup.set('setup', 'basedn', basedn)
realm = domainname.upper()
print('REALM: ' + realm)
setup.set('setup', 'realm', realm)

# sambadomain
sambadomain = domainname.split('.')[0].upper()
print('Samba domain: ' + sambadomain)
setup.set('setup', 'sambadomain', sambadomain)

# dhcprange
ititle = title + ': DHCP Range'
dhcprange1 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '100'
dhcprange2 = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '200'
dhcprange = dhcprange1 + ' ' + dhcprange2
while True:
    rc, dhcprange = dialog.inputbox(_('Enter the two ip addresses for the free dhcp range (space separated):'), title=ititle, height=16, width=64, init=dhcprange)
    if rc == 'cancel':
        sys.exit(1)
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    if isValidHostIpv4(dhcprange1) and isValidHostIpv4(dhcprange2):
        break
print('DHCP range: ' + dhcprange)
setup.set('setup', 'dhcprange', dhcprange)

# firewallip
ititle = title + ': Firewall IP'
try:
    firewallip=setup.get('setup', 'firewallip')
except:
    firewallip = gatewayip
while True:
    rc, firewallip = dialog.inputbox(_('Enter the ip address of the firewall:'), title=ititle, height=16, width=64, init=firewallip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(firewallip):
        break
print('Firewall ip: ' + firewallip)
setup.set('setup', 'firewallip', firewallip)

# opsi
ititle = title + ': Opsi IP'
try:
    opsiip=setup.get('setup', 'opsiip')
except:
    opsiip = ''
while True:
    rc, opsiip = dialog.inputbox(_('Enter the ip address of the opsi server (optional):'), title=ititle, height=16, width=64, init=opsiip)
    if rc == 'cancel':
        sys.exit(1)
    if opsiip == '' or isValidHostIpv4(opsiip):
        break
print('Opsi ip: ' + opsiip)
setup.set('setup', 'opsiip', opsiip)

# mail
ititle = title + ': Mail IP'
try:
    mailip=setup.get('setup', 'mailip')
except:
    mailip = ''
while True:
    rc, mailip = dialog.inputbox(_('Enter the ip address of the mail server (optional):'), title=ititle, height=16, width=64, init=mailip)
    if rc == 'cancel':
        sys.exit(1)
    if mailip == '' or isValidHostIpv4(mailip):
        break
print('Mail ip: ' + mailip)
setup.set('setup', 'mailip', mailip)

# smtprelay
ititle = title + ': SMTP Relay IP'
while True:
    rc, smtprelay = dialog.inputbox(_('Enter the ip address of the smtp relay server (optional):'), title=ititle, height=16, width=64, init=setup.get('setup', 'smtprelay'))
    if rc == 'cancel':
        sys.exit(1)
    if ('smtprelay' not in locals() or smtprelay == ''):
        smtprelay = ''
        break
    if (isValidHostIpv4(smtprelay) or isValidDomainname(smtprelay) or isValidHostIpv4(smtprelay)):
        break

print('SMTP relay ip: ' + smtprelay)
setup.set('setup', 'smtprelay', smtprelay)

# global admin password
ititle = title + ': Password of global-admin'
while True:
    rc, adminpw = dialog.passwordbox(_('Enter the password to use for the global-admin (Note: Input will be unvisible!):'), title=ititle)
    if rc == 'cancel':
        sys.exit(1)
    if isValidPassword(adminpw):
        break
while True:
    rc, adminpw_repeated = dialog.passwordbox(_('Re-enter the global-admin password:'), title=ititle)
    if rc == 'cancel':
        sys.exit(1)
    if adminpw == adminpw_repeated:
        break

print('global-admin password: ' + adminpw)
setup.set('setup', 'adminpw', adminpw)

# firewall root password
ititle = title + ': ' + _('Firewall root password')
skipfw = setup.getboolean('setup', 'skipfw')
if skipfw == False:
    while True:
        rc, firewallpw = dialog.passwordbox(_('Enter the firewall root password:'), title=ititle)
        if rc == 'cancel':
            sys.exit(1)
        if firewallpw == '':
            continue
        else:
            rc, firewallpw_repeated = dialog.passwordbox(_('Re-enter the firewall root password:'), title=ititle)
            if rc == 'cancel':
                sys.exit(1)
        if firewallpw == firewallpw_repeated:
            break
    print('Firewall root password: ' + firewallpw)
    setup.set('setup', 'firewallpw', firewallpw)

# opsi root password
ititle = title + ': ' + _('Opsi root password')
if isValidHostIpv4(opsiip):
    while True:
        rc, opsipw = dialog.passwordbox(_('Enter the opsi root password:'), title=ititle)
        if rc == 'cancel':
            sys.exit(1)
        if opsipw == '':
            continue
        else:
            rc, opsipw_repeated = dialog.passwordbox(_('Re-enter the opsi root password:'), title=ititle)
            if rc == 'cancel':
                sys.exit(1)
        if opsipw == opsipw_repeated:
            break
    print('Opsi root password: ' + opsipw)
    setup.set('setup', 'opsipw', opsipw)

# mail root password
ititle = title + ': ' + _('Mail root password')
if (isValidHostIpv4(mailip) and mailip != serverip):
    while True:
        rc, mailpw = dialog.passwordbox(_('Enter the mail root password:'), title=ititle)
        if rc == 'cancel':
            sys.exit(1)
        if opsipw == '':
            continue
        else:
            rc, mailpw_repeated = dialog.passwordbox(_('Re-enter the mail root password:'), title=ititle)
            if rc == 'cancel':
                sys.exit(1)
        if mailpw == mailpw_repeated:
            break
    print('Mail root password: ' + mailpw)
    setup.set('setup', 'mailpw', mailpw)

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
