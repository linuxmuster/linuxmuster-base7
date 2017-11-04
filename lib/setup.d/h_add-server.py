#!/usr/bin/python3
#
# add additional servers to devices.csv
# thomas@linuxmuster.net
# 20170814
#

import configparser
import constants
import os
import re

from functions import printScript
from functions import readTextfile
from functions import writeTextfile
from functions import isValidHostIpv4
from functions import subProc
from subprocess import Popen, PIPE

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
    serverip = setup.get('setup', 'serverip')
    devicescsv = constants.WIMPORTDATA
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# get mac address from arp cache
def getMacFromArp(ip):
    try:
        subProc('ping -c2 ' + ip, logfile)
        pid = Popen(["arp", "-n", ip], stdout=PIPE)
        arpout = pid.communicate()[0]
        mac = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", str(arpout)).groups()[0]
    except:
        mac = ''
    return mac

# add devices entry
def addServerDevice(hostname, mac, ip):
    if mac == '':
        return False
    line = 'server;' + hostname + ';nopxe;' + mac + ';' + ip + ';;;;;1;0'
    rc, content = readTextfile(devicescsv)
    if rc == False:
        return rc
    if ';' + hostname + ';' in content:
        content = '\n' + content + '\n'
        content = re.sub(r'\n.+?;' + hostname + ';.+?\n', '\n' + line + '\n', content)
        content = content[1:-1]
    else:
        if content[-1] != '\n':
            line = '\n' + line
        else:
            line = line + '\n'
        content = content + line
    rc = writeTextfile(devicescsv, content, 'w')
    if rc == False:
        return rc

# collect array
device_array = []

# firewall
device_array.append(('firewall', firewallip))
# opsi
if isValidHostIpv4(opsiip):
    device_array.append(('opsi', opsiip))
# mail
if (isValidHostIpv4(mailip) and mailip != serverip):
    device_array.append(('mail', mailip))

# iterate
printScript('Creating device entries for:')
for item in device_array:
    hostname = item[0]
    ip = item[1]
    msg = '* ' + hostname + ' '
    printScript(msg, '', False, False, True)
    # get mac address
    mac = getMacFromArp(ip)
    # create devices.csv entry
    rc = addServerDevice(hostname, mac, ip)
    if rc == False:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    else:
        printScript(' ' + ip + ' ' + mac, '', True, True, False, len(msg))
