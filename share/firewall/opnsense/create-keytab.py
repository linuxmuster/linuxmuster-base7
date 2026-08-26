#!/usr/bin/python3
#
# Filename     : create-keytab.py
# Description  : Create OPNsense web proxy SSO keytab
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260826
#

import getopt
import os
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import datetime, firewallApi, getSetupValue, printScript, readTextfile


# check first if firewall is skipped by setup
skipfw = getSetupValue('skipfw')
if skipfw:
    printScript('Firewall is skipped by setup!')
    sys.exit(0)


def restartFirewallService(firewallip, item):
    """Restart an OPNsense plugin service via pluginctl over ssh.

    Exits the script on failure, matching the previous inline behaviour.
    """
    printScript('Restarting ' + item)
    result = subprocess.run(['ssh', '-q', '-oBatchmode=yes', '-oStrictHostkeyChecking=no',
                            firewallip, 'pluginctl', '-s', item, 'restart'])
    if result.returncode != 0:
        sys.exit(1)


def fixSquidConfigOwnership(firewallip):
    """Fix group ownership of the templated squid config tree (#200).

    OPNsense's configd daemon applies a hardened umask (0o27) to itself
    (service/modules/daemonize.py). The template renderer that writes
    squid.conf and its pre-auth/post-auth/auth includes on the very first
    boot after installing os-squid creates each directory with a bare
    os.mkdir() - no explicit group - so it inherits root's own primary
    group "wheel" instead of "squid". But OPNsense's own squid rc.d script
    runs the squid master process directly as user/group "squid" from the
    start (squid_user/squid_group both default to "squid" - no root, no
    privilege drop), so it can't read the root:wheel 640/750 files/dirs
    configd just created for it: squid dies on boot with "FATAL: Unable to
    open configuration file: ... Permission denied".

    Confirmed live: this only reproduces on a genuinely fresh OPNsense
    install where /usr/local/etc/squid never existed before - most likely
    triggered by fwsetup.sh's `pkg install os-squid` itself, which renders
    the templates for the first time against the already-running (already
    umask-hardened) configd daemon, before the reboot that follows ever
    happens. A system upgraded from an older release already has this
    directory tree from back then (with the correct group), and upgrades
    never touch pre-existing files/directories - so the bug stays hidden
    there. A plain reboot on its own does not reproduce it either -
    confirmed live that a normal reboot leaves already-correct ownership
    alone, which is exactly why this needs to run once, right here, after
    fwsetup.sh's own reboot has completed.

    A plain chgrp (no chmod) is enough to fix it - the existing 640/750
    modes are correct as-is and must NOT be loosened to world-readable,
    since the pre-auth/post-auth includes carry the LDAP bind password in
    plain text. Verified live end-to-end (two full linuxmuster-opnsense-
    reset runs, plus an independent reboot afterwards) that this makes
    squid start reliably and stay that way.

    Safe to run unconditionally and repeatedly: a no-op wherever the
    ownership is already correct.
    """
    printScript('Fixing squid config directory ownership')
    result = subprocess.run(['ssh', '-q', '-oBatchmode=yes', '-oStrictHostkeyChecking=no',
                            firewallip, 'chgrp', '-R', 'squid', '/usr/local/etc/squid'])
    if result.returncode != 0:
        sys.exit(1)


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

    # fix squid's config directory ownership *before* even attempting to
    # restart it below, or the restart is a no-op against a still-broken
    # config on a fresh install's very first boot (#200)
    fixSquidConfigOwnership(firewallip)

    # reload relevant services
    for item in ['unbound', 'squid']:
        restartFirewallService(firewallip, item)

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

    # squid was restarted above *before* the keytab (and possibly the SPN
    # just added) existed - its Kerberos-negotiate helper needs a second
    # restart now that both are actually in place, or SSO auth silently
    # keeps failing until some unrelated later restart/reboot (#198)
    restartFirewallService(firewallip, 'squid')


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
