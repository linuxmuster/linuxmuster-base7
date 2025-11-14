#!/usr/bin/python3
#
# linbo setup
# thomas@linuxmuster.net
# 20251114
#

"""
Setup module i_linbo: Configure LINBO (Linux Network Boot) system.

This module:
- Creates LINBO directory structure (/srv/linbo/)
- Generates example start.conf files for different OS types (Ubuntu, Windows)
- Creates LINBO icons directory and copies default icons
- Sets up PXE boot configuration
- Configures proper file and directory permissions
- Prepares cache and image directories

LINBO is the linuxmuster.net boot and imaging solution that allows:
- Network booting of client computers
- OS image deployment and management
- Automated system installation and recovery
"""

import configparser
import datetime
import glob
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import backupCfg, enterPassword, getSetupValue, isValidPassword, \
    mySetupLogfile, modIni, printScript, readTextfile, setupComment, writeTextfile
from linuxmuster_base7.setup.helpers import DEFAULT_LINBO_IP

logfile = mySetupLogfile(__file__)

# read INIFILE, get schoolname
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    serverip = getSetupValue('serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# test adminpw
try:
    adminpw = getSetupValue('adminpw')
except Exception as error:
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
    subprocess.run(['chmod', '600', configfile], shell=False)
    # enable rsync service
    subprocess.run(['systemctl', '-q', 'enable', 'rsync.service'], shell=False)
    # restart rsync service
    subprocess.run(['service', 'rsync', 'stop'], shell=False)
    subprocess.run(['service', 'rsync', 'start'], shell=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
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
            DEFAULT_LINBO_IP, serverip), 'w')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# linbo-torrent service
msg = 'Activating linbo-torrent service '
printScript(msg, '', False, False, True)
try:
    subprocess.run(['systemctl', '-q', 'enable', 'opentracker'], shell=False)
    subprocess.run(['systemctl', '-q', 'enable', 'linbo-torrent'], shell=False)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# linbofs update
msg = 'Reconfiguring linbo (forking to background) '
printScript(msg, '', False, False, True)
try:
    for keyfile in glob.glob(environment.SYSDIR + '/linbo/*key*'):
        if os.path.isfile(keyfile):
            os.unlink(keyfile)
    # Run dpkg-reconfigure in background with output redirected to logfile
    with open(logfile, 'a') as log:
        log.write('-' * 78 + '\n')
        log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
        log.write('#### dpkg-reconfigure linuxmuster-linbo7 (background) ####\n')
        log.flush()
        subprocess.Popen(['dpkg-reconfigure', 'linuxmuster-linbo7'],
                        stdout=log, stderr=subprocess.STDOUT,
                        start_new_session=True)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
