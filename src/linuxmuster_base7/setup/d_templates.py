#!/usr/bin/python3
#
# process config templates
# thomas@linuxmuster.net
# 20250910
#

import configparser
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import datetime
import os
import subprocess
import sys

from linuxmuster_base7.functions import backupCfg, getSetupValue, mySetupLogfile, printScript, readTextfile
from linuxmuster_base7.functions import replaceInFile, setupComment

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

# templates, whose corresponding configfiles must not be overwritten
do_not_overwrite = 'dhcpd.custom.conf'
# templates, whose corresponding configfiles must not be backed up
do_not_backup = ['interfaces.linuxmuster',
                 'dovecot.linuxmuster.conf', 'smb.conf']

printScript('Processing config templates:')
for f in os.listdir(environment.TPLDIR):
    source = environment.TPLDIR + '/' + f
    msg = '* ' + f + ' '
    printScript(msg, '', False, False, True)
    try:
        # read template file
        rc, filedata = readTextfile(source)
        # replace placeholders with values
        filedata = filedata.replace('@@bitmask@@', bitmask)
        filedata = filedata.replace('@@broadcast@@', broadcast)
        filedata = filedata.replace('@@dhcprange@@', dhcprange)
        filedata = filedata.replace('@@dhcprange1@@', dhcprange1)
        filedata = filedata.replace('@@dhcprange2@@', dhcprange2)
        filedata = filedata.replace('@@domainname@@', domainname)
        filedata = filedata.replace('@@firewallip@@', firewallip)
        filedata = filedata.replace('@@linbodir@@', linbodir)
        filedata = filedata.replace('@@netbiosname@@', netbiosname)
        filedata = filedata.replace('@@netmask@@', netmask)
        filedata = filedata.replace('@@network@@', network)
        filedata = filedata.replace('@@realm@@', realm)
        filedata = filedata.replace('@@sambadomain@@', sambadomain)
        filedata = filedata.replace('@@schoolname@@', schoolname)
        filedata = filedata.replace('@@servername@@', servername)
        filedata = filedata.replace('@@serverip@@', serverip)
        filedata = filedata.replace('@@ntpsockdir@@', environment.NTPSOCKDIR)
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
        if (f in do_not_overwrite and os.path.isfile(target)):
            printScript(' Success!', '', True, True, False, len(msg))
            continue
        # create target directory
        targetdir = os.path.dirname(target)
        if targetdir:
            result = subprocess.run(['mkdir', '-p', targetdir], capture_output=True, text=True, check=False)
            if logfile and (result.stdout or result.stderr):
                with open(logfile, 'a') as log:
                    log.write('-' * 78 + '\n')
                    log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
                    log.write('#### mkdir -p ' + targetdir + ' ####\n')
                    if result.stdout:
                        log.write(result.stdout)
                    if result.stderr:
                        log.write(result.stderr)
                    log.write('-' * 78 + '\n')
        # backup file
        if f not in do_not_backup:
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
    result = subprocess.run(['/usr/sbin/lmn-prepare', '-x', '-s', '-u', '-p', 'server',
                            '-f', firewallip, '-n', serverip + '/' + bitmask,
                            '-d', domainname, '-t', servername, '-r', serverip,
                            '-a', adminpw],
                           capture_output=True, text=True, check=False)
    if logfile:
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
            log.write('#### /usr/sbin/lmn-prepare -x -s -u -p server ... ####\n')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
    # remove adminpw from logfile
    replaceInFile(logfile, adminpw, '******')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# set server time
msg = 'Adjusting server time '
printScript(msg, '', False, False, True)
# Helper function to run command with logging
def run_with_log(cmd_list, cmd_desc):
    result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
    if logfile and (result.stdout or result.stderr):
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
            log.write('#### ' + cmd_desc + ' ####\n')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
    return result

run_with_log(['mkdir', '-p', environment.NTPSOCKDIR], 'mkdir -p ' + environment.NTPSOCKDIR)
run_with_log(['chgrp', 'ntp', environment.NTPSOCKDIR], 'chgrp ntp ' + environment.NTPSOCKDIR)
run_with_log(['chmod', '750', environment.NTPSOCKDIR], 'chmod 750 ' + environment.NTPSOCKDIR)
run_with_log(['timedatectl', 'set-ntp', 'false'], 'timedatectl set-ntp false')
run_with_log(['systemctl', 'stop', 'ntp'], 'systemctl stop ntp')
run_with_log(['ntpdate', 'pool.ntp.org'], 'ntpdate pool.ntp.org')
run_with_log(['systemctl', 'enable', 'ntp'], 'systemctl enable ntp')
run_with_log(['systemctl', 'start', 'ntp'], 'systemctl start ntp')
now = str(datetime.datetime.now()).split('.')[0]
printScript(' ' + now, '', True, True, False, len(msg))
