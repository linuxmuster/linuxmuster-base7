#!/usr/bin/python3
#
# mailserver setup
# thomas@linuxmuster.net
# 20180214
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
from functions import sambaTool
from functions import subProc
from functions import writeTextfile

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# files
mailcert =  constants.SSLDIR + '/mail.cert.pem'
mailkey =  constants.SSLDIR + '/mail.key.pem'
setuptmp = '/tmp/setup.ini'
setuphelper = '/tmp/setup.sh'

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    # get setup various values
    mailip = setup.get('setup', 'mailip')
    serverip = setup.get('setup', 'serverip')
    adminpw = setup.get('setup', 'adminpw')
    # get binduser password
    rc, binduserpw = readTextfile(constants.BINDUSERSECRET)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# main functions
def main():
    # helper files for mailserver setup
    msg = '* Creating helper files '
    printScript(msg, '', False, False, True)
    try:
        # add binduser password to setup.ini
        rc, content = readTextfile(setupini)
        content = content + 'binduserpw = ' + binduserpw
        rc = writeTextfile(setuptmp, content, 'w')
        # create setup helper script
        content = '#!/bin/bash\nmkdir -p ' + constants.SSLDIR
        content = content + '\nmv /tmp/*.pem ' + constants.SSLDIR
        content = content + '\nchmod 640 ' + constants.SSLDIR + '/*.key.pem'
        content = content + '\nln -sf ' + constants.SSLDIR + '/cacert.pem /etc/ssl/certs/cacert.pem'
        content = content + '\napt-get update\napt-get -y install linuxmuster-mail'
        content = content + '\nlinuxmuster-mail.py -c ' + setuptmp
        content = content + '\nsystemctl start linuxmuster-mail.service'
        rc = writeTextfile(setuphelper, content, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    # open ssh connection
    if mailip != serverip:
        msg = '* Establishing ssh connection to mailserver '
        printScript(msg, '', False, False, True)
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(mailip, 22, 'root', adminpw)
        try:
            ftp = ssh.open_sftp()
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)
        # uploading data & certs
        msg = '* Uploading files to mailserver '
        printScript(msg, '', False, False, True)
        for item in [setuptmp, setuphelper, mailcert, mailkey]:
            if not ftp.put(item, '/tmp/' + os.path.basename(item)):
                printScript(' ' + os.path.basename(item) + ' failed!', '', True, True, False, len(msg))
                sys.exit(1)
        ftp.chmod(setuphelper, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
        printScript(' Success!', '', True, True, False, len(msg))
        # start mailserver setup per ssh
        msg = '* Starting mailserver setup '
        printScript(msg, '', False, False, True)
        try:
            stdin, stdout, stderr = ssh.exec_command(setuphelper)
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)
        # close ssh connection
        ftp.close()
        ssh.close()
    # local mailserver setup
    else:
        msg = '* Starting mailserver setup '
        printScript(msg, '', False, False, True)
        try:
            subProc('apt update && apt -y install linuxmuster-mail', logfile)
            subProc('linuxmuster-mail.py -s -c ' + setuptmp, logfile)
            subProc('systemctl start linuxmuster-mail.service', logfile)
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)
    os.unlink(setuptmp)
    # add mail dns entry
    msg = '* Creating dns entry '
    printScript(msg, '', False, False, True)
    try:
        sambaTool('dns add localhost linuxmuster.lan mail A ' + mailip)
        sambaTool('dns add localhost linuxmuster.lan mail MX "' + mailip + ' 10"')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# mailserver setup only if ip is set
if isValidHostIpv4(mailip):
    main()
