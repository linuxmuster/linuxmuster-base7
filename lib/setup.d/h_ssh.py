#!/usr/bin/python3
#
# setup ssh host keys
# thomas@linuxmuster.net
# 20220105
#

import configparser
import constants
import os
import re
import sys

from functions import backupCfg, checkSocket, isValidHostIpv4, modIni
from functions import mySetupLogfile, printScript, replaceInFile
from functions import setupComment, subProc

logfile = mySetupLogfile(__file__)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.RawConfigParser(
        delimiters=('='), inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    # get ip addresses
    serverip = setup.get('setup', 'serverip')
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
        subProc('ssh-keygen -t ' + a + ' -f '
                + hostkey_prefix + a + '_key -N ""', logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    msg = '* ' + a + ' root key '
    printScript(msg, '', False, False, True)
    try:
        subProc('ssh-keygen -t ' + a + ' -f '
                + rootkey_prefix + a + ' -N ""', logfile)
        if a == 'rsa':
            subProc('base64 ' + constants.SSHPUBKEY
                    + ' > ' + constants.SSHPUBKEYB64, logfile)
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
