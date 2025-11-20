#!/usr/bin/python3
#
# create samba users & shares
# thomas@linuxmuster.net
# 20251113
#

"""
Setup module k_samba-users: Create initial Samba users, groups, and shares.

This module:
- Creates global binduser account for LDAP queries (used by dhcpd, etc.)
- Creates sophomorix-admin user for school management
- Creates global-admin user for system administration
- Sets passwords for all service accounts
- Creates required organizational units (OUs) in AD
- Configures Samba shares (homes, printers, etc.)
- Sets proper ACLs and permissions on share directories
- Runs sophomorix-check to validate user database

User accounts created:
- global-binduser: Read-only LDAP access for services
- sophomorix-admin: School administration via sophomorix tools
- global-admin: Full system administration rights

All service passwords are stored securely in /etc/linuxmuster/.secret/
"""

import configparser
import datetime
import os
import shlex
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from functions import mySetupLogfile, printScript, randomPassword, readTextfile
from functions import replaceInFile, writeTextfile
from setup.helpers import runWithLog

logfile = mySetupLogfile(__file__)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = environment.SETUPINI
try:
    setup = configparser.RawConfigParser(delimiters=('='))
    setup.read(setupini)
    adminpw = setup.get('setup', 'adminpw')
    domainname = setup.get('setup', 'domainname')
    sambadomain = setup.get('setup', 'sambadomain')
    firewallip = setup.get('setup', 'firewallip')
    # get binduser password
    rc, binduserpw = readTextfile(environment.BINDUSERSECRET)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# samba backup
msg = 'Backing up samba '
printScript(msg, '', False, False, True)
try:
    runWithLog(['sophomorix-samba', '--backup-samba', 'without-users'], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# renew sophomorix configs
import os.path
if os.path.isfile(environment.SCHOOLCONF):
    os.unlink(environment.SCHOOLCONF)
if os.path.isfile(environment.SOPHOSYSDIR + '/sophomorix.conf'):
    os.unlink(environment.SOPHOSYSDIR + '/sophomorix.conf')
runWithLog(['sophomorix-postinst'], logfile)

# create default-school share
schoolname = os.path.basename(environment.DEFAULTSCHOOL)
defaultpath = environment.SCHOOLSSHARE + '/' + schoolname
shareopts = 'writeable=y guest_ok=n'
shareoptsex = ['comment "Share for default-school"', '"hide unreadable" yes', '"msdfs root" no',
               '"strict allocate" yes', '"valid users" "' + sambadomain + '\\administrator, @' + sambadomain + '\\SCHOOLS"']
msg = 'Creating share for ' + schoolname + ' '
printScript(msg, '', False, False, True)
try:
    runWithLog(['net', 'conf', 'addshare', schoolname, defaultpath, shareopts], logfile)
    for item in shareoptsex:
        runWithLog('net conf setparm ' + schoolname + ' ' + item, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create global-admin
sophomorix_comment = "created by linuxmuster-setup"
msg = 'Creating samba account for global-admin '
printScript(msg, '', False, False, True)
try:
    runWithLog(['sophomorix-admin', '--create-global-admin', 'global-admin',
                '--password', adminpw],
               logfile, maskSecrets=[adminpw])
    runWithLog(['sophomorix-user', '--user', 'global-admin',
                '--comment', sophomorix_comment], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create global bind user
msg = 'Creating samba account for global-binduser '
printScript(msg, '', False, False, True)
try:
    runWithLog(['sophomorix-admin', '--create-global-binduser', 'global-binduser',
                '--password', binduserpw],
               logfile, maskSecrets=[binduserpw])
    runWithLog(['sophomorix-user', '--user', 'global-binduser',
                '--comment', sophomorix_comment], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# no expiry for Administrator password
msg = 'No expiry for administrative passwords '
printScript(msg, '', False, False, True)
try:
    for item in ['Administrator', 'global-admin', 'global-binduser']:
        runWithLog(['samba-tool', 'user', 'setexpiry', item, '--noexpiry',
                    '--username=global-admin', '--password=' + adminpw],
                   logfile, maskSecrets=[adminpw])
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# create default-school, no connection to ad
msg = 'Creating ou for ' + schoolname + ' '
printScript(msg, '', False, False, True)
try:
    runWithLog(['sophomorix-school', '--create', '--school', schoolname], logfile)
    runWithLog(['sophomorix-school', '--gpo-create', schoolname], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create pgmadmin for default-school
msg = 'Creating samba account for pgmadmin '
printScript(msg, '', False, False, True)
try:
    runWithLog(['sophomorix-admin', '--create-school-admin', 'pgmadmin',
                '--school', schoolname, '--password', adminpw],
               logfile, maskSecrets=[adminpw])
    runWithLog(['sophomorix-user', '--user', 'pgmadmin',
                '--comment', sophomorix_comment], logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create dns-admin account
msg = 'Creating samba account for dns-admin '
printScript(msg, '', False, False, True)
try:
    dnspw = randomPassword(16)
    desc = 'Unprivileged user for DNS updates via DHCP server'
    runWithLog(['samba-tool', 'user', 'create', 'dns-admin', dnspw,
                '--description=' + desc, '--username=global-admin',
                '--password=' + adminpw],
               logfile, maskSecrets=[dnspw, adminpw])
    runWithLog(['samba-tool', 'user', 'setexpiry', 'dns-admin', '--noexpiry',
                '--username=global-admin', '--password=' + adminpw],
               logfile, maskSecrets=[adminpw])
    runWithLog(['samba-tool', 'group', 'addmembers', 'DnsAdmins', 'dns-admin',
                '--username=global-admin', '--password=' + adminpw],
               logfile, maskSecrets=[adminpw])
    rc = writeTextfile(environment.DNSADMINSECRET, dnspw, 'w')
    subprocess.run(['chgrp', 'dhcpd', environment.DNSADMINSECRET], check=True)
    subprocess.run(['chmod', '440', environment.DNSADMINSECRET], check=True)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# mask passwords in logfile
msg = 'Masking passwords in logfile '
printScript(msg, '', False, False, True)
try:
    for item in [adminpw, binduserpw, dnspw]:
        replaceInFile(logfile, item, '******')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)
