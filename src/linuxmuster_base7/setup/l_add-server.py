#!/usr/bin/python3
#
# add additional servers to devices.csv
# thomas@linuxmuster.net
# 20251114
#

"""
Setup module l_add-server: Register main server and firewall in devices.csv.

This module:
- Reads server and firewall IP addresses from setup configuration
- Obtains MAC addresses for each device (from hardware, ARP cache, or generates random)
- Creates or updates device entries in devices.csv
- Marks devices as type 'addc' (main server) or 'server' (additional servers)

MAC address discovery priority:
1. Main server: Read from local hardware (getnode())
2. Firewall: Query ARP cache after ping
3. Fallback: Generate random MAC address if discovery fails
"""

import configparser
import datetime
import os
import random
import re
import subprocess
import sys
from subprocess import Popen, PIPE
from uuid import getnode

sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import getSetupValue, isValidHostIpv4, isValidMac, mySetupLogfile, \
    printScript, readTextfile, writeTextfile
from linuxmuster_base7.setup.helpers import runWithLog

logfile = mySetupLogfile(__file__)


# Read setup configuration and current devices.csv
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
try:
    firewallip = getSetupValue('firewallip')
    servername = getSetupValue('servername')
    serverip = getSetupValue('serverip')
    rc, devices = readTextfile(environment.WIMPORTDATA)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)


def getRandomMac(devices):
    """
    Generate a random MAC address that doesn't conflict with existing devices.

    Args:
        devices: Current devices.csv content to check for conflicts

    Returns:
        Random MAC address in format 00:00:00:XX:XX:XX (uppercase)
    """
    while True:
        mac = "00:00:00:%02x:%02x:%02x" % (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
            )
        if not ';' + mac.upper() + ';' in devices:
            break
    return mac.upper()


def getMacFromArp(ip):
    """
    Retrieve MAC address from ARP cache by pinging device and querying arp table.

    Attempts up to 10 times with 15-second intervals between tries.
    Pings the device to ensure it's in the ARP cache before querying.

    Args:
        ip: IP address to query

    Returns:
        MAC address in uppercase format, or empty string if not found
    """
    mac = ''
    c = 0
    max = 10
    while not isValidMac(mac):
        if c > 0:
            import time
            time.sleep(15)
        # Ping device to populate ARP cache
        runWithLog(['ping', '-c2', ip], logfile, checkErrors=False)
        # Query ARP table
        pid = Popen(["arp", "-n", ip], stdout=PIPE)
        arpout = pid.communicate()[0]
        try:
            mac = re.search(
                r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", str(arpout)).groups()[0]
            if isValidMac(mac):
                return mac.upper()
        except Exception as error:
            mac = ''
        c = c + 1
        if c > max:
            break
    return mac


def addServerDevice(hostname, mac, ip, devices):
    """
    Add or update a server device entry in devices.csv format.

    Creates a device line with format:
    server;hostname;nopxe;MAC;IP;;;;type;;0;;;;SETUP;

    If device already exists (by hostname), updates the entry.
    Otherwise appends new entry.

    Args:
        hostname: Device hostname
        mac: MAC address
        ip: IP address
        devices: Current devices.csv content

    Returns:
        Updated devices.csv content
    """
    if mac == '':
        return devices
    # Main server is type 'addc' (Active Directory Domain Controller)
    # Other servers are type 'server'
    if ip == serverip:
        type = 'addc'
    else:
        type = 'server'
    line = 'server;' + hostname + ';nopxe;' + mac + \
        ';' + ip + ';;;;' + type + ';;0;;;;SETUP;'
    # Update existing entry if hostname found
    if ';' + hostname + ';' in devices:
        devices = '\n' + devices + '\n'
        devices = re.sub(r'\n.+?;' + hostname + ';.+?\n',
                         '\n' + line + '\n', devices)
        devices = devices[1:-1]
    # Otherwise append new entry
    else:
        if devices[-1] != '\n':
            line = '\n' + line
        else:
            line = line + '\n'
        devices = devices + line
    return devices


# Build list of devices to register (server and firewall)
device_array = []
device_array.append((servername, serverip))  # Main server
device_array.append(('firewall', firewallip))  # Firewall appliance

# Process each device: discover MAC and create devices.csv entry
printScript('Creating device entries for:')
for item in device_array:
    hostname = item[0]
    ip = item[1]
    msg = '* ' + hostname + ' '
    printScript(msg, '', False, False, True)

    # Obtain MAC address using appropriate method for each device
    if ip == serverip:
        # Main server: get MAC from local hardware
        h = iter(hex(getnode())[2:].zfill(12))
        mac = ":".join(i + next(h) for i in h)
    else:
        # Other devices: query ARP cache
        mac = getMacFromArp(ip)

    # Fallback to random MAC if discovery failed
    if mac == '':
        mac = getRandomMac(devices)

    # Add or update device entry in devices.csv
    devices = addServerDevice(hostname, mac, ip, devices)
    if rc == False:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    else:
        printScript(' ' + ip + ' ' + mac, '', True, True, False, len(msg))

# Write updated devices.csv file
if not writeTextfile(environment.WIMPORTDATA, devices, 'w'):
    sys.exit(1)
