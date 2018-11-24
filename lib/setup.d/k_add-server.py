#!/usr/bin/python3
#
# add additional servers to devices.csv
# thomas@linuxmuster.net
# 20181124
#

import configparser
import constants
import os
import random
import re
import sys

from functions import printScript
from functions import readTextfile
from functions import writeTextfile
from functions import isValidHostIpv4
from functions import subProc
from subprocess import Popen, PIPE
from uuid import getnode

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup.ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    firewallip = setup.get('setup', 'firewallip')
    opsiip = setup.get('setup', 'opsiip')
    mailip = setup.get('setup', 'mailip')
    dockerip = setup.get('setup', 'dockerip')
    servername = setup.get('setup', 'servername')
    serverip = setup.get('setup', 'serverip')
    rc, devices = readTextfile(constants.WIMPORTDATA)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get random mac address
def getRandomMac(devices):
    while True:
        mac = "00:00:00:%02x:%02x:%02x" % (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
            )
        if not ';' + mac.upper() + ';' in devices:
            break
    return mac.upper()

# get mac address from arp cache
def getMacFromArp(ip):
    mac = ''
    c = 0
    max = 10
    while mac == '':
        if c > 0:
            os.system('sleep 15')
        subProc('ping -c2 ' + ip, logfile)
        pid = Popen(["arp", "-n", ip], stdout=PIPE)
        arpout = ''
        arpout = pid.communicate()[0]
        if arpout != '':
            mac = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", str(arpout)).groups()[0]
            break
        c = c + 1
        if c > max:
            break
    if mac == '':
        return mac
    else:
        return mac.upper()

# add devices entry
def addServerDevice(hostname, mac, ip, devices):
    if mac == '':
        return devices
    line = 'server;' + hostname + ';nopxe;' + mac + ';' + ip + ';;;;server;;0;;;;SETUP;'
    if ';' + hostname + ';' in devices:
        devices = '\n' + devices + '\n'
        devices = re.sub(r'\n.+?;' + hostname + ';.+?\n', '\n' + line + '\n', devices)
        devices = devices[1:-1]
    else:
        if devices[-1] != '\n':
            line = '\n' + line
        else:
            line = line + '\n'
        devices = devices + line
    return devices

# collect array
device_array = []

# server
device_array.append((servername, serverip))
# firewall
device_array.append(('firewall', firewallip))
# opsi
if isValidHostIpv4(opsiip):
    device_array.append(('opsi', opsiip))
# docker
if isValidHostIpv4(dockerip):
    device_array.append(('docker', dockerip))

# iterate
printScript('Creating device entries for:')
for item in device_array:
    hostname = item[0]
    ip = item[1]
    msg = '* ' + hostname + ' '
    printScript(msg, '', False, False, True)
    # get mac address
    if ip == serverip:
        h = iter(hex(getnode())[2:].zfill(12))
        mac = ":".join(i + next(h) for i in h)
    else:
        mac = getMacFromArp(ip)
    if mac == '':
        mac = getRandomMac(devices)
    # create devices.csv entry
    devices = addServerDevice(hostname, mac, ip, devices)
    if rc == False:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    else:
        printScript(' ' + ip + ' ' + mac, '', True, True, False, len(msg))

# finally write devices.csv
if not writeTextfile(constants.WIMPORTDATA, devices, 'w'):
    sys.exit(1)
