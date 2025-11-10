#!/usr/bin/python3
#
# firewall setup
# thomas@linuxmuster.net
# 20251110
#

import bcrypt
import environment
import datetime
import os
import shutil
import sys

from bs4 import BeautifulSoup
from functions import getFwConfig, getSetupValue, isValidHostIpv4, mySetupLogfile
from functions import modIni, printScript, putFwConfig, putSftp, randomPassword
from functions import readTextfile, sshExec, subProc, writeTextfile

logfile = mySetupLogfile(__file__)


# main routine
def main():
    # get various setup values
    msg = 'Reading setup data '
    printScript(msg, '', False, False, True)
    try:
        serverip = getSetupValue('serverip')
        bitmask = getSetupValue('bitmask')
        firewallip = getSetupValue('firewallip')
        servername = getSetupValue('servername')
        domainname = getSetupValue('domainname')
        basedn = getSetupValue('basedn')
        network = getSetupValue('network')
        adminpw = getSetupValue('adminpw')
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # get timezone
    rc, timezone = readTextfile('/etc/timezone')
    timezone = timezone.replace('\n', '')

    # get binduser password
    rc, binduserpw = readTextfile(environment.BINDUSERSECRET)

    # get firewall root password provided by linuxmuster-opnsense-reset
    pwfile = '/tmp/linuxmuster-opnsense-reset'
    if os.path.isfile(pwfile):
        # firewall reset after setup, given password is current password
        rc, rolloutpw = readTextfile(pwfile)
        productionpw = rolloutpw
        os.unlink(pwfile)
    else:
        # initial setup, rollout root password is standardized
        rolloutpw = environment.ROOTPW
        # new root production password provided by setup
        productionpw = adminpw

    # create and save radius secret
    msg = 'Calculating radius secret '
    printScript(msg, '', False, False, True)
    try:
        radiussecret = randomPassword(16)
        with open(environment.RADIUSSECRET, 'w') as secret:
            secret.write(radiussecret)
        subProc('chmod 400 ' + environment.RADIUSSECRET, logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # firewall config files
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    fwconftmp = environment.FWCONFLOCAL
    fwconfbak = fwconftmp.replace('.xml', '-' + now + '.xml')
    fwconftpl = environment.FWOSCONFTPL

    # get current config
    rc = getFwConfig(firewallip, rolloutpw)
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
        soup = BeautifulSoup(content, features='xml')
        # save certain configuration values for later use
        firmware = str(soup.find('firmware'))
        sysctl = str(soup.find('sysctl'))
        # get already configured interfaces
        interfaces = ''
        interfaces_element = soup.find('interfaces')
        if interfaces_element and '<lan>' in str(interfaces_element):
            interfaces = str(interfaces_element)
        # save language information
        try:
            language = str(soup.findAll('language')[0])
        except:
            language = ''
        # second try get language from locale settings
        if language == '':
            try:
                lang = os.environ['LANG'].split('.')[0]
            except:
                lang = 'en_US'
            language = '<language>' + lang + '</language>'
        # save gateways configuration
        gateways = ''
        gateways_element = soup.find('gateways')
        if gateways_element:
            gateways = str(gateways_element)
        gwconfig = ''
        gwconfig_element = soup.find('Gateways')
        if gwconfig_element:
            gwconfig = str(gwconfig_element)
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
        rc, cacertb64 = readTextfile(environment.CACERTB64)
        rc, fwcertb64 = readTextfile(
            environment.SSLDIR + '/firewall.cert.pem.b64')
        rc, fwkeyb64 = readTextfile(environment.SSLDIR + '/firewall.key.pem.b64')
        rc, authorizedkey = readTextfile(environment.SSHPUBKEYB64)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # create list of first ten network ips for aliascontent (NoProxy group in firewall)
    aliascontent = ''
    netpre = network.split(
        '.')[0] + '.' + network.split('.')[1] + '.' + network.split('.')[2] + '.'
    c = 0
    max = 10
    while c < max:
        c = c + 1
        aliasip = netpre + str(c)
        if aliascontent == '':
            aliascontent = aliasip
        else:
            aliascontent = aliascontent + ' ' + aliasip
    # add server ip if not already collected
    if not serverip in aliascontent:
        aliascontent = aliascontent + '\n' + serverip

    # create new firewall configuration
    msg = '* Creating xml configuration file '
    printScript(msg, '', False, False, True)
    try:
        # create password hash for new firewall password
        hashedpw = bcrypt.hashpw(str.encode(productionpw), bcrypt.gensalt(10))
        fwrootpw_hashed = hashedpw.decode()
        apikey = randomPassword(80)
        apisecret = randomPassword(80)
        hashedpw = bcrypt.hashpw(str.encode(apisecret), bcrypt.gensalt(10))
        apisecret_hashed = hashedpw.decode()
        # read template
        rc, content = readTextfile(fwconftpl)
        # replace placeholders with values
        content = content.replace('@@firmware@@', firmware)
        content = content.replace('@@sysctl@@', sysctl)
        content = content.replace('@@servername@@', servername)
        content = content.replace('@@domainname@@', domainname)
        content = content.replace('@@basedn@@', basedn)
        content = content.replace('@@interfaces@@', interfaces)
        content = content.replace('@@gateways@@', gateways)
        content = content.replace('@@gwconfig@@', gwconfig)
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
        content = content.replace('@@radiussecret@@', radiussecret)
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
        rc = modIni(environment.FWAPIKEYS, 'api', 'key', apikey)
        rc = modIni(environment.FWAPIKEYS, 'api', 'secret', apisecret)
        os.system('chmod 400 ' + environment.FWAPIKEYS)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

    # upload config files
    # upload modified main config.xml
    rc = putFwConfig(firewallip, '/tmp/opnsense.xml', rolloutpw)
    if not rc:
        sys.exit(1)

    # upload modified auth config file for web-proxy sso (#83)
    printScript('Creating web proxy sso auth config file')
    subProc(environment.FWSHAREDIR + '/create-auth-config.py', logfile)
    conftmp = '/tmp/' + os.path.basename(environment.FWAUTHCFG)
    if not os.path.isfile(conftmp):
        sys.exit(1)
    rc = putSftp(firewallip, conftmp, conftmp, rolloutpw)
    if not rc:
        sys.exit(1)

    # remove temporary files
    os.unlink(conftmp)

    # reboot firewall
    printScript('Installing extensions and rebooting firewall')
    fwsetup_local = environment.FWSHAREDIR + '/fwsetup.sh'
    fwsetup_remote = '/tmp/fwsetup.sh'
    rc = putSftp(firewallip, fwsetup_local, fwsetup_remote, rolloutpw)
    rc = sshExec(firewallip, 'chmod +x ' + fwsetup_remote, rolloutpw)
    rc = sshExec(firewallip, fwsetup_remote, rolloutpw)
    if not rc:
        sys.exit(1)


# quit if firewall setup shall be skipped
skipfw = getSetupValue('skipfw')
if skipfw:
    msg = 'Skipping firewall setup as requested'
    printScript(msg, '', True, False, False)
else:
    main()
