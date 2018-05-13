#!/usr/bin/python3
#
# firewall setup
# thomas@linuxmuster.net
# 20180513
#

import bcrypt
import configparser
import constants
import datetime
import os
import paramiko
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, NavigableString
from functions import isValidHostIpv4
from functions import printScript
from functions import readTextfile
from functions import writeTextfile
from shutil import copyfile

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
    # check if firewall shall be skipped
    skipfw = setup.getboolean('setup', 'skipfw')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# main routine
def main():
    # get setup various values
    serverip = setup.get('setup', 'serverip')
    bitmask = setup.get('setup', 'bitmask')
    firewallip = setup.get('setup', 'firewallip')
    servername = setup.get('setup', 'servername')
    domainname = setup.get('setup', 'domainname')
    basedn = setup.get('setup', 'basedn')
    opsiip = setup.get('setup', 'opsiip')
    dockerip = setup.get('setup', 'dockerip')
    network = setup.get('setup', 'network')
    adminpw = setup.get('setup', 'adminpw')
    # get timezone
    rc, timezone = readTextfile('/etc/timezone')
    timezone = timezone.replace('\n', '')
    # get binduser password
    rc, binduserpw = readTextfile(constants.BINDUSERSECRET)

    # firewall config files
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    fwconf = '/conf/config.xml'
    fwconftmp = constants.CACHEDIR + '/opnsense.xml'
    fwconfbak = constants.CACHEDIR + '/opnsense-' + now + '.xml'
    fwconftpl = constants.FWOSCONFTPL

    # dummy ip addresses
    if not isValidHostIpv4(opsiip):
        opsiip = network.split('.')[0] + '.' + network.split('.')[1] + '.' + network.split('.')[2] + '.2'
    if not isValidHostIpv4(dockerip):
        dockerip = network.split('.')[0] + '.' + network.split('.')[1] + '.' + network.split('.')[2] + '.3'

    # establish ssh connection to firewall
    msg = '* Establishing ssh connection '
    printScript(msg, '', False, False, True)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(firewallip, port=22, username='root', password=constants.ROOTPW)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # get current config
    msg = '* Downloading current firewall configuration '
    printScript(msg, '', False, False, True)
    try:
        ftp = ssh.open_sftp()
        ftp.get(fwconf, fwconftmp)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # get current config
    msg = '* Backing up '
    printScript(msg, '', False, False, True)
    try:
        shutil.copy(fwconftmp, fwconfbak)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # get root password hash
    msg = '* Reading config '
    printScript(msg, '', False, False, True)
    try:
        rc, content = readTextfile(fwconftmp)
        # save wan interface configuration
        soup = BeautifulSoup(content, 'lxml')
        wanconfig = str(soup.findAll('wan')[0])
        # save opt1 configuration if present
        try:
            opt1config = str(soup.findAll('opt1')[0])
        except:
            opt1config = ''
        # get already configured lan interfaces
        config = ET.fromstring(content)
        lanif = ''
        for lan in config.iter('lan'):
            if lan.find('if'):
                lanif = lan.find('if').text
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # get base64 encoded certs
    msg = '* Reading certificates & ssh key '
    printScript(msg, '', False, False, True)
    try:
        rc, cacertb64 = readTextfile(constants.CACERTB64)
        rc, fwcertb64 = readTextfile(constants.SSLDIR + '/firewall.cert.pem.b64')
        rc, fwkeyb64 = readTextfile(constants.SSLDIR + '/firewall.key.pem.b64')
        rc, authorizedkey = readTextfile(constants.SSHPUBKEYB64)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # create new firewall configuration
    msg = '* Creating xml configuration file '
    printScript(msg, '', False, False, True)
    try:
        # create password hash for new firewall password
        hashedpw = bcrypt.hashpw(str.encode(adminpw), bcrypt.gensalt(10))
        fwrootpw = hashedpw.decode()
        # read template
        rc, content = readTextfile(fwconftpl)
        # replace placeholders with values
        content = content.replace('@@servername@@', servername)
        content = content.replace('@@domainname@@', domainname)
        content = content.replace('@@basedn@@', basedn)
        content = content.replace('@@wanconfig@@', wanconfig)
        content = content.replace('@@lanif@@', lanif)
        content = content.replace('@@opt1config@@', opt1config)
        content = content.replace('@@serverip@@', serverip)
        content = content.replace('@@firewallip@@', firewallip)
        content = content.replace('@@network@@', network)
        content = content.replace('@@bitmask@@', bitmask)
        content = content.replace('@@opsiip@@', opsiip)
        content = content.replace('@@dockerip@@', dockerip)
        content = content.replace('@@fwrootpw@@', fwrootpw)
        content = content.replace('@@authorizedkey@@', authorizedkey)
        content = content.replace('@@binduserpw@@', binduserpw)
        content = content.replace('@@timezone@@', timezone)
        content = content.replace('@@cacertb64@@', cacertb64)
        content = content.replace('@@fwcertb64@@', fwcertb64)
        content = content.replace('@@fwkeyb64@@', fwkeyb64)
        # write new configfile
        rc = writeTextfile(fwconftmp, content, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # upload new configfile
    msg = '* Uploading configuration file '
    printScript(msg, '', False, False, True)
    try:
        ftp.put(fwconftmp, fwconf)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # reboot firewall
    msg = '* Rebooting firewall '
    printScript(msg, '', False, False, True)
    try:
        stdin, stdout, stderr = ssh.exec_command('/sbin/reboot')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # close connections
    ftp.close()
    ssh.close()

    # remove temporary files
    os.unlink(fwconftmp)

# quit if firewall setup shall be skipped
if skipfw:
    msg = 'Skipping firewall setup as requested'
    printScript(msg, '', True, False, False)
else:
    main()
