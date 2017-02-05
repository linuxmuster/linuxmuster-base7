#!/usr/bin/python3
#
# e_samba-provisioning.py
# thomas@linuxmuster.net
# 20170205
#

import configparser
import constants
import os
from functions import randompassword
from functions import printScript

printScript('', 'begin')
printScript(os.path.basename(__file__))

# stop services
os.system('service smbd stop')
os.system('service nmbd stop')

# save old smb.conf
smbconf = '/etc/samba/smb.conf'
smbconf_old = smbconf + '.old'
if os.path.isfile(smbconf_old):
    os.remove(smbconf_old)
if os.path.isfile(smbconf):
    os.rename(smbconf, smbconf_old )

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)

REALM = i.get('setup', 'domainname').upper()
sambadomain = i.get('setup', 'sambadomain')
dnsforwarder = i.get('setup', 'gatewayip')
domainname = i.get('setup', 'domainname')
adminpw = i.get('setup', 'adminpw')

# generate ad admin password
adadminpw = randompassword(16)
with open(constants.ADADMINSECRET, 'w') as secret:
    secret.write(adadminpw)
os.system('chmod 600 ' + constants.ADADMINSECRET)
# symlink for sophomorix
os.system('ln -sf ' + constants.ADADMINSECRET + ' ' + constants.SOPHOSYSDIR + '/sophomorix-samba.secret')

# provisioning
#os.system('samba-tool domain provision --use-xattrs=yes --use-rfc2307 --server-role=dc --domain=' + sambadomain + ' --realm=' + REALM + ' --adminpass=' + adadminpw)
os.system('samba-tool domain provision --use-xattrs=yes --server-role=dc --domain=' + sambadomain + ' --realm=' + REALM + ' --adminpass="' + adadminpw + '"')

# provide dns forwarder in smb.conf
s = configparser.ConfigParser()
s.read(smbconf)
s.set('global', 'dns forwarder', dnsforwarder)
with open(smbconf, 'w') as config:
    s.write(config)

# create krb5.conf symlink
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

# loading sophomorix samba schema
os.system('sophomorix-samba --schema-load')
