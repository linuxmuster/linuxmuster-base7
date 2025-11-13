#!/usr/bin/python3
#
# setup ssh host keys
# thomas@linuxmuster.net
# 20251112
#

import configparser
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import glob
import os
import re
import subprocess
import datetime
import sys

from linuxmuster_base7.functions import backupCfg, checkSocket, getSetupValue, isValidHostIpv4, modIni, \
    mySetupLogfile, printScript, replaceInFile, setupComment, writeTextfile

logfile = mySetupLogfile(__file__)

# Helper function to run command with logging
def run_with_log(cmd_list, cmd_desc, logfile):
    result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
    if logfile and (result.stdout or result.stderr):
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####')
            log.write('#### ' + cmd_desc + ' ####')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
    return result


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
crypto_list = ['dsa', 'ecdsa', 'ed25519', 'rsa']
sshdir = '/root/.ssh'
rootkey_prefix = sshdir + '/id_'
known_hosts = sshdir + '/known_hosts'

# stop ssh service
msg = 'Stopping ssh service '
printScript(msg, '', False, False, True)
try:
    run_with_log(['service', 'ssh', 'stop'], 'service ssh stop', logfile)
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
    run_with_log(['ssh-keygen', '-A'], 'ssh-keygen -A', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
printScript('Creating ssh root keys:')
for a in crypto_list:
    msg = '* ' + a + ' key '
    printScript(msg, '', False, False, True)
    try:
        keyfile = rootkey_prefix + a + '_key'
        run_with_log(['ssh-keygen', '-t', a, '-f', keyfile, '-N', ''], 'ssh-keygen -t ' + a + ' -f ...', logfile)
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
    run_with_log(['service', 'ssh', 'start'], 'service ssh start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
