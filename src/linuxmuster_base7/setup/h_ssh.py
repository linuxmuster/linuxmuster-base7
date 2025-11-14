#!/usr/bin/python3
#
# setup ssh host keys
# thomas@linuxmuster.net
# 20251112
#

import configparser
import datetime
import glob
import os
import re
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import backupCfg, checkSocket, getSetupValue, isValidHostIpv4, modIni, \
    mySetupLogfile, printScript, replaceInFile, setupComment, writeTextfile
from linuxmuster_base7.setup.helpers import runWithLog, CRYPTO_TYPES

logfile = mySetupLogfile(__file__)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    # get ip addresses
    serverip = getSetupValue('serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# variables
hostkey_prefix = '/etc/ssh/ssh_host_'
sshdir = '/root/.ssh'
rootkey_prefix = sshdir + '/id_'
known_hosts = sshdir + '/known_hosts'

# stop ssh service
msg = 'Stopping ssh service '
printScript(msg, '', False, False, True)
try:
    runWithLog(['service', 'ssh', 'stop'], logfile, checkErrors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
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
    runWithLog(['ssh-keygen', '-A'], logfile, checkErrors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
printScript('Creating ssh root keys:')
for a in CRYPTO_TYPES:
    msg = '* ' + a + ' key '
    printScript(msg, '', False, False, True)
    try:
        keyfile = rootkey_prefix + a + '_key'
        runWithLog(['ssh-keygen', '-t', a, '-f', keyfile, '-N', ''], logfile, checkErrors=False)
        if a == 'rsa':
            pubkey = keyfile + '.pub'
            b64sshkey = subprocess.check_output(['base64', pubkey]).decode('utf-8').replace('\n', '')
            writeTextfile(environment.SSHPUBKEYB64, b64sshkey, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)

# start ssh service
msg = 'starting ssh service '
printScript(msg, '', False, False, True)
try:
    runWithLog(['service', 'ssh', 'start'], logfile, checkErrors=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
