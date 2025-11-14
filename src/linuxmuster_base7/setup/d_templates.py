#!/usr/bin/python3
#
# process config templates
# thomas@linuxmuster.net
# 20250910
#

import configparser
import datetime
import os
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import backupCfg, getSetupValue, mySetupLogfile, printScript, readTextfile
from linuxmuster_base7.functions import replaceInFile, setupComment
from linuxmuster_base7.setup.helpers import runWithLog, replaceTemplateVars
from linuxmuster_base7.setup.helpers import DO_NOT_OVERWRITE_FILES, DO_NOT_BACKUP_FILES

logfile = mySetupLogfile(__file__)

# read setup data
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    # read default values
    defaults = configparser.ConfigParser(delimiters=('='))
    defaults.read(environment.DEFAULTSINI)
    # read setup values
    adminpw = getSetupValue('adminpw')
    bitmask = getSetupValue('bitmask')
    broadcast = getSetupValue('broadcast')
    dhcprange = getSetupValue('dhcprange')
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    domainname = getSetupValue('domainname')
    firewallip = getSetupValue('firewallip')
    linbodir = environment.LINBODIR
    netbiosname = getSetupValue('netbiosname')
    netmask = getSetupValue('netmask')
    network = getSetupValue('network')
    realm = getSetupValue('realm')
    sambadomain = getSetupValue('sambadomain')
    schoolname = getSetupValue('schoolname')
    servername = getSetupValue('servername')
    serverip = getSetupValue('serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# Note: do_not_overwrite and do_not_backup constants are imported from helpers.py

printScript('Processing config templates:')
for f in os.listdir(environment.TPLDIR):
    source = environment.TPLDIR + '/' + f
    msg = '* ' + f + ' '
    printScript(msg, '', False, False, True)
    try:
        # read template file
        rc, filedata = readTextfile(source)
        # replace placeholders with values
        variables = {
            '@@bitmask@@': bitmask,
            '@@broadcast@@': broadcast,
            '@@dhcprange@@': dhcprange,
            '@@dhcprange1@@': dhcprange1,
            '@@dhcprange2@@': dhcprange2,
            '@@domainname@@': domainname,
            '@@firewallip@@': firewallip,
            '@@linbodir@@': linbodir,
            '@@netbiosname@@': netbiosname,
            '@@netmask@@': netmask,
            '@@network@@': network,
            '@@realm@@': realm,
            '@@sambadomain@@': sambadomain,
            '@@schoolname@@': schoolname,
            '@@servername@@': servername,
            '@@serverip@@': serverip,
            '@@ntpsockdir@@': environment.NTPSOCKDIR
        }
        filedata = replaceTemplateVars(filedata, variables)
        # get target path
        firstline = filedata.split('\n')[0]
        target = firstline.partition(' ')[2]
        # remove target path from shebang line, define target file permissions
        if '#!/bin/sh' in firstline or '#!/bin/bash' in firstline:
            filedata = filedata.replace(' ' + target, '\n# ' + target)
            operms = '755'
        elif 'sudoers.d' in target:
            operms = '400'
        else:
            operms = '644'
        # do not overwrite specified configfiles if they exist
        if (f in DO_NOT_OVERWRITE_FILES and os.path.isfile(target)):
            printScript(' Success!', '', True, True, False, len(msg))
            continue
        # create target directory
        targetdir = os.path.dirname(target)
        if targetdir:
            runWithLog(['mkdir', '-p', targetdir], logfile, checkErrors=False)
        # backup file
        if f not in DO_NOT_BACKUP_FILES:
            backupCfg(target)
        with open(target, 'w') as outfile:
            outfile.write(setupComment())
            outfile.write(filedata)
        subprocess.run(['chmod', operms, target], check=True)
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)

# server prepare update
msg = 'Server prepare update '
printScript(msg, '', False, False, True)
try:
    runWithLog(['/usr/sbin/lmn-prepare', '-x', '-s', '-u', '-p', 'server',
                '-f', firewallip, '-n', serverip + '/' + bitmask,
                '-d', domainname, '-t', servername, '-r', serverip,
                '-a', adminpw],
               logfile, checkErrors=False, maskSecrets=[adminpw])
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# set server time
msg = 'Adjusting server time '
printScript(msg, '', False, False, True)
runWithLog(['mkdir', '-p', environment.NTPSOCKDIR], logfile, checkErrors=False)
runWithLog(['chgrp', 'ntp', environment.NTPSOCKDIR], logfile, checkErrors=False)
runWithLog(['chmod', '750', environment.NTPSOCKDIR], logfile, checkErrors=False)
runWithLog(['timedatectl', 'set-ntp', 'false'], logfile, checkErrors=False)
runWithLog(['systemctl', 'stop', 'ntp'], logfile, checkErrors=False)
runWithLog(['ntpdate', 'pool.ntp.org'], logfile, checkErrors=False)
runWithLog(['systemctl', 'enable', 'ntp'], logfile, checkErrors=False)
runWithLog(['systemctl', 'start', 'ntp'], logfile, checkErrors=False)
now = str(datetime.datetime.now()).split('.')[0]
printScript(' ' + now, '', True, True, False, len(msg))
