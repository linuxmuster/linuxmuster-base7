#!/usr/bin/python3
#
#  create web proxy sso keytab
# thomas@linuxmuster.net
# 20200309
#

import getopt
import sys

from functions import dtStr
from functions import getSetupValue
from functions import firewallApi
from functions import sshExec


def usage():
    print('Usage: create-keytab.py [options]')
    print('Creates opnsense web proxy sso keytable.')
    print('If adminpw is omitted it tests only the existance of the key table.')
    print(' [options] may be:')
    print(' -a <adminpw>, --adminpw=<adminpw>: global-admin password')
    print(' -v,           --verbose          : verbose output')
    print(' -h,           --help             : print this help')


# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "a:hv", ["adminpw=", "help", "verbose"])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err)  # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

verbose = False
adminpw = ''

# evaluate options
for o, a in opts:
    if o in ("-v", "--verbose"):
        verbose = True
    elif o in ("-a", "--adminpw"):
        adminpw = a
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"


print('### create-keytab.py ' + dtStr())

# get firewall ip from setupini
firewallip = getSetupValue('firewallip')


# create keytable
if adminpw != '':
    # reload relevant services
    for item in ['unbound', 'squid']:
        rc = sshExec(firewallip, 'pluginctl -s ' + item + ' restart')
        if not rc:
            sys.exit(1)
    # create keytab
    payload = '{"admin_login": "global-admin", "admin_password": "' + adminpw + '"}'
    apipath = '/proxysso/service/createkeytab'
    res = firewallApi('post', apipath, payload)
    if verbose:
        print(res)


# test success
keytabtest = 'No keytab'
apipath = '/proxysso/service/showkeytab'
res = firewallApi('get', apipath)
if verbose:
    print(res)
if keytabtest in str(res):
    rc = 1
    print('No keytab present :-(')
else:
    rc = 0
    print('Keytab exists :-)')


sys.exit(rc)
