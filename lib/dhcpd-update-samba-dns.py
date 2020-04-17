#!/usr/bin/python3
#
# adds/updates/removes A DNS records
# thomas@linuxmuster.net
# 20200417
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

# check if ip has not changed or has to be updated
if cmd == 'add':
    try:
        ip_resolved = socket.gethostbyname(hostname)
        if ip_resolved == ip:
            print('IP for ' + hostname + ' has remained unchanged, doing nothing.')
            sys.exit(0)
        else:
            cmd = 'update'
            ip = ip_resolved + ' ' + ip
    except Exception as error:
        print(error)

# check if it is a dynamic ip device
if not isDynamicIpDevice(hostname):
    print(hostname + ' is no dynamic ip device, doing nothing.')
    sys.exit(0)

# print message
if cmd == 'add':
    print('Creating A record for ' + hostname + '.')
elif cmd == 'update':
    print('IP for ' + hostname + ' has changed, performing update.')
else:
    print("Deleting " + hostname + "'s A record.")

domainname = socket.getfqdn().split('.', 1)[1]

sambaTool('dns ' + cmd + ' localhost ' + domainname + ' ' + hostname + ' A ' + ip)
