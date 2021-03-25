#!/usr/bin/python3
#
# adds/updates/removes A DNS records
# thomas@linuxmuster.net
# 20210321
#

import socket
import sys

from functions import isDynamicIpDevice
from functions import isValidHostname
from functions import isValidHostIpv4
from functions import sambaTool

cmd = ''
ip = ''
hostname = ''

# get arguments
cmd, ip, hostname = sys.argv[1:]

# check arguments
if cmd not in ['add', 'delete']:
    sys.exit(1)
if not isValidHostIpv4(ip):
    sys.exit(1)
if not isValidHostname(hostname):
    sys.exit(1)

# no action for pxclient
if hostname.lower() == 'pxeclient':
    sys.exit(0)

# check if it is a dynamic ip device
if not isDynamicIpDevice(hostname):
    sys.exit(0)

# test if there are already valid dns records for this host
try:
    ip_resolved = socket.gethostbyname(hostname)
except:
    ip_resolved = ''
try:
    name_resolved = socket.gethostbyaddr(ip)[0].split('.')[0]
except:
    name_resolved = ''
if cmd == 'add' and ip == ip_resolved and hostname == name_resolved:
    print('DNS records for host ' + hostname + ' with ip ' + ip + ' are already up-to-date.')
    sys.exit(0)

# delete existing dns records if there are any
domainname = socket.getfqdn().split('.', 1)[1]
fqdn = hostname + '.' + domainname
for item in ip_resolved, ip:
    if item == '':
        continue
    if sambaTool('dns delete localhost ' + domainname + ' ' + hostname + ' A ' + item):
        print('Deleted A record for ' + fqdn + ' -> ' + item + '.')
    oc1, oc2, oc3, oc4 = item.split('.')
    zone = oc3 + '.' + oc2 + '.' + oc1 + '.in-addr.arpa'
    if sambaTool('dns delete localhost ' + zone + ' ' + oc4 + ' PTR ' + fqdn):
        print('Deleted PTR record for ' + item + ' -> ' + fqdn + '.')

# in case of deletion job is already done
if cmd == 'delete':
    sys.exit(0)

# add dns A record
try:
    sambaTool('dns add localhost ' + domainname + ' ' + hostname + ' A ' + ip)
    print('Added A record for ' + fqdn + '.')
except:
    print('Failed to add A record for ' + fqdn + '.')
    sys.exit(1)

# add dns zone if necessary
if not sambaTool('dns zoneinfo localhost ' + zone):
    try:
        sambaTool('dns zonecreate localhost ' + zone)
        print('Created dns zone ' + zone + '.')
    except:
        print('Failed to create zone ' + zone + '.')
        sys.exit(1)

# add dns PTR record
try:
    sambaTool('dns add localhost ' + zone + ' ' + oc4 + ' PTR ' + fqdn)
    print('Added PTR record for ' + ip + '.')
except:
    print('Failed to add PTR record for ' + ip + '.')
    sys.exit(1)
