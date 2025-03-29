#!/usr/bin/python3
#
# setup ssh host keys
# thomas@linuxmuster.net
# 20240219
#

import configparser
import environment
import glob
import os
import re
import subprocess
import sys

from functions import backupCfg, checkSocket, isValidHostIpv4, modIni
from functions import mySetupLogfile, printScript, replaceInFile
from functions import setupComment, subProc, writeTextfile

logfile = mySetupLogfile(__file__)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = environment.SETUPINI
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

# stop ssh service
msg = 'Stopping ssh service '
printScript(msg, '', False, False, True)
try:
    subProc('service ssh stop', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# delete old ssh keys
for file in glob.glob('/etc/ssh/*key*'):
    os.unlink(file)
for file in glob.glob(sshdir + '/id*'):
    os.unlink(file)

# create ssh keys
msg = "Creating ssh host keys "
printScript(msg, '', False, False, True)
try:
    subProc('ssh-keygen -A', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
printScript('Creating ssh root keys:')
for a in crypto_list:
    msg = '* ' + a + ' key '
    printScript(msg, '', False, False, True)
    try:
        subProc('ssh-keygen -t ' + a + ' -f '
                + rootkey_prefix + a + ' -N ""', logfile)
        if a == 'rsa':
            keyfile = rootkey_prefix + a + '.pub'
            b64sshkey = subprocess.check_output(['base64', keyfile]).decode('utf-8').replace('\n', '')
            writeTextfile(environment.SSHPUBKEYB64, b64sshkey, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# start ssh service
msg = 'starting ssh service '
printScript(msg, '', False, False, True)
try:
    subProc('service ssh start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
