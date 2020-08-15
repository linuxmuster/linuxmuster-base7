#!/usr/bin/python3
#
# mailserver setup
# thomas@linuxmuster.net
# 20200415
#

import configparser
import constants
import os
import sys
from functions import isValidHostIpv4
from functions import printScript
from functions import putSftp
from functions import sambaTool
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# files
cacert = constants.CACERT
mailcert = constants.SSLDIR + '/mail.cert.pem'
mailkey = constants.SSLDIR + '/mail.key.pem'
setuptmp = '/tmp/setup.ini'
imagename = 'tvial/docker-mailserver:stable'

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.RawConfigParser(delimiters=('='), inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    # get setup various values
    mailip = setup.get('setup', 'mailip')
    serverip = setup.get('setup', 'serverip')
    domainname = setup.get('setup', 'domainname')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)


# main functions
def main():
    # open ssh connection
    if mailip != serverip:
        # start mailserver setup per ssh
        printScript('Remote mailserver setup')
        sshcmd = 'ssh -q -oStrictHostKeyChecking=accept-new ' + mailip + ' '
        try:
            msg = '* Uploading certificates '
            printScript(msg, '', False, False, True)
            # create remote ssl cert dir
            subProc(sshcmd + 'mkdir -p ' + constants.SSLDIR, logfile)
            # upload certs
            for item in [cacert, mailcert, mailkey]:
                putSftp(mailip, item, item)
            # link cacert
            subProc(sshcmd + 'ln -sf ' + cacert + ' /etc/ssl/certs', logfile)
            printScript(' Success!', '', True, True, False, len(msg))

            msg = '* Uploading setup data '
            printScript(msg, '', False, False, True)
            # create remote dir for setup.ini
            subProc(sshcmd + 'mkdir -p ' + constants.VARDIR, logfile)
            # upload setup.ini
            putSftp(mailip, setuptmp, setupini)
            printScript(' Success!', '', True, True, False, len(msg))

            msg = '* Installing linuxmuster-mail package '
            printScript(msg, '', False, False, True)
            # install linuxmuster-mail pkg
            subProc(sshcmd + 'apt update', logfile)
            subProc(sshcmd + 'apt -y install linuxmuster-mail', logfile)
            # key permissions
            subProc(sshcmd + 'chmod 640 ' + mailkey, logfile)
            subProc(sshcmd + 'chgrp docker ' + mailkey, logfile)
            printScript(' Success!', '', True, True, False, len(msg))

            msg = '* Pulling mailserver image '
            printScript(msg, '', False, False, True)
            # pull image
            subProc(sshcmd + 'docker pull ' + imagename, logfile)
            printScript(' Success!', '', True, True, False, len(msg))

            msg = '* Setting up mailserver container '
            printScript(msg, '', False, False, True)
            # invoke setup script
            subProc(sshcmd + '/usr/sbin/linuxmuster-mail-setup -f -c ' + setupini, logfile)
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            msg = 'Remote mailserver setup '
            printScript(msg, '', False, False, True)
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)
    # local mailserver setup
    else:
        msg = 'Local mailserver setup '
        printScript(msg, '', False, False, True)
        try:
            subProc('apt update && apt -y install linuxmuster-mail', logfile)
            subProc('/usr/sbin/linuxmuster-mail-setup -f -c ' + setuptmp, logfile)
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

    # add mail dns entry
    msg = '* Creating dns entry '
    printScript(msg, '', False, False, True)
    try:
        sambaTool('dns add localhost ' + domainname + ' mail A ' + mailip, logfile)
        sambaTool('dns add localhost ' + domainname + ' mail MX "' + mailip + ' 10"', logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)


# mailserver setup only if ip is set
if isValidHostIpv4(mailip):
    main()
