#!/usr/bin/python3
#
# create samba users & shares
# thomas@linuxmuster.net
# 20200304
#

import configparser
import constants
import os
import sys
from functions import modIni
from functions import readTextfile
from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    adminpw = setup.get('setup', 'adminpw')
    domainname = setup.get('setup', 'domainname')
    sambadomain = setup.get('setup', 'sambadomain')
    firewallip = setup.get('setup', 'firewallip')
    # get binduser password
    rc, binduserpw = readTextfile(constants.BINDUSERSECRET)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# samba backup
msg = 'Backing up samba '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-samba --backup-samba without-users', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# renew sophomorix configs
os.system('rm -f ' + constants.SCHOOLCONF)
os.system('rm -f ' + constants.SOPHOSYSDIR + '/sophomorix.conf')
subProc('sophomorix-postinst', logfile)

# create default-school share
schoolname = os.path.basename(constants.DEFAULTSCHOOL)
defaultpath = constants.SCHOOLSSHARE + '/' + schoolname
shareopts = 'writeable=y guest_ok=n'
shareoptsex = ['comment "Share for default-school"', '"hide unreadable" yes', '"msdfs root" no', '"strict allocate" yes', '"valid users" "' + sambadomain + '\\administrator, @' + sambadomain + '\\SCHOOLS"']
msg = 'Creating share for ' + schoolname
printScript(msg, '', False, False, True)
try:
    subProc('net conf addshare ' + schoolname + ' ' + defaultpath + ' ' + shareopts, logfile)
    for item in shareoptsex:
        subProc('net conf setparm ' + schoolname + ' ' + item)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global-admin
sophomorix_comment = "created by linuxmuster-setup"
msg = 'Creating samba account for global-admin '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create-global-admin global-admin --password "' + adminpw + '"', logfile)
    subProc('sophomorix-user --user global-admin --comment "' + sophomorix_comment + '"', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global bind user
msg = 'Creating samba account for global-binduser '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create-global-binduser global-binduser --password "' + binduserpw + '"', logfile)
    subProc('sophomorix-user --user global-binduser --comment "' + sophomorix_comment + '"', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# no expiry for Administrator password
msg = 'No expiry for administrative passwords '
printScript(msg, '', False, False, True)
try:
    for i in ['Administrator', 'global-admin', 'sophomorix-admin', 'global-binduser']:
        subProc('samba-tool user setexpiry ' + i + ' --noexpiry', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create default-school, no connection to ad
msg = 'Creating ou for ' + schoolname
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-school --create --school ' + schoolname, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# add firewall as dns forwarder
# smb.conf
msg = 'Add firewall as dns forwarder '
printScript(msg, '', False, False, True)
try:
    modIni('/etc/samba/smb.conf','global', 'dns forwarder', firewallip)
    subProc('echo "nameserver ' + firewallip + '" >> /etc/resolv.conf', logfile)
    subProc('systemctl restart samba-ad-dc.service', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
