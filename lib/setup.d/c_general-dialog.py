#!/usr/bin/python3
#
# general setup
# thomas@linuxmuster.net
# 20180215
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
ititle = title + ': Servername'
while True:
    rc, servername = dialog.inputbox('Enter the hostname of the main server:', title=ititle, height=16, width=64, init=setup.get('setup', 'servername'))
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostname(servername):
        break

print('Server hostname: ' + servername)
setup.set('setup', 'servername', servername)

# domainname
ititle = title + ': Domainname'
while True:
    rc, domainname = dialog.inputbox('Note that the first part of the domain name is used automatically as samba domain. Enter the internet domain name:', title=ititle, height=16, width=64, init=setup.get('setup', 'domainname'))
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
    rc, dhcprange = dialog.inputbox('Enter the two ip addresses for the free dhcp range (space separated):', title=ititle, height=16, width=64, init=dhcprange)
    if rc == 'cancel':
        sys.exit(1)
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    if isValidHostIpv4(dhcprange1) and isValidHostIpv4(dhcprange2):
        break
print('DHCP range: ' + dhcprange)
setup.set('setup', 'dhcprange', dhcprange)

# opsi
ititle = title + ': Opsi-IP'
try:
    opsiip=setup.get('setup', 'opsiip')
except:
    opsiip = ''
while True:
    rc, opsiip = dialog.inputbox('Enter the ip address of the opsi server (optional):', title=ititle, height=16, width=64, init=opsiip)
    if rc == 'cancel':
        sys.exit(1)
    if opsiip == '' or isValidHostIpv4(opsiip):
        break
print('Opsi ip: ' + opsiip)
setup.set('setup', 'opsiip', opsiip)

# dockerip
ititle = title + ': Dockerhost-IP'
try:
    dockerip=setup.get('setup', 'dockerip')
except:
    dockerip = ''
while True:
    rc, dockerip = dialog.inputbox('Enter the ip address of the docker host (optional):', title=ititle, height=16, width=64, init=dockerip)
    if rc == 'cancel':
        sys.exit(1)
    if isValidHostIpv4(dockerip) or dockerip == '':
        break
print('Docker host ip: ' + dockerip)
setup.set('setup', 'dockerip', dockerip)

# mail
nostatus = False
servermail = False
dockermail = False
ititle = title + ': Mailserver IP'
try:
    mailip=setup.get('setup', 'mailip')
    if isValidHostIpv4(mailip) and mailip == serverip:
        servermail = True
    elif isValidHostIpv4(mailip) and mailip == dockerip:
        dockermail = True
except:
    mailip = ''
    nostatus = True
while True:
    if dockerip != '':
        rc, mailip = dialog.radiolist('Enter the ip address of the mail server (optional):', title=ititle, height=16, width=64, list_height=3, choices=[('', 'no mailserver', nostatus), (serverip, 'use server ip', servermail), (dockerip, 'use docker ip', dockermail)])
    else:
        rc, mailip = dialog.radiolist('Enter the ip address of the mail server (optional):', title=ititle, height=16, width=64, list_height=3, choices=[('', 'no mailserver', nostatus), (serverip, 'use server ip', servermail)])
    #rc, mailip = dialog.inputbox('Enter the ip address of the mail server (optional):', title=ititle, height=16, width=64, init=mailip)
    if rc == 'cancel':
        sys.exit(1)
    if mailip == '' or isValidHostIpv4(mailip):
        break
print('Mail ip: ' + mailip)
setup.set('setup', 'mailip', mailip)

# smtp access data
if mailip != '':
    # smtp relay ip of fully qualified domain name
    ititle = title + ': SMTP Relay IP'
    try:
        smtprelay=setup.get('setup', 'smtprelay')
    except:
        smtprelay = ''
    while True:
        rc, smtprelay = dialog.inputbox('Enter the ip address or fqdn of the smtp relay (optional):', title=ititle, height=16, width=64, init=smtprelay)
        if rc == 'cancel':
            sys.exit(1)
        if (isValidHostIpv4(smtprelay) or isValidDomainname(smtprelay) or smtprelay == ''):
            break
    print('SMTP relay ip: ' + smtprelay)
    setup.set('setup', 'smtprelay', smtprelay)
    # ask only if smtprelay is set
    if smtprelay != '':
        # smtp user
        ititle = title + ': SMTP Username'
        try:
            smtpuser=setup.get('setup', 'smtpuser')
        except:
            smtpuser = ''
        while True:
            rc, smtpuser = dialog.inputbox('Enter the name of the smtp user:', title=ititle, height=16, width=64, init=smtpuser)
            if rc == 'cancel':
                sys.exit(1)
            if smtpuser != '':
                break
        print('SMTP Username: ' + smtpuser)
        setup.set('setup', 'smtpuser', smtpuser)
        # smtp password
        ititle = title + ': SMTP Password'
        try:
            smtppw=setup.get('setup', 'smtppw')
        except:
            smtppw = ''
        while True:
            rc, smtppw = dialog.inputbox('Enter the name of the smtp user:', title=ititle, height=16, width=64, init=smtppw)
            if rc == 'cancel':
                sys.exit(1)
            if smtppw != '':
                break
        print('SMTP Password: ' + smtppw)
        setup.set('setup', 'smtppw', smtppw)

# global admin password
ititle = title + ': Administrator password'
while True:
    rc, adminpw = dialog.passwordbox('Enter the Administrator password (Note: Input will be unvisible!):', title=ititle)
    if rc == 'cancel':
        sys.exit(1)
    if isValidPassword(adminpw):
        break
while True:
    rc, adminpw_repeated = dialog.passwordbox('Re-enter the Administrator password:', title=ititle)
    if rc == 'cancel':
        sys.exit(1)
    if adminpw == adminpw_repeated:
        break

print('Administrator password: ' + adminpw)
setup.set('setup', 'adminpw', adminpw)

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
