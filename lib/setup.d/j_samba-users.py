#!/usr/bin/python3
#
# create samba users
# thomas@linuxmuster.net
# 20180627
#

import configparser
import constants
import os
import sys
from functions import randomPassword
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
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    adminpw = setup.get('setup', 'adminpw')
    domainname = setup.get('setup', 'domainname')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create sophomorix admin user
msg = 'Calculating random passwords '
printScript(msg, '', False, False, True)
try:
    binduserpw = randomPassword(16)
    with open(constants.BINDUSERSECRET, 'w') as secret:
        secret.write(binduserpw)
    subProc('chmod 400 ' + constants.SECRETDIR + '/*', logfile)
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

# create default-school share
schoolname = os.path.basename(constants.DEFAULTSCHOOL)
defaultpath = constants.SCHOOLSSHARE + '/' + schoolname
shareopts = constants.SCHOOLSSHAREOPTS
msg = 'Creating share for ' + schoolname
printScript(msg, '', False, False, True)
try:
    subProc('net conf addshare ' + schoolname + ' ' + defaultpath + ' ' + shareopts, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global-admin
msg = 'Creating samba account for global-admin '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create-global-admin global-admin --password ' + adminpw, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create global bind user
msg = 'Creating samba account for global-binduser '
printScript(msg, '', False, False, True)
try:
    subProc('sophomorix-admin --create-global-binduser global-binduser --password ' + binduserpw, logfile)
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

# create user shares
printScript('Creating user shares:')
chown_admin = "global-admin:Domain Admins"
acl_admin = "u::rwx,u:global-admin:rwx,g::rwx,g:Domain Admins:rwx,g:users:rx,o::-"
acl_linbo = "u::rwx,u:global-admin:rwx,g::rwx,g:Domain Admins:rwx,o::rx"
chown_users = "global-admin:users"
acl_users = "u::rwx,u:global-admin:rwx,g::rwx,g:Domain Admins:rwx,g:users:rwx,o::-"
chown_teachers = "global-admin:teachers"
acl_teachers = "u::rwx,u:global-admin:rwx,g::rwx,g:Domain Admins:rwx,g:teachers:rwx,o::-"
for share in ['printers', 'print$', 'linbo', 'pgm', 'cdrom', 'share', 'classes', 'projects', 'school', 'teachers']:
    try:
        msg = '* ' + share + ' '
        printScript(msg, '', False, False, True)
        # define paths
        if share == 'print$':
            sharepath = '/var/lib/samba/printers'
        elif share == 'printers':
            sharepath = '/var/tmp'
        elif share == 'linbo':
            sharepath = constants.LINBODIR
        elif share == 'classes' or share == 'projects' or share == 'school' or share == 'teachers':
            sharepath = defaultpath + '/share/' + share
        else:
            sharepath = defaultpath + '/' + share
        # create share folders
        subProc('mkdir -p ' + sharepath, logfile)
        # add shares
        if not share in ['classes', 'projects', 'school', 'teachers']:
            subProc('net conf addshare ' + share + ' ' + sharepath + ' ' + shareopts, logfile)
        # define acls
        if share == 'school':
            chown_cur = chown_users
            acl_cur = acl_users
        elif share == 'linbo':
            chown_cur = chown_admin
            acl_cur = acl_linbo
        elif share == 'teachers':
            chown_cur = chown_teachers
            acl_cur = acl_teachers
        else:
            chown_cur = chown_admin
            acl_cur = acl_admin
        # set permissions
        subProc(constants.SHAREDIR + '/setfacl.sh "' + chown_cur + '" "' + acl_cur + '" ' + sharepath, logfile)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
