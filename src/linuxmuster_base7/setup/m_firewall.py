#!/usr/bin/python3
#
# firewall setup
# thomas@linuxmuster.net
# 20251110
#

import bcrypt
import datetime
import os
import shlex
import shutil
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from bs4 import BeautifulSoup
from linuxmuster_base7.functions import getFwConfig, getSetupValue, isValidHostIpv4, mySetupLogfile
from linuxmuster_base7.functions import modIni, printScript, putFwConfig, putSftp, randomPassword
from linuxmuster_base7.functions import readTextfile, sshExec, writeTextfile
from linuxmuster_base7.setup.helpers import runWithLog

logfile = mySetupLogfile(__file__)


def readSetupData():
    """Read all setup configuration values needed for firewall setup."""
    msg = 'Reading setup data '
    printScript(msg, '', False, False, True)
    try:
        data = {
            'serverip': getSetupValue('serverip'),
            'bitmask': getSetupValue('bitmask'),
            'firewallip': getSetupValue('firewallip'),
            'servername': getSetupValue('servername'),
            'domainname': getSetupValue('domainname'),
            'basedn': getSetupValue('basedn'),
            'network': getSetupValue('network'),
            'adminpw': getSetupValue('adminpw')
        }
        printScript(' Success!', '', True, True, False, len(msg))
        return data
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def getFirewallPasswords():
    """Determine rollout and production passwords for firewall."""
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
        productionpw = getSetupValue('adminpw')
    return rolloutpw, productionpw


def createRadiusSecret():
    """Create and save RADIUS secret."""
    msg = 'Calculating radius secret '
    printScript(msg, '', False, False, True)
    try:
        radiussecret = randomPassword(16)
        with open(environment.RADIUSSECRET, 'w') as secret:
            secret.write(radiussecret)
        runWithLog(['chmod', '400', environment.RADIUSSECRET], logfile)
        printScript(' Success!', '', True, True, False, len(msg))
        return radiussecret
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def backupFirewallConfig(fwconftmp, timestamp):
    """Backup current firewall configuration."""
    fwconfbak = fwconftmp.replace('.xml', '-' + timestamp + '.xml')
    msg = '* Backing up '
    printScript(msg, '', False, False, True)
    try:
        shutil.copy(fwconftmp, fwconfbak)
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def extractConfigValues(fwconftmp):
    """Extract configuration values from current firewall config XML."""
    msg = '* Reading current config '
    printScript(msg, '', False, False, True)
    try:
        rc, content = readTextfile(fwconftmp)
        soup = BeautifulSoup(content, features='xml')

        # save certain configuration values for later use
        config = {
            'firmware': str(soup.find('firmware')),
            'sysctl': str(soup.find('sysctl'))
        }

        # get already configured interfaces
        interfaces_element = soup.find('interfaces')
        if interfaces_element and '<lan>' in str(interfaces_element):
            config['interfaces'] = str(interfaces_element)
        else:
            config['interfaces'] = ''

        # save language information
        try:
            config['language'] = str(soup.findAll('language')[0])
        except Exception:
            # second try get language from locale settings
            try:
                lang = os.environ['LANG'].split('.')[0]
            except Exception:
                lang = 'en_US'
            config['language'] = '<language>' + lang + '</language>'

        # save gateways configuration
        gateways_element = soup.find('gateways')
        config['gateways'] = str(gateways_element) if gateways_element else ''

        gwconfig_element = soup.find('Gateways')
        config['gwconfig'] = str(gwconfig_element) if gwconfig_element else ''

        # save opt1 configuration if present
        try:
            config['opt1config'] = str(soup.findAll('opt1')[0])
        except Exception:
            config['opt1config'] = ''

        printScript(' Success!', '', True, True, False, len(msg))
        return config
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def readCertificatesAndKeys():
    """Read base64 encoded certificates and SSH keys."""
    msg = '* Reading certificates & ssh key '
    printScript(msg, '', False, False, True)
    try:
        rc, cacertb64 = readTextfile(environment.CACERTB64)
        rc, fwcertb64 = readTextfile(environment.SSLDIR + '/firewall.cert.pem.b64')
        rc, fwkeyb64 = readTextfile(environment.SSLDIR + '/firewall.key.pem.b64')
        rc, authorizedkey = readTextfile(environment.SSHPUBKEYB64)
        printScript(' Success!', '', True, True, False, len(msg))
        return cacertb64, fwcertb64, fwkeyb64, authorizedkey
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def createNoProxyAliasContent(network, serverip):
    """Create list of first ten network IPs for NoProxy group alias."""
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
            aliascontent = aliascontent + ' ' + aliasip
    # add server ip if not already collected
    if serverip not in aliascontent:
        aliascontent = aliascontent + '\n' + serverip
    return aliascontent


def createFirewallConfig(fwconftpl, fwconftmp, config, setup_data, productionpw,
                        binduserpw, radiussecret, timezone, aliascontent,
                        cacertb64, fwcertb64, fwkeyb64, authorizedkey):
    """Create new firewall configuration from template."""
    msg = '* Creating xml configuration file '
    printScript(msg, '', False, False, True)
    try:
        # create password hash for new firewall password
        hashedpw = bcrypt.hashpw(str.encode(productionpw), bcrypt.gensalt(10))
        fwrootpw_hashed = hashedpw.decode()

        # create API credentials
        apikey = randomPassword(80)
        apisecret = randomPassword(80)
        hashedpw = bcrypt.hashpw(str.encode(apisecret), bcrypt.gensalt(10))
        apisecret_hashed = hashedpw.decode()

        # read template
        rc, content = readTextfile(fwconftpl)

        # replace placeholders with values
        replacements = {
            '@@firmware@@': config['firmware'],
            '@@sysctl@@': config['sysctl'],
            '@@servername@@': setup_data['servername'],
            '@@domainname@@': setup_data['domainname'],
            '@@basedn@@': setup_data['basedn'],
            '@@interfaces@@': config['interfaces'],
            '@@gateways@@': config['gateways'],
            '@@gwconfig@@': config['gwconfig'],
            '@@serverip@@': setup_data['serverip'],
            '@@firewallip@@': setup_data['firewallip'],
            '@@network@@': setup_data['network'],
            '@@bitmask@@': setup_data['bitmask'],
            '@@aliascontent@@': aliascontent,
            '@@fwrootpw_hashed@@': fwrootpw_hashed,
            '@@authorizedkey@@': authorizedkey,
            '@@apikey@@': apikey,
            '@@apisecret_hashed@@': apisecret_hashed,
            '@@binduserpw@@': binduserpw,
            '@@radiussecret@@': radiussecret,
            '@@language@@': config['language'],
            '@@timezone@@': timezone,
            '@@cacertb64@@': cacertb64,
            '@@fwcertb64@@': fwcertb64,
            '@@fwkeyb64@@': fwkeyb64
        }

        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        # write new configfile
        rc = writeTextfile(fwconftmp, content, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
        return apikey, apisecret
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def saveApiCredentials(apikey, apisecret):
    """Save API credentials to ini file."""
    msg = '* Saving api credentials '
    printScript(msg, '', False, False, True)
    try:
        rc = modIni(environment.FWAPIKEYS, 'api', 'key', apikey)
        rc = modIni(environment.FWAPIKEYS, 'api', 'secret', apisecret)
        subprocess.run(['chmod', '400', environment.FWAPIKEYS], check=True)
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)


def uploadConfigFiles(firewallip, rolloutpw):
    """Upload configuration files to firewall."""
    # upload modified main config.xml
    rc = putFwConfig(firewallip, '/tmp/opnsense.xml', rolloutpw)
    if not rc:
        sys.exit(1)

    # upload modified auth config file for web-proxy sso (#83)
    printScript('Creating web proxy sso auth config file')
    runWithLog([environment.FWSHAREDIR + '/create-auth-config.py'], logfile)
    conftmp = '/tmp/' + os.path.basename(environment.FWAUTHCFG)
    if not os.path.isfile(conftmp):
        sys.exit(1)
    rc = putSftp(firewallip, conftmp, conftmp, rolloutpw)
    if not rc:
        sys.exit(1)

    # remove temporary files
    os.unlink(conftmp)


def rebootFirewall(firewallip, rolloutpw):
    """Install extensions and reboot firewall."""
    printScript('Installing extensions and rebooting firewall')
    fwsetup_local = environment.FWSHAREDIR + '/fwsetup.sh'
    fwsetup_remote = '/tmp/fwsetup.sh'
    rc = putSftp(firewallip, fwsetup_local, fwsetup_remote, rolloutpw)
    rc = sshExec(firewallip, 'chmod +x ' + fwsetup_remote, rolloutpw)
    rc = sshExec(firewallip, fwsetup_remote, rolloutpw)
    if not rc:
        sys.exit(1)


# main routine
def main():
    """Orchestrate firewall setup process."""
    # Read all configuration data
    setup_data = readSetupData()

    # Get timezone
    rc, timezone = readTextfile('/etc/timezone')
    timezone = timezone.replace('\n', '')

    # Get binduser password
    rc, binduserpw = readTextfile(environment.BINDUSERSECRET)

    # Determine rollout and production passwords
    rolloutpw, productionpw = getFirewallPasswords()

    # Create RADIUS secret
    radiussecret = createRadiusSecret()

    # Setup firewall config file paths
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    fwconftmp = environment.FWCONFLOCAL
    fwconftpl = environment.FWOSCONFTPL

    # Get current firewall configuration
    rc = getFwConfig(setup_data['firewallip'], rolloutpw)
    if not rc:
        sys.exit(1)

    # Backup current configuration
    backupFirewallConfig(fwconftmp, timestamp)

    # Extract configuration values from current config
    config = extractConfigValues(fwconftmp)

    # Read certificates and keys
    cacertb64, fwcertb64, fwkeyb64, authorizedkey = readCertificatesAndKeys()

    # Create NoProxy alias content
    aliascontent = createNoProxyAliasContent(setup_data['network'], setup_data['serverip'])

    # Create new firewall configuration
    apikey, apisecret = createFirewallConfig(
        fwconftpl, fwconftmp, config, setup_data, productionpw,
        binduserpw, radiussecret, timezone, aliascontent,
        cacertb64, fwcertb64, fwkeyb64, authorizedkey
    )

    # Save API credentials
    saveApiCredentials(apikey, apisecret)

    # Upload configuration files to firewall
    uploadConfigFiles(setup_data['firewallip'], rolloutpw)

    # Reboot firewall with new configuration
    rebootFirewall(setup_data['firewallip'], rolloutpw)


# quit if firewall setup shall be skipped
skipfw = getSetupValue('skipfw')
if skipfw:
    msg = 'Skipping firewall setup as requested'
    printScript(msg, '', True, False, False)
else:
    main()
