#!/usr/bin/python3
#
# process config templates
# thomas@linuxmuster.net
# 20251114
#

"""
Setup module d_templates: Process and deploy configuration file templates.

This module:
- Reads setup values from configuration
- Iterates through all template files in /usr/share/linuxmuster/templates/
- Replaces placeholder variables (@@servername@@, @@serverip@@, etc.) with actual values
- Extracts target path from first line of each template
- Creates target directories if needed
- Backs up existing files (unless in DO_NOT_BACKUP list)
- Skips overwriting certain files (if in DO_NOT_OVERWRITE list)
- Sets appropriate file permissions (755 for scripts, 400 for sudoers, 644 for others)
- Runs lmn-prepare to configure linuxmuster packages
- Synchronizes system time with NTP servers

Templates are text files with placeholders like @@variable@@ that get replaced
with actual configuration values during setup.
"""

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

# Read all setup configuration values needed for template processing
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    # Read default values from defaults.ini
    defaults = configparser.ConfigParser(delimiters=('='))
    defaults.read(environment.DEFAULTSINI)
    # Read computed setup values
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

# Process all template files from templates directory
# Note: DO_NOT_OVERWRITE_FILES and DO_NOT_BACKUP_FILES are imported from helpers.py
printScript('Processing config templates:')
for f in os.listdir(environment.TPLDIR):
    source = environment.TPLDIR + '/' + f
    msg = '* ' + f + ' '
    printScript(msg, '', False, False, True)
    try:
        # Read template file content
        rc, filedata = readTextfile(source)

        # Replace all placeholder variables with actual values
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

        # Extract target path from first line (shebang or comment)
        firstline = filedata.split('\n')[0]
        target = firstline.partition(' ')[2]

        # Determine file permissions based on file type
        # Shell scripts: 755 (executable), sudoers: 400 (read-only root), others: 644
        if '#!/bin/sh' in firstline or '#!/bin/bash' in firstline:
            filedata = filedata.replace(' ' + target, '\n# ' + target)
            operms = '755'
        elif 'sudoers.d' in target:
            operms = '400'
        else:
            operms = '644'

        # Skip overwriting if file exists and is in protection list
        if (f in DO_NOT_OVERWRITE_FILES and os.path.isfile(target)):
            printScript(' Success!', '', True, True, False, len(msg))
            continue

        # Create target directory if it doesn't exist
        targetdir = os.path.dirname(target)
        if targetdir:
            runWithLog(['mkdir', '-p', targetdir], logfile, checkErrors=False)

        # Backup existing file unless it's in no-backup list
        if f not in DO_NOT_BACKUP_FILES:
            backupCfg(target)

        # Write processed template to target location
        with open(target, 'w') as outfile:
            outfile.write(setupComment())
            outfile.write(filedata)
        subprocess.run(['chmod', operms, target], check=True)
        printScript(' Success!', '', True, True, False, len(msg))
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        sys.exit(1)

# Run lmn-prepare to configure linuxmuster packages with setup parameters
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

# Synchronize system time with NTP servers
# Disable systemd-timesyncd, use ntpd instead for better accuracy
msg = 'Adjusting server time '
printScript(msg, '', False, False, True)
runWithLog(['mkdir', '-p', environment.NTPSOCKDIR], logfile, checkErrors=False)
runWithLog(['chgrp', 'ntpsec', environment.NTPSOCKDIR], logfile, checkErrors=False)
runWithLog(['chmod', '750', environment.NTPSOCKDIR], logfile, checkErrors=False)
runWithLog(['timedatectl', 'set-ntp', 'false'], logfile, checkErrors=False)
runWithLog(['systemctl', 'stop', 'ntpsec'], logfile, checkErrors=False)
runWithLog(['ntpdate', 'pool.ntp.org'], logfile, checkErrors=False)  # One-time sync
runWithLog(['systemctl', 'enable', 'ntpsec'], logfile, checkErrors=False)
runWithLog(['systemctl', 'start', 'ntpsec'], logfile, checkErrors=False)  # Start continuous sync
now = str(datetime.datetime.now()).split('.')[0]
printScript(' ' + now, '', True, True, False, len(msg))
