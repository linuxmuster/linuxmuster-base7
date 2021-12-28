#!/usr/bin/python3
#
# general setup
# thomas@linuxmuster.net
# 20211228
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
    setup = configparser.RawConfigParser(
        delimiters=('='), inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    serverip = setup.get('setup', 'serverip')
    servername = setup.get('setup', 'servername')
    domainname = setup.get('setup', 'domainname')
    dhcprange = setup.get('setup', 'dhcprange')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get network interfaces
# iface_list, iface_default = detectedInterfaces()

# begin dialog
title = 'linuxmuster.net 7.1: Setup for ' + \
    servername + '.' + domainname + '\n\n'
dialog = Dialog(dialog="dialog")
dialog.set_background_title(title)
button_names = {dialog.OK:     "OK",
                dialog.CANCEL: "Cancel"}


# servername
ititle = title + ': Servername'
while True:
    rc, servername = dialog.inputbox('Enter the hostname of the main server:',
                                     title=ititle, height=16, width=64, init=setup.get('setup', 'servername'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostname(servername):
        break

print('Server hostname: ' + servername)
setup.set('setup', 'servername', servername)
setup.set('setup', 'hostname', servername)
netbiosname = servername.upper()
print('Netbios name: ' + netbiosname)
setup.set('setup', 'netbiosname', netbiosname)


# domainname
ititle = title + ': Domainname'
while True:
    rc, domainname = dialog.inputbox(
        'Note that the first part of the domain name is used automatically as samba domain (maximal 15 characters using a-z and "-"). Use a prepending "linuxmuster" if your domain has more characters. Enter the internet domain name:', title=ititle, height=16, width=64, init=domainname)
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
sambadomain = realm.split('.')[0]
print('Sambadomain: ' + sambadomain)
setup.set('setup', 'sambadomain', sambadomain)


# dhcprange
ititle = title + ': DHCP Range'
dhcprange1 = dhcprange.split(' ')[0]
dhcprange2 = dhcprange.split(' ')[1]
if dhcprange1 == '':
    dhcprange1 = serverip.split('.')[
                            0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '100'
if dhcprange2 == '':
    dhcprange2 = serverip.split('.')[
                            0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.' + '200'
dhcprange = dhcprange1 + ' ' + dhcprange2
while True:
    rc, dhcprange = dialog.inputbox(
        'Enter the two ip addresses for the free dhcp range (space separated):', title=ititle, height=16, width=64, init=dhcprange)
    if rc == 'cancel':
        sys.exit(1)
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    if isValidHostIpv4(dhcprange1) and isValidHostIpv4(dhcprange2):
        break
print('DHCP range: ' + dhcprange)
setup.set('setup', 'dhcprange', dhcprange)


# global admin password
ititle = title + ': Administrator password'
adminpw = ''
adminpw_repeated = ''
while True:
    rc, adminpw = dialog.passwordbox(
        'Enter the Administrator password (Note: Input will be unvisible!). Minimal length is 7 characters. Use upper and lower and special characters or numbers (e.g. mUster!):', title=ititle, insecure=True)
    if rc == 'cancel':
        sys.exit(1)
    if isValidPassword(adminpw):
        while True:
            rc, adminpw_repeated = dialog.passwordbox(
                'Re-enter the Administrator password:', title=ititle, insecure=True)
            if rc == 'cancel':
                sys.exit(1)
            if isValidPassword(adminpw_repeated):
                break
    if adminpw == adminpw_repeated:
        break

# print('Administrator password: ' + adminpw)
setup.set('setup', 'adminpw', adminpw)


# write INIFILE
msg = 'Writing input to setup ini file '
printScript(msg, '', False, False, True)
try:
    with open(setupini, 'w') as INIFILE:
        setup.write(INIFILE)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)


# set root password
msg = 'Setting root password '
printScript(msg, '', False, False, True)
try:
    subProc('echo "root:' + adminpw + '" | chpasswd', logfile)
    if os.path.isdir('/home/linuxmuster'):
        subProc('echo "linuxmuster:' + adminpw + '" | chpasswd', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
