#!/usr/bin/python3
#
# Filename     : opnsense_reset.py
# Description  : Reset OPNsense configuration to setup state
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260902
#

import environment
import getopt
import importlib
import os
import subprocess
import sys
import time

from linuxmuster_base7.functions import createServerCert, datetime, enterPassword, firewallApi, \
    getSetupValue, printScript, sshExec, writeTextfile, waitForFw
from linuxmuster_base7.setup.helpers import CERT_VALIDITY_DAYS, runWithLog


INFOTXT = 'Sets the firewall to the state after setup.\n\
Custom adjustments made since then are lost.\n\
Note: The firewall will be restarted during the process.'

# Default sleep time in seconds after firewall restart
DEFAULT_SLEEP = 10


def usage():
    """Print usage information and command-line options.

    Displays help text showing all available command-line options for
    resetting the OPNsense firewall configuration.
    """
    print('Usage: linuxmuster-opnsense-reset [options]')
    print(INFOTXT)
    print(' [options] may be:')
    print(' -f, --force       : Force execution without asking for consent.')
    print(' -p, --pw=<secret> : Current firewall root password,')
    print('                     if it is omitted script will ask for it.')
    print(' -s, --sleep=<#>   : Sleep time in secs after firewall restart and before')
    print('                     keytab creation (default 10).')
    print(' -h, --help        : Print this help.')


def parseArguments():
    """Parse and validate command-line arguments.

    Returns:
        Tuple of (force_flag, admin_password, sleep_time)
        - force_flag: Boolean indicating if user consent prompt should be skipped
        - admin_password: Firewall root password or None if not provided
        - sleep_time: Number of seconds to wait after firewall restart

    Exits:
        Exits with code 2 if invalid arguments are provided
    """
    try:
        opts, args = getopt.getopt(sys.argv[1:], "fhp:s:", ["force", "help", "pw=", "sleep="])
    except getopt.GetoptError as err:
        # Print error message (e.g., "option -a not recognized")
        print(err)
        usage()
        sys.exit(2)

    # Extract option values with defaults
    force = False
    adminpw = None
    sleep = DEFAULT_SLEEP

    for o, a in opts:
        if o in ("-f", "--force"):
            force = True
        elif o in ("-p", "--pw"):
            adminpw = a
        elif o in ("-s", "--sleep"):
            sleep = int(a)
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    return force, adminpw, sleep


def promptUserConsent():
    """Prompt user for explicit consent before proceeding.

    Displays warning message and requires user to type 'YES' to continue.
    This prevents accidental execution of potentially destructive operations.

    Exits:
        Exits with code 0 if user does not consent
    """
    print(INFOTXT)
    answer = input('Do you want to continue (YES)? ')
    if answer != 'YES':
        sys.exit(0)


def validateFirewallAccess(firewallip, adminpw):
    """Test SSH connection to firewall with provided credentials.

    Args:
        firewallip: IP address of the firewall
        adminpw: Root password for SSH authentication

    Returns:
        True if SSH connection successful

    Exits:
        Exits with code 1 if SSH connection fails
    """
    if not sshExec(firewallip, 'exit', adminpw):
        sys.exit(1)
    return True


def storePasswordTemporarily(adminpw):
    """Store firewall password in temporary file with secure permissions.

    This file is read by m_firewall.py to determine the current firewall password.
    The file is created with restrictive permissions (0o600 - owner read/write only)
    to prevent unauthorized access to the password.

    Args:
        adminpw: Firewall root password to store

    Returns:
        Path to the temporary file

    Exits:
        Exits with code 1 if file creation fails
    """
    tmpfile = '/tmp/linuxmuster-opnsense-reset'
    try:
        # Create file with restrictive permissions before writing sensitive data
        fd = os.open(tmpfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.write(fd, adminpw.encode('utf-8'))
        os.close(fd)
        return tmpfile
    except Exception as error:
        printScript(f'Failed to write password file: {error}')
        sys.exit(1)


def ensureFirewallCert(logfile):
    """Ensure firewall SSL certificate exists, create if missing.

    Args:
        logfile: Path to log file for error messages

    Exits:
        Exits with code 1 if certificate creation fails
    """
    cert_path = environment.SSLDIR + '/firewall.cert.pem'
    if not os.path.isfile(cert_path):
        printScript('Creating firewall SSL certificate...')
        if not createServerCert('firewall', str(CERT_VALIDITY_DAYS), logfile):
            sys.exit(1)


def resetFirewallConfig(logfile):
    """Invoke firewall setup module to reset configuration.

    Imports and executes the m_firewall.py setup module which
    performs the actual firewall configuration reset.

    Args:
        logfile: Path to log file for error messages

    Returns:
        0 if successful, 1 if failed
    """
    try:
        importlib.import_module('linuxmuster_base7.setup.m_firewall')
        return 0
    except Exception as error:
        with open(logfile, 'a') as log:
            log.write(str(error) + '\n')
        return 1


def recreateKeytab(logfile, sleep):
    """Delete old kerberos keytab (if any) and create a new one.

    This function:
    1. Checks whether an old keytab exists; deletes it via the firewall
       API and waits `sleep` seconds only if it does (#201) - a firewall
       that never had a keytab yet has nothing to delete or wait for
    2. Creates a new keytab using create-keytab.py script

    Args:
        logfile: Path to log file for command output
        sleep: Number of seconds to wait between operations

    Returns:
        0 if successful, 1 if failed
    """
    # Step 1: check whether an old keytab exists, and only try to delete it
    # if it does - "no keytab present" is the normal state on a firewall
    # that has never had one yet (a fresh install, or an earlier keytab
    # creation that never succeeded for some other reason), not a fatal
    # error. Aborting here instead of continuing straight to creation
    # permanently bricked opnsense-reset on such a firewall - it could
    # never get past this check to actually create the missing keytab.
    with open(logfile, 'a') as log:
        result = subprocess.run([environment.FWSHAREDIR + '/create-keytab.py', '-c'],
            stdout=log, stderr=subprocess.STDOUT, check=False)

    if result.returncode == 0:
        printScript('Deleting old keytab.')
        apipath = '/proxysso/service/deletekeytab'
        res = firewallApi('get', apipath)
        print(res)

        printScript('Waiting ' + str(sleep) + ' seconds.')
        time.sleep(sleep)
    else:
        printScript('No existing keytab found, creating a new one.')

    # Step 2: Create new keytab
    with open(logfile, 'a') as log:
        result = subprocess.run([environment.FWSHAREDIR + '/create-keytab.py'],
            stdout=log, stderr=subprocess.STDOUT, check=False)

    rc = 0 if result.returncode == 0 else 1
    if rc == 0:
        printScript('New kerberos key table has been successfully created.')
    else:
        printScript('Failed to create new kerberos key table. See opnsense-reset.log for details.')

    return rc


def reimportSubnets(logfile):
    """Re-run subnet import to restore what the config reset just wiped out.

    The uploaded config template (config.xml.tpl) hardcodes an empty
    <staticroutes/> and <filter/> section, so every run of m_firewall.py -
    triggered here by resetFirewallConfig() - wipes any LAN gateway's static
    routes and firewall pass rules for subnets other than the server's own
    (see /etc/linuxmuster/subnets.csv), along with their outbound NAT rules.
    The LAN gateway itself survives (the template has no <Gateways> section
    at all), so afterwards it points nowhere. linuxmuster-import-subnets
    already recreates gateway/routes/NAT idempotently from subnets.csv, so
    simply calling it again here repairs exactly that gap - found live when
    clients on an extra subnet could reach the firewall but not the internet
    after a reset.

    Args:
        logfile: Path to log file for command output

    Returns:
        0 if successful, 1 if failed
    """
    printScript('Re-importing subnets to restore firewall routes and NAT rules.')
    try:
        runWithLog(['linuxmuster-import-subnets'], logfile)
        return 0
    except Exception as error:
        printScript(f'Failed to re-import subnets: {error}')
        return 1


def main():
    """Main entry point for CLI tool.

    Orchestrates the complete OPNsense firewall reset workflow:
    1. Check if firewall is enabled in setup
    2. Parse command-line arguments
    3. Prompt for user consent (unless --force is used)
    4. Validate firewall access with SSH
    5. Store password temporarily for setup module
    6. Ensure firewall SSL certificate exists
    7. Reset firewall configuration via setup module
    8. Wait for firewall to come back online
    9. Wait for the firewall to stabilize
    10. Re-import subnets (restores gateway/routes/NAT wiped by the reset)
    11. Recreate kerberos keytab

    Exit codes:
        0: Success
        1: Operation failed (SSH, cert, config reset, subnet re-import, or keytab)
        2: Invalid command-line arguments
    """
    # Step 1: Check if firewall is enabled in setup configuration
    skipfw = getSetupValue('skipfw')
    if skipfw:
        printScript('Firewall is skipped by setup!')
        sys.exit(0)

    # Step 2: Parse command-line arguments
    force, adminpw, sleep = parseArguments()

    # Initialize logging
    logfile = environment.LOGDIR + '/opnsense-reset.log'
    now = str(datetime.datetime.now()).split('.')[0]
    printScript('linuxmuster-opnsense-reset ' + now)

    # Step 3: Prompt for user consent (unless --force flag is set)
    if not force:
        promptUserConsent()

    # Step 4: Get firewall password if not provided via command line
    if adminpw is None:
        adminpw = enterPassword('the current firewall root', validate=False)

    # Step 5: Validate SSH access to firewall
    firewallip = getSetupValue('firewallip')
    validateFirewallAccess(firewallip, adminpw)

    # Step 6: Store password temporarily for m_firewall.py to use
    storePasswordTemporarily(adminpw)

    # Step 7: Ensure firewall SSL certificate exists
    ensureFirewallCert(logfile)

    # Step 8: Reset firewall configuration
    rc = resetFirewallConfig(logfile)
    if rc != 0:
        sys.exit(rc)

    # Step 9: Wait for firewall to come back online
    try:
        waitForFw(wait=30)
    except Exception as error:
        print(error)
        sys.exit(1)

    # Give firewall additional time to stabilize
    printScript('Waiting ' + str(sleep) + ' seconds.')
    time.sleep(sleep)

    # Step 10: Re-import subnets to restore gateway/routes/NAT wiped by the reset
    rc_subnets = reimportSubnets(logfile)

    # Step 11: Recreate kerberos keytab
    rc_keytab = recreateKeytab(logfile, sleep)

    sys.exit(1 if rc_subnets != 0 or rc_keytab != 0 else 0)


if __name__ == '__main__':
    main()
