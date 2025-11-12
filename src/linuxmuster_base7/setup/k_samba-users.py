#!/usr/bin/python3
#
# create samba users & shares
# thomas@linuxmuster.net
# 20250729
#

import configparser
import datetime
import os
import shlex
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import mySetupLogfile, printScript, randomPassword, readTextfile
from linuxmuster_base7.functions import replaceInFile, sambaTool, writeTextfile

logfile = mySetupLogfile(__file__)

# Helper function to run command with logging
def run_with_log(cmd_string, logfile):
    """Execute command with output captured to logfile."""
    cmd_args = shlex.split(cmd_string)
    result = subprocess.run(cmd_args, capture_output=True, text=True, check=False, shell=False)
    if logfile and (result.stdout or result.stderr):
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
            log.write('#### ' + cmd_string + ' ####\n')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd_args, result.stdout, result.stderr)
    return result


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
    run_with_log('sophomorix-samba --backup-samba without-users', logfile)
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
run_with_log('sophomorix-postinst', logfile)

# create default-school share
schoolname = os.path.basename(environment.DEFAULTSCHOOL)
defaultpath = environment.SCHOOLSSHARE + '/' + schoolname
shareopts = 'writeable=y guest_ok=n'
shareoptsex = ['comment "Share for default-school"', '"hide unreadable" yes', '"msdfs root" no',
               '"strict allocate" yes', '"valid users" "' + sambadomain + '\\administrator, @' + sambadomain + '\\SCHOOLS"']
msg = 'Creating share for ' + schoolname + ' '
printScript(msg, '', False, False, True)
try:
    run_with_log('net conf addshare ' + schoolname + ' '
            + defaultpath + ' ' + shareopts, logfile)
    for item in shareoptsex:
        run_with_log('net conf setparm ' + schoolname + ' ' + item, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create global-admin
sophomorix_comment = "created by linuxmuster-setup"
msg = 'Creating samba account for global-admin '
printScript(msg, '', False, False, True)
try:
    run_with_log('sophomorix-admin --create-global-admin global-admin --password "'
            + adminpw + '"', logfile)
    run_with_log('sophomorix-user --user global-admin --comment "'
            + sophomorix_comment + '"', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create global bind user
msg = 'Creating samba account for global-binduser '
printScript(msg, '', False, False, True)
try:
    run_with_log('sophomorix-admin --create-global-binduser global-binduser --password "'
            + binduserpw + '"', logfile)
    run_with_log('sophomorix-user --user global-binduser --comment "'
            + sophomorix_comment + '"', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# no expiry for Administrator password
msg = 'No expiry for administrative passwords '
printScript(msg, '', False, False, True)
try:
    for i in ['Administrator', 'global-admin', 'sophomorix-admin', 'global-binduser']:
        sambaTool('user setexpiry ' + i + ' --noexpiry', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(error, '', True, True, False, len(msg))
    sys.exit(1)

# create default-school, no connection to ad
msg = 'Creating ou for ' + schoolname + ' '
printScript(msg, '', False, False, True)
try:
    run_with_log('sophomorix-school --create --school ' + schoolname, logfile)
    run_with_log('sophomorix-school --gpo-create ' + schoolname, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create pgmadmin for default-school
msg = 'Creating samba account for pgmadmin '
printScript(msg, '', False, False, True)
try:
    run_with_log('sophomorix-admin --create-school-admin pgmadmin --school '
            + schoolname + ' --password "' + adminpw + '"', logfile)
    run_with_log('sophomorix-user --user pgmadmin --comment "'
            + sophomorix_comment + '"', logfile)
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
    sambaTool('user create dns-admin ' + dnspw
              + ' --description="' + desc + '"', logfile)
    sambaTool('user setexpiry dns-admin --noexpiry', logfile)
    sambaTool('group addmembers DnsAdmins dns-admin', logfile)
    rc, writeTextfile(environment.DNSADMINSECRET, dnspw, 'w')
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
