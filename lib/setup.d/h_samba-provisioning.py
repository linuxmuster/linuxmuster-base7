#!/usr/bin/python3
#
# e_samba-provisioning.py
# thomas@linuxmuster.net
# 20170324
#

import configparser
import constants
import glob
import os
import sys
from functions import randomPassword
from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# stop services
msg = 'Stopping samba services '
printScript(msg, '', False, False, True)
services = ['winbind', 'samba-ad-dc', 'smbd', 'nmbd']
try:
    for s in services:
        subProc('service ' + s + ' stop', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser()
    setup.read(setupini)
    realm = setup.get('setup', 'domainname').upper()
    sambadomain = setup.get('setup', 'sambadomain')
    dnsforwarder = setup.get('setup', 'gatewayip')
    domainname = setup.get('setup', 'domainname')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# generate ad admin password
msg = 'Generating AD admin password '
printScript(msg, '', False, False, True)
try:
    adadminpw = randomPassword(16)
    with open(constants.ADADMINSECRET, 'w') as secret:
        secret.write(adadminpw)
    subProc('chmod 600 ' + constants.ADADMINSECRET, logfile)
    # symlink for sophomorix
    subProc('ln -sf ' + constants.ADADMINSECRET + ' ' + constants.SOPHOSYSDIR + '/sophomorix-samba.secret', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# alte smb.conf löschen
smbconf = '/etc/samba/smb.conf'
if os.path.isfile(smbconf):
    map(os.unlink, glob.glob(smbconf))

# provisioning samba
msg = 'Provisioning samba '
printScript(msg, '', False, False, True)
try:
    subProc('samba-tool domain provision --use-xattrs=yes --server-role=dc --domain=' + sambadomain + ' --realm=' + realm + ' --adminpass=' + adadminpw, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create krb5.conf symlink
msg = 'Provisioning krb5 '
printScript(msg, '', False, False, True)
try:
    krb5conf_src = '/var/lib/samba/private/krb5.conf'
    krb5conf_dst = '/etc/krb5.conf'
    if os.path.isfile(krb5conf_dst):
        os.remove(krb5conf_dst)
        os.symlink(krb5conf_src, krb5conf_dst)
        k = configparser.ConfigParser()
        k.read(krb5conf_dst)
        k.set('libdefaults', 'dns_lookup_realm', 'true')
        with open(krb5conf_dst, 'w') as config:
            k.write(config)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# loading sophomorix samba schema
msg = 'Provisioning sophomorix samba schema '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-samba --schema-load', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# set dns forwarder
msg = 'Setting dns forwarder to ' + dnsforwarder
printScript(msg, '', False, False, True)
try:
    samba = configparser.ConfigParser()
    samba.read(smbconf)
    samba.set('global', 'dns forwarder', dnsforwarder)
    with open (smbconf, 'w') as outfile:
        samba.write(outfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# restart services
msg = 'Restarting samba services '
printScript(msg, '', False, False, True)
try:
    subProc('systemctl daemon-reload', logfile)
    for s in services:
        subProc('service ' + s + ' stop', logfile)
    for s in services[::-1]:
        subProc('service ' + s + ' start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
