#!/usr/bin/python3
#
# samba provisioning
# thomas@linuxmuster.net
# 20250729
#

import configparser
import datetime
import os
import shlex
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import getSetupValue, mySetupLogfile, printScript, randomPassword, \
    readTextfile, writeTextfile
from linuxmuster_base7.setup.helpers import runWithLog

logfile = mySetupLogfile(__file__)

# stop services
msg = 'Stopping samba services '
printScript(msg, '', False, False, True)

services = ['winbind', 'samba-ad-dc', 'smbd', 'nmbd', 'systemd-resolved', 'samba-ad-dc']
try:
    for service in services:
        runWithLog(['systemctl', 'stop', service + '.service'], logfile)
        if service == 'samba-ad-dc':
            continue
        # disabling not needed samba services
        runWithLog(['systemctl', 'disable', service + '.service'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    realm = getSetupValue('domainname').upper()
    sambadomain = getSetupValue('sambadomain')
    serverip = getSetupValue('serverip')
    servername = getSetupValue('servername')
    domainname = getSetupValue('domainname')
    basedn = getSetupValue('basedn')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# generate ad admin password
msg = 'Generating AD admin password '
printScript(msg, '', False, False, True)
try:
    adadminpw = randomPassword(16)
    with open(environment.ADADMINSECRET, 'w') as secret:
        secret.write(adadminpw)
    runWithLog(['chmod', '400', environment.ADADMINSECRET], logfile)
    # symlink for sophomorix
    runWithLog(['ln', '-sf', environment.ADADMINSECRET, environment.SOPHOSYSDIR + '/sophomorix-samba.secret'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# alte smb.conf löschen
smbconf = '/etc/samba/smb.conf'
if os.path.isfile(smbconf):
    os.unlink(smbconf)

# provisioning samba
msg = 'Provisioning samba '
printScript(msg, '', False, False, True)
try:
    runWithLog(['samba-tool', 'domain', 'provision', '--use-rfc2307', '--server-role=dc',
                '--domain=' + sambadomain, '--realm=' + realm, '--adminpass=' + adadminpw],
               logfile, maskSecrets=[adadminpw])
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create krb5.conf symlink
krb5conf_src = '/var/lib/samba/private/krb5.conf'
if os.path.isfile(krb5conf_src):
    msg = 'Provisioning krb5 '
    printScript(msg, '', False, False, True)
    try:
        krb5conf_dst = '/etc/krb5.conf'
        if os.path.isfile(krb5conf_dst):
            os.remove(krb5conf_dst)
        os.symlink(krb5conf_src, krb5conf_dst)
        rc, filedata = readTextfile(krb5conf_dst)
        filedata = filedata.replace('dns_lookup_realm = false', 'dns_lookup_realm = true')
        rc = writeTextfile(krb5conf_dst, filedata, 'w')
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(error, '', True, True, False, len(msg))
        sys.exit(1)

# restart services
msg = 'Enabling samba services '
printScript(msg, '', False, False, True)
try:
    runWithLog(['systemctl', 'daemon-reload'], logfile)
    for service in services:
        runWithLog(['systemctl', 'stop', service], logfile)
    runWithLog(['systemctl', 'mask', 'smbd.service'], logfile)
    runWithLog(['systemctl', 'mask', 'nmbd.service'], logfile)
    # start only samba-ad-dc service
    runWithLog(['systemctl', 'unmask', 'samba-ad-dc.service'], logfile)
    runWithLog(['systemctl', 'enable', 'samba-ad-dc.service'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# backup samba before sophomorix modifies anything
msg = 'Backing up samba '
printScript(msg, '', False, False, True)
try:
    runWithLog(['sophomorix-samba', '--backup-samba', 'without-sophomorix-schema'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# loading sophomorix samba schema
msg = 'Provisioning sophomorix samba schema '
printScript(msg, '', False, False, True)
try:
    subprocess.run(['sh', '-c', 'cd /usr/share/sophomorix/schema && ./sophomorix_schema_add.sh ' + basedn + ' . -H /var/lib/samba/private/sam.ldb -writechanges'], capture_output=True, text=True, check=False)  # Complex shell command requiring cd
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# fixing resolv.conf
msg = 'Fixing resolv.conf '
printScript(msg, '', False, False, True)
try:
    resconf = '/etc/resolv.conf'
    now = str(datetime.datetime.now()).split('.')[0]
    header = '# created by linuxmuster-setup ' + now + '\n'
    search = 'search ' + domainname + '\n'
    ns = 'nameserver ' + serverip + '\n'
    filedata = header + search + ns
    os.unlink(resconf)
    rc = writeTextfile(resconf, filedata, 'w')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# exchange smb.conf
msg = 'Exchanging smb.conf '
printScript(msg, '', False, False, True)
try:
    import shutil
    shutil.move(smbconf, smbconf + '.orig')
    shutil.move(smbconf + '.setup', smbconf)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# starting samba service again
msg = 'Starting samba ad dc service '
printScript(msg, '', False, False, True)
try:
    runWithLog(['systemctl', 'start', 'samba-ad-dc.service'], logfile)
    import time
    time.sleep(5)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
