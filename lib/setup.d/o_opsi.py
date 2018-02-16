#!/usr/bin/python3
#
# opsiserver setup
# thomas@linuxmuster.net
# 20180215
#

import configparser
import constants
import os
import paramiko
import re
import stat
import sys
from functions import isValidHostIpv4
from functions import printScript
from functions import readTextfile
from functions import subProc
from functions import writeTextfile

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# files
opsicert =  constants.SSLDIR + '/opsi.cert.pem'
opsikey =  constants.SSLDIR + '/opsi.key.pem'
setuptmp = '/tmp/settings'
setuphelper = '/tmp/setup.sh'

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    # get setup various values
    serverip = setup.get('setup', 'serverip')
    opsiip = setup.get('setup', 'opsiip')
    adminpw = setup.get('setup', 'adminpw')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# main functions
def main():
    # helper files for opsiserver setup
    msg = '* Creating helper files '
    printScript(msg, '', False, False, True)
    try:
        # create settings file for opsi setup
        rc, content = readTextfile(setupini)
        content = content.replace('[setup]\n', '')
        content = content.replace('\n\n', '\n')
        content = content.replace(' = ', '="')
        content = content.replace('\n', '"\n')
        content = content + '\nadmin="Administrator"'
        rc = writeTextfile(setuptmp, content, 'w')
        # create setup helper script
        content = '#!/bin/bash\nmkdir -p ' + constants.SSLDIR
        content = content + '\nmv /tmp/*.pem ' + constants.SSLDIR
        content = content + '\nchmod 640 ' + constants.SSLDIR + '/*.key.pem'
        content = content + '\nln -sf ' + constants.SSLDIR + '/cacert.pem /etc/ssl/certs/cacert.pem'
        content = content + '\nmv /tmp/settings ' + constants.OPSILMNDIR
        content = content + '\n' + constants.OPSISETUP + ' --first | tee /tmp/linuxmuster-opsi.log\n'
        rc = writeTextfile(setuphelper, content, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    # open ssh connection
    msg = '* Establishing ssh connection to opsiserver '
    printScript(msg, '', False, False, True)
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(opsiip, 22, 'root', adminpw)
    try:
        ftp = ssh.open_sftp()
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    # uploading data & certs
    msg = '* Uploading files to opsiserver '
    printScript(msg, '', False, False, True)
    for item in [setuptmp, setuphelper, opsicert, opsikey]:
        if not ftp.put(item, '/tmp/' + os.path.basename(item)):
            printScript(' ' + os.path.basename(item) + ' failed!', '', True, True, False, len(msg))
            sys.exit(1)
    ftp.chmod(setuphelper, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
    ftp.close()
    ssh.close()
    printScript(' Success!', '', True, True, False, len(msg))
    # start opsiserver setup per ssh
    msg = '* Starting opsiserver setup '
    printScript(msg, '', False, False, True)
    try:
        sshcmd = 'ssh -oNumberOfPasswordPrompts=0 -oStrictHostKeyChecking=no -p 22 ' + opsiip
        setupcmd = sshcmd + ' ' + setuphelper
        subProc(setupcmd, logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    # close ssh connection
    os.unlink(setuptmp)

# mailserver setup only if ip is set
if isValidHostIpv4(opsiip):
    main()
