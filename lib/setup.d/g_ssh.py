#!/usr/bin/python3
#
# setup ssh keys and ssh links to additional servers
# thomas@linuxmuster.net
# 20180129
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
from functions import printScript
from functions import replaceInFile
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
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    # get firewall ip
    serverip = setup.get('setup', 'serverip')
    opsiip = setup.get('setup', 'opsiip')
    dockerip = setup.get('setup', 'dockerip')
    # check if firewall shall be skipped
    skipfw = setup.getboolean('setup', 'skipfw')
    if skipfw == False:
        # get firewall root password
        firewallpw = setup.get('setup', 'firewallpw')
    printScript(' Success!', '', True, True, False, len(msg))
except:
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
        if a == 'rsa':
            subProc('base64 ' + constants.SSHPUBKEY + ' > ' + constants.SSHPUBKEYB64, logfile)
            rc = replaceInFile(constants.SSHPUBKEYB64, '\n', '')
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

# install ssh link to additional servers
success = []
items = []
if isValidHostIpv4(opsiip):
    items.append((opsiip, 22))
if isValidHostIpv4(dockerip):
    items.append((dockerip, 22))
for item in items:
    ip = item[0]
    port = item[1]
    rc = doSshLink(ip, port, constants.ROOTPW)
    if rc == True:
        success.append(ip)

# test success
rc = 0
for item in items:
    ip = item[0]
    if not ip in success:
        printScript('No connection to host ' + ip + ' available!')
        rc = 1
if rc == 1:
    sys.exit(rc)
