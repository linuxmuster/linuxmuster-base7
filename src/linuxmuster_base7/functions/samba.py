#!/usr/bin/python3
#
# Filename     : samba.py
# Description  : Samba AD / samba-tool helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import datetime
import socket
import subprocess
from ldap3 import Server, Connection
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from .files import readTextfile, replaceInFile


# get basedn from domainname
def getBaseDN():
    domainname = socket.getfqdn().split('.', 1)[1]
    basedn = ''
    for item in domainname.split('.'):
        if basedn == '':
            basedn = 'DC=' + item
        else:
            basedn = basedn + ',DC=' + item
    return basedn


# AD query
def adSearch(search_filter, search_base=''):
    # get search parameters
    rc, bindsecret = readTextfile(environment.BINDUSERSECRET)
    basedn = getBaseDN()
    binduser = 'CN=global-binduser,OU=Management,OU=GLOBAL,' + basedn
    if search_base == '':
        search_base = basedn
    elif basedn not in search_base:
        search_base = search_base + ',' + basedn
    # make connection
    server = Server('localhost')
    conn = Connection(server, binduser, bindsecret, auto_bind=True)
    conn.search(search_base, search_filter)
    return conn.entries


# return True if dynamic ip device
def isDynamicIpDevice(name, school='default-school'):
    samacountname = name.upper() + '$'
    search_filter = '(&(objectClass=computer)(sAMAccountName=' + \
        samacountname + ')(sophomorixComputerIP=DHCP))'
    search_base = 'OU=Devices,OU=' + school + ',OU=SCHOOLS'
    res = adSearch(search_filter, search_base)
    if len(res) == 0:
        return False
    else:
        return True


# samba-tool
def sambaTool(options, logfile=None):
    subcmd = options.split(' ')[0]
    if subcmd == 'dns':
        adminuser = 'dns-admin'
        rc, adminpw = readTextfile(environment.DNSADMINSECRET)
    else:
        adminuser = 'administrator'
        rc, adminpw = readTextfile(environment.ADADMINSECRET)
    if not rc:
        return rc
    # Build command as list for secure execution
    cmd_list = ['samba-tool'] + options.split() + ['--username=' + adminuser, '--password=' + adminpw]
    # for debugging
    # printScript(' '.join(cmd_list))
    result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
    rc = result.returncode == 0 and not result.stderr
    # Log output if logfile provided
    if logfile is not None:
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
            log.write('#### samba-tool ' + options + ' --username=' + adminuser + ' --password=****** ####\n')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
        # mask password in logfile
        replaceInFile(logfile, adminpw, '******')
    return rc
