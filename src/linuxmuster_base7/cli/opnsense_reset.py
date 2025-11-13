#!/usr/bin/python3
#
# reset opnsense configuration to setup state
# thomas@linuxmuster.net
# 20251113
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


infotxt = 'Sets the firewall to the state after setup.\n\
Custom adjustments made since then are lost.\n\
Note: The firewall will be restarted during the process.'


def usage():
    print('Usage: linuxmuster-opnsense-reset [options]')
    print(infotxt)
    print(' [options] may be:')
    print(' -f, --force       : Force execution without asking for consent.')
    print(' -p, --pw=<secret> : Current firewall root password,')
    print('                     if it is omitted script will ask for it.')
    print(' -s, --sleep=<#>   : Sleep time in secs after firewall restart and before')
    print('                     keytab creation (default 10).')
    print(' -h, --help        : Print this help.')


def main():
    """Reset OPNsense firewall configuration to setup state."""
    # check first if firewall is skipped by setup
    skipfw = getSetupValue('skipfw')
    if skipfw:
        printScript('Firewall is skipped by setup!')
        sys.exit(0)

    # get cli args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "fhp:s:", ["force", "help", "pw=", "sleep="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    # evaluate options
    force = False
    adminpw = None
    sleep = 10
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

    logfile = environment.LOGDIR + '/opnsense-reset.log'
    now = str(datetime.datetime.now()).split('.')[0]
    printScript('linuxmuster-opnsense-reset ' + now)

    # security prompt
    if not force:
        print(infotxt)
        answer = input('Do you want to continue (YES)? ')
        if answer != 'YES':
            sys.exit(0)

    #  ask for password
    if adminpw is None:
        adminpw = enterPassword('the current firewall root', validate=False)

    # test ssh connection with provided password
    firewallip = getSetupValue('firewallip')
    if not sshExec(firewallip, 'exit', adminpw):
        sys.exit(1)

    # write password to temporary file
    if not writeTextfile('/tmp/linuxmuster-opnsense-reset', adminpw, 'w'):
        sys.exit(1)

    # create firewall cert if not there
    if not os.path.isfile(environment.SSLDIR + '/firewall.cert.pem'):
        if not createServerCert('firewall', logfile):
            sys.exit(1)

    # invoke firewall setup module
    try:
        importlib.import_module('linuxmuster_base7.setup.m_firewall')
        rc = 0
    except Exception as error:
        with open(logfile, 'a') as log:
            log.write(str(error) + '\n')
        rc = 1

    # wait for firewall
    try:
        waitForFw(wait=30)
    except Exception as error:
        print(error)
        sys.exit(1)

    printScript('Waiting ' + str(sleep) + ' seconds.')
    time.sleep(sleep)

    # delete old keytable
    with open(logfile, 'a') as log:
        result = subprocess.run([environment.FWSHAREDIR + '/create-keytab.py', '-c'],
            stdout=log, stderr=subprocess.STDOUT, check=False)
    rc = 0 if result.returncode == 0 else 1
    if rc == 0:
        printScript('Deleting old keytab.')
        apipath = '/proxysso/service/deletekeytab'
        res = firewallApi('get', apipath)
        print(res)

        printScript('Waiting ' + str(sleep) + ' seconds.')
        time.sleep(sleep)

    # create new keytab
    with open(logfile, 'a') as log:
        result = subprocess.run([environment.FWSHAREDIR + '/create-keytab.py'],
            stdout=log, stderr=subprocess.STDOUT, check=False)
    rc = 0 if result.returncode == 0 else 1
    if rc == 0:
        printScript('New kerberos key table has been successfully created.')
    else:
        printScript('Failed to create new kerberos key table. See opnsense-reset.log for details.')

    sys.exit(rc)


if __name__ == '__main__':
    main()
