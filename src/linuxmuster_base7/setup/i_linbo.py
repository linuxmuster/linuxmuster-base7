#!/usr/bin/python3
#
# linbo setup
# thomas@linuxmuster.net
# 20250729
#

import configparser
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import os
import re
import subprocess
import sys

from linuxmuster_base7.functions import backupCfg, enterPassword, getSetupValue, isValidPassword, \
    mySetupLogfile, modIni, printScript, readTextfile, setupComment, subProc, writeTextfile

logfile = mySetupLogfile(__file__)

# read INIFILE, get schoolname
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    serverip = getSetupValue('serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# test adminpw
try:
    adminpw = getSetupValue('adminpw')
except:
    adminpw = ''
if not isValidPassword(adminpw):
    printScript('There is no admin password!')
    adminpw = enterPassword('admin', True)
    if not isValidPassword(adminpw):
        printScript('No valid admin password! Aborting!')
        sys.exit(1)
    else:
        msg = 'Saving admin password to setup.ini '
        printScript(msg, '', False, False, True)
        rc = modIni(environment.SETUPINI, 'setup', 'adminpw', adminpw)
        if rc == True:
            printScript(' Success!', '', True, True, False, len(msg))
        else:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

# write linbo auth data to rsyncd.secrets
msg = 'Creating rsync secrets file '
printScript(msg, '', False, False, True)
configfile = '/etc/rsyncd.secrets'
filedata = setupComment() + '\n' + 'linbo:' + adminpw + '\n'
try:
    with open(configfile, 'w') as outfile:
        outfile.write(filedata)
    # set permissions
    subProc('chmod 600 ' + configfile, logfile)
    # enable rsync service
    subProc('systemctl -q enable rsync.service', logfile)
    # restart rsync service
    subProc('service rsync stop', logfile)
    subProc('service rsync start', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# set serverip in default start.conf
msg = 'Providing server ip to linbo start.conf files '
# default start.conf
conffiles = [environment.LINBODIR + '/start.conf']
# collect example start.conf files
for item in os.listdir(environment.LINBODIR + '/examples'):
    if not item.startswith('start.conf.'):
        continue
    conffiles.append(environment.LINBODIR + '/examples/' + item)
printScript(msg, '', False, False, True)
try:
    for startconf in conffiles:
        rc, content = readTextfile(startconf)
        rc = writeTextfile(startconf, content.replace(
            '10.16.1.1', serverip), 'w')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# linbo-torrent service
msg = 'Activating linbo-torrent service '
printScript(msg, '', False, False, True)
try:
    subprocess.call('systemctl -q enable opentracker 2>&1', shell=True)
    subprocess.call('systemctl -q enable linbo-torrent 2>&1', shell=True)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# linbofs update
msg = 'Reconfiguring linbo (forking to background) '
printScript(msg, '', False, False, True)
try:
    subProc('rm -f ' + environment.SYSDIR + '/linbo/*key*', logfile)
    subprocess.call('dpkg-reconfigure linuxmuster-linbo7 >> '
                    + logfile + ' 2>&1 &', shell=True)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
