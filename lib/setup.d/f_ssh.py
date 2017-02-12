#!/usr/bin/python3
#
# f_ssh.py
# thomas@linuxmuster.net
# 20170212
#

import configparser
import constants
import os
import re
import sys

from functions import backupCfg
from functions import checkSocket
from functions import doSshLink
from functions import isValidHostIpv4
from functions import isValidPassword
from functions import enterPassword
from functions import printScript
from functions import setupComment
from functions import subProc
from functions import modIni

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
    # get firewall ip
    firewallip = setup.get('setup', 'firewallip')
    # get firewall root password
    firewallpw = setup.get('setup', 'firewallpw')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# test firewall and opsi passwords
msg = 'Checking firewall password '
printScript(msg, '', False, False, True)
try:
    nopw = False
    if not isValidPassword(firewallpw):
        nopw = True
        printScript(' needs input:', '', True, True, False, len(msg))
        firewallpw = enterPassword('firewall', False)
        setup.set('setup', 'firewallpw', firewallpw)
        modIni(setupini, 'setup', 'firewallpw', firewallpw)
    else:
        printScript(' Success!', '', True, True, False, len(msg))
except:
    if nopw == True:
        msg = 'Firewall password '
        printScript(msg, '', False, False, True)
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get opsi ip if set
opsiip = setup.get('setup', 'opsiip')
# get opsi server's root password
if isValidHostIpv4(opsiip):
    msg = 'Checking opsi server password '
    printScript(msg, '', False, False, True)
    try:
        opsipw = setup.get('setup', 'opsipw')
        nopw = False
        if not isValidPassword(opsipw):
            nopw = True
            printScript(' needs input:', '', True, True, False, len(msg))
            opsipw = enterPassword('opsi server', False)
            setup.set('setup', 'opsipw', opsipw)
            modIni(setupini, 'setup', 'opsipw', opsipw)
        else:
            printScript(' Success!', '', True, True, False, len(msg))
    except:
        if nopw == True:
            msg = 'Opsi server password '
            printScript(msg, '', False, False, True)
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# variables
hostkey_prefix = '/etc/ssh/ssh_host_'
crypto_list = ['dsa', 'ecdsa', 'ed25519', 'rsa']
sshdir = '/root/.ssh'
rootkey_prefix = sshdir + '/id_'
known_hosts = sshdir + '/known_hosts'

# delete old ssh keys
subProc('rm -f /etc/ssh/*key* ' + sshdir + '/id*', logfile)

# create ssh keys
printScript('Creating ssh keys:')
for a in crypto_list:
    msg = '* ' + a + ' host key '
    printScript(msg, '', False, False, True)
    try:
        subProc('ssh-keygen -t ' + a + ' -f ' + hostkey_prefix + a + '_key -N ""', logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    msg = '* ' + a + ' root key '
    printScript(msg, '', False, False, True)
    try:
        subProc('ssh-keygen -t ' + a + ' -f ' + rootkey_prefix + a + ' -N ""', logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# restart ssh service
msg = 'Restarting ssh service '
printScript(msg, '', False, False, True)
try:
    subProc('service ssh restart', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# remove known_hosts
if os.path.isfile(known_hosts):
    subProc('rm -f ' + known_hosts, logfile)

# iterate ips and ports
items = [(firewallip, 22, firewallpw), (firewallip, 222, firewallpw)]
success = []
if isValidHostIpv4(opsiip):
    items.append((opsiip, 22, opsipw))
for item in items:
    ip = item[0]
    port = item[1]
    secret = item[2]
    rc = doSshLink(ip, port, secret)
    if rc == True:
        success.append(ip)

# test success
rc = 0
for item in items:
    ip = item[0]
    if not ip in success:
        printScript('No SSH connection to host ' + ip + ' available!')
        rc = 1
if rc == 1:
    sys.exit(rc)
