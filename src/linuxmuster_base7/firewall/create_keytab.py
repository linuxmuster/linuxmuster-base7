#!/usr/bin/python3
#
# create web proxy sso keytab
# thomas@linuxmuster.net
# 20250422
#

import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import getopt
import os
import subprocess
import sys

from linuxmuster_base7.functions import datetime, firewallApi, getSetupValue, printScript, readTextfile


# check first if firewall is skipped by setup
skipfw = getSetupValue('skipfw')
if skipfw:
    printScript('Firewall is skipped by setup!')
    sys.exit(0)


def usage():
    print('Usage: create-keytab.py [options]')
    print('Creates opnsense web proxy sso keytable.')
    print('If adminpw is omitted saved administrator credentials are used.')
    print(' [options] may be:')
    print(' -a <adminpw>, --adminpw=<adminpw>: global-admin password (optional)')
    print(' -c,           --check            : check only the presence of keytable file')
    print(' -v,           --verbose          : be more verbose')
    print(' -h,           --help             : print this help')


# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "a:chv", ["adminpw=", "check", "help", "verbose"])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err)  # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

verbose = False
adminpw = None
adminlogin = 'global-admin'
check = False

# evaluate options
for o, a in opts:
    if o in ("-v", "--verbose"):
        verbose = True
    elif o in ("-a", "--adminpw"):
        adminpw = a
    elif o in ("-c", "--check"):
        check = True
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"


now = str(datetime.datetime.now()).split('.')[0]
printScript('create-keytab.py ' + now)


if not check:
    # get firewall ip from setupini
    firewallip = getSetupValue('firewallip')

    # get administrator credentials if global-admin password was not provided
    if adminpw is None:
        rc, adminpw = readTextfile(environment.ADADMINSECRET)
        adminlogin = 'administrator'

    # reload relevant services
    for item in ['unbound', 'squid']:
        printScript('Restarting ' + item)
        result = subprocess.run(['ssh', '-q', '-oBatchmode=yes', '-oStrictHostKeyChecking=accept-new',
                                firewallip, 'pluginctl', '-s', item, 'restart'])
        if result.returncode != 0:
            sys.exit(1)

    # create keytab
    payload = '{"admin_login": "' + adminlogin + '", "admin_password": "' + adminpw + '"}'
    apipath = '/proxysso/service/createkeytab'
    res = firewallApi('post', apipath, payload)
    if verbose:
        print(res)

    # set firewall spn if it does not exist yet
    entry = 'HTTP/firewall\n'
    output = subprocess.check_output(['samba-tool', 'spn', 'list', 'FIREWALL-K$']).decode('utf-8')
    if entry not in output:
        entry = entry.replace('\n', '')
        printScript('Adding servicePrincipalName ' + entry + ' for FIREWALL-K$')
        subprocess.run(['samba-tool', 'spn', 'add', entry, 'FIREWALL-K$'])


# check success
keytabtest = 'No keytab'
apipath = '/proxysso/service/showkeytab'
res = firewallApi('get', apipath)
if verbose:
    print(res)
if keytabtest in str(res):
    rc = 1
    printScript('Keytab is not present :-(')
else:
    rc = 0
    printScript('Keytab is present :-)')


sys.exit(rc)
