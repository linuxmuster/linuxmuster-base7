#!/usr/bin/python3
#
# firewall setup
# thomas@linuxmuster.net
# 20181127
#

import bcrypt
import configparser
import constants
import datetime
import os
import re
import shutil
import sys
from bs4 import BeautifulSoup, NavigableString
from functions import getFwConfig
from functions import isValidHostIpv4
from functions import modIni
from functions import printScript
from functions import putFwConfig
from functions import randomPassword
from functions import readTextfile
from functions import sshExec
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
    fwconftmp = constants.FWCONFLOCAL
    fwconfbak = fwconftmp.replace('.xml', '-' + now + '.xml')
    fwconftpl = constants.FWOSCONFTPL

    # dummy ip addresses
    if not isValidHostIpv4(opsiip):
        opsiip = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.2'
    if not isValidHostIpv4(dockerip):
        dockerip = serverip.split('.')[0] + '.' + serverip.split('.')[1] + '.' + serverip.split('.')[2] + '.3'

    # get current config
    rc = getFwConfig(firewallip, constants.ROOTPW)
    if not rc:
        sys.exit(1)

    # backup config
    msg = '* Backing up '
    printScript(msg, '', False, False, True)
    try:
        shutil.copy(fwconftmp, fwconfbak)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # get root password hash
    msg = '* Reading current config '
    printScript(msg, '', False, False, True)
    try:
        rc, content = readTextfile(fwconftmp)
        soup = BeautifulSoup(content, 'lxml')
        # save interface configuration
        wanconfig = str(soup.findAll('wan')[0])
        lanconfig = str(soup.findAll('lan')[0])
        # save language information
        try:
            language = str(soup.findAll('language')[0])
        except:
            language = ''
        # save gateway configuration
        try:
            gwconfig = str(soup.findAll('gateways')[0])
        except:
            gwconfig = ''
        # save dnsserver configuration
        try:
            dnsconfig = str(soup.findAll('dnsserver')[0])
        except:
            dnsconfig = ''
        # save opt1 configuration if present
        try:
            opt1config = str(soup.findAll('opt1')[0])
        except:
            opt1config = ''
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

    # create list of first ten network ips for aliascontent (NoProxy group in firewall)
    aliascontent = ''
    netpre = network.split('.')[0] + '.' + network.split('.')[1] + '.' + network.split('.')[2] + '.'
    c = 0
    max = 10
    while c < max:
        c = c + 1
        aliasip = netpre + str(c)
        if aliascontent == '':
            aliascontent = aliasip
        else:
            aliascontent = aliascontent + '\n' + aliasip
    # add server ips if not already collected
    for aliasip in [serverip, opsiip, dockerip]:
        if not aliasip in aliascontent:
            aliascontent = aliascontent + '\n' + aliasip

    # create new firewall configuration
    msg = '* Creating xml configuration file '
    printScript(msg, '', False, False, True)
    try:
        # create password hash for new firewall password
        hashedpw = bcrypt.hashpw(str.encode(adminpw), bcrypt.gensalt(10))
        fwrootpw_hashed = hashedpw.decode()
        apikey = randomPassword(80)
        apisecret = randomPassword(80)
        hashedpw = bcrypt.hashpw(str.encode(apisecret), bcrypt.gensalt(10))
        apisecret_hashed = hashedpw.decode()
        # read template
        rc, content = readTextfile(fwconftpl)
        # replace placeholders with values
        content = content.replace('@@servername@@', servername)
        content = content.replace('@@domainname@@', domainname)
        content = content.replace('@@basedn@@', basedn)
        content = content.replace('@@wanconfig@@', wanconfig)
        content = content.replace('@@dnsconfig@@', dnsconfig)
        content = content.replace('@@gwconfig@@', gwconfig)
        content = content.replace('@@lanconfig@@', lanconfig)
        content = content.replace('@@opt1config@@', opt1config)
        content = content.replace('@@serverip@@', serverip)
        content = content.replace('@@firewallip@@', firewallip)
        content = content.replace('@@network@@', network)
        content = content.replace('@@bitmask@@', bitmask)
        content = content.replace('@@aliascontent@@', aliascontent)
        content = content.replace('@@fwrootpw_hashed@@', fwrootpw_hashed)
        content = content.replace('@@authorizedkey@@', authorizedkey)
        content = content.replace('@@apikey@@', apikey)
        content = content.replace('@@apisecret_hashed@@', apisecret_hashed)
        content = content.replace('@@binduserpw@@', binduserpw)
        content = content.replace('@@language@@', language)
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

    # create api credentials ini file
    msg = '* Saving api credentials '
    printScript(msg, '', False, False, True)
    try:
        rc = modIni(constants.FWAPIKEYS, 'api', 'key', apikey)
        rc = modIni(constants.FWAPIKEYS, 'api', 'secret', apisecret)
        os.system('chmod 400 ' + constants.FWAPIKEYS)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # upload new configfile
    rc = putFwConfig(firewallip, constants.ROOTPW)
    if not rc:
        sys.exit(1)

    # remove temporary files
    #os.unlink(fwconftmp)

    # reboot firewall
    rc = sshExec(firewallip, 'configctl firmware reboot', adminpw)
    if not rc:
        sys.exit(1)

# quit if firewall setup shall be skipped
if skipfw:
    msg = 'Skipping firewall setup as requested'
    printScript(msg, '', True, False, False)
else:
    main()
