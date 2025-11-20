#!/usr/bin/python3
#
# reset opnsense configuration to setup state
# thomas@linuxmuster.net
# 20251117
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
        if not createServerCert('firewall', logfile):
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
    """Delete old kerberos keytab and create new one.

    This function:
    1. Deletes the old keytab via firewall API
    2. Waits for the specified sleep time
    3. Creates a new keytab using create-keytab.py script

    Args:
        logfile: Path to log file for command output
        sleep: Number of seconds to wait between operations

    Returns:
        0 if successful, 1 if failed
    """
    # Step 1: Delete old keytab
    with open(logfile, 'a') as log:
        result = subprocess.run([environment.FWSHAREDIR + '/create-keytab.py', '-c'],
            stdout=log, stderr=subprocess.STDOUT, check=False)

    if result.returncode != 0:
        return 1

    printScript('Deleting old keytab.')
    apipath = '/proxysso/service/deletekeytab'
    res = firewallApi('get', apipath)
    print(res)

    printScript('Waiting ' + str(sleep) + ' seconds.')
    time.sleep(sleep)

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
    9. Recreate kerberos keytab

    Exit codes:
        0: Success
        1: Operation failed (SSH, cert, config reset, or keytab)
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

    # Step 10: Recreate kerberos keytab
    rc = recreateKeytab(logfile, sleep)

    sys.exit(rc)


if __name__ == '__main__':
    main()
