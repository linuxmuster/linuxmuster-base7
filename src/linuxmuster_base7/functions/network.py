#!/usr/bin/python3
#
# Filename     : network.py
# Description  : Subnet/device CSV parsing, IP/hostname/MAC validation and
#                network interface helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import csv
import re
import socket
from contextlib import closing
from IPy import IP
from netaddr import IPNetwork, IPAddress
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import netifaces


# test if ip matches subnet
def ipMatchSubnet(ip, subnet):
    if ip == 'DHCP' and subnet == 'all':
        return True
    if ip == 'DHCP':
        return False
    try:
        if subnet == 'all':
            cidr_array = getSubnetArray('0')
        else:
            cidr_array = [[subnet]]
        for cidr in cidr_array:
            if IPAddress(ip) in IPNetwork(cidr[0]):
                return True
    except Exception as error:
        print(error)
    return False


# get ip's subnet
def getIpSubnet(ip):
    subnets = getSubnetArray('0')
    for item in subnets:
        subnet = item[0]
        if ipMatchSubnet(ip, subnet):
            return subnet


# get ip's broadcast address
def getIpBcAddress(ip):
    try:
        subnet = getIpSubnet(ip)
        if subnet is None:
            return
        net = IPNetwork(subnet)
        bcaddr = str(net.broadcast)
        return bcaddr
    except Exception as error:
        print(error)


# reads devices.csv and returns a list of devices arrays: [array1, array2, ...]
# fieldnrs: comma separated list of field nrs ('0,1,2,3,...') to be returned,
#   default is all fields were returned
# subnet filter: only hosts whose ip matches the specified subnet (CIDR) were
#   returned, if 'all' is specified all subnets defined insubnets.csv were
#   checked, if 'DHCP' is specified all dynamic ip hosts are returned
# pxeflag filter: comma separated list of flags ('0,1,2,3'), only hosts with
#   the specified pxeflags were returned
def readDevicesCsv(school='default-school'):
    """
    Read devices CSV file for specified school.

    Opens the appropriate devices.csv file based on school name and reads
    all rows. Skips rows that begin with non-alphanumeric characters
    (comments or empty lines).

    Args:
        school: School name (default: 'default-school')

    Returns:
        List of raw CSV rows (each row is a list of fields)

    Raises:
        IOError: If devices.csv file cannot be opened
    """
    # Determine CSV file path based on school
    if school == "default-school":
        csv_path = environment.SOPHOSYSDIR + "/default-school/devices.csv"
    else:
        csv_path = environment.SOPHOSYSDIR + "/" + school + "/" + school + ".devices.csv"

    # Read CSV file
    with open(csv_path, newline='') as infile:
        content = csv.reader(infile, delimiter=';', quoting=csv.QUOTE_NONE)
        rows = []
        for row in content:
            # Skip rows that begin with non-alphanumeric characters
            try:
                if row[0][0:1].isalnum():
                    rows.append(row)
            except (IndexError, Exception):
                continue
    return rows


def validateDeviceRow(row, school='default-school'):
    """
    Validate and parse a device row from devices.csv.

    Extracts device fields, applies hostname transformation for non-default
    schools, and validates hostname, MAC address, and IP address.

    Args:
        row: CSV row as list of fields
        school: School name for hostname transformation

    Returns:
        Tuple of (is_valid, device_dict) where:
        - is_valid: Boolean indicating if row is valid
        - device_dict: Dictionary with parsed fields (hostname, group, mac, ip, pxe, raw_row)
          or None if invalid
    """
    try:
        # Transform hostname for non-default schools (add school prefix)
        if school != "default-school":
            row = row.copy()  # Don't modify original
            row[1] = school + "-" + row[1]

        # Extract device fields from CSV columns
        hostname = row[1]
        group = row[2]
        mac = row[3]
        ip = row[4]
        pxe = row[10]

        # Validate hostname and MAC address
        if not isValidHostname(hostname) or not isValidMac(mac):
            return False, None

        # Validate IP address (must be valid IPv4 or 'DHCP')
        if not isValidHostIpv4(ip) and ip != 'DHCP':
            return False, None

        # Return validated device data
        device = {
            'hostname': hostname,
            'group': group,
            'mac': mac,
            'ip': ip,
            'pxe': pxe,
            'raw_row': row
        }
        return True, device

    except (IndexError, KeyError, Exception) as error:
        # Invalid row format or missing fields
        print(error)
        return False, None


def filterDevices(devices, subnet='', pxeflag=''):
    """
    Filter device list based on subnet and PXE flag criteria.

    Applies filtering rules:
    - subnet='DHCP': Only include devices with ip='DHCP'
    - subnet='x.x.x.x/y': Only include devices in specified subnet
    - pxeflag='flag1,flag2': Only include devices with matching PXE flags

    Args:
        devices: List of device dictionaries
        subnet: Subnet filter ('DHCP', IP/netmask, or empty for no filter)
        pxeflag: PXE flag filter (comma-separated values, empty for no filter)

    Returns:
        Filtered list of device dictionaries
    """
    filtered = []
    for device in devices:
        ip = device['ip']
        pxe = device['pxe']

        # Filter by subnet
        if subnet == 'DHCP':
            # Only include DHCP devices
            if ip != 'DHCP':
                continue
        elif subnet != '':
            # Only include devices in specified subnet
            if ip == 'DHCP' or not ipMatchSubnet(ip, subnet):
                continue

        # Filter by PXE flag
        if pxeflag != '':
            if pxe not in pxeflag.split(','):
                continue

        filtered.append(device)

    return filtered


def transformDeviceRow(device, fieldnrs=''):
    """
    Transform device dict to include only specified fields from raw CSV row.

    Args:
        device: Device dictionary with 'raw_row' field
        fieldnrs: Comma-separated field numbers to return (empty=all fields)

    Returns:
        List with selected fields from raw CSV row

    Examples:
        fieldnrs='' returns entire row
        fieldnrs='1,3,4' returns fields at positions 1, 3, and 4
    """
    raw_row = device['raw_row']

    # Return all fields if no specific fields requested
    if fieldnrs == '':
        return raw_row

    # Extract only requested field numbers
    result = []
    for field in fieldnrs.split(','):
        try:
            result.append(raw_row[int(field)])
        except (ValueError, IndexError):
            # Invalid field number, skip it
            continue

    return result


def getDevicesArray(fieldnrs='', subnet='', pxeflag='', school='default-school'):
    """
    Get filtered and validated device array from devices.csv.

    This function orchestrates the device reading, validation, filtering,
    and transformation process by calling specialized helper functions.

    Args:
        fieldnrs: Comma-separated field numbers to return (empty=all fields)
        subnet: Subnet filter ('DHCP', IP/netmask, or empty for no filter)
        pxeflag: PXE flag filter (comma-separated values, empty for no filter)
        school: School name (default: 'default-school')

    Returns:
        List of device rows matching criteria, with selected fields

    Example:
        # Get all devices
        devices = getDevicesArray()

        # Get DHCP devices, return only fields 1,3,4
        devices = getDevicesArray(fieldnrs='1,3,4', subnet='DHCP')

        # Get devices in subnet with PXE flags '1' or '3'
        devices = getDevicesArray(subnet='10.0.0.0/16', pxeflag='1,3')
    """
    # Read CSV file
    raw_rows = readDevicesCsv(school)

    # Validate and parse each row
    valid_devices = []
    for row in raw_rows:
        is_valid, device = validateDeviceRow(row, school)
        if is_valid:
            valid_devices.append(device)

    # Apply filters
    filtered_devices = filterDevices(valid_devices, subnet, pxeflag)

    # Transform to requested fields
    devices_array = []
    for device in filtered_devices:
        devices_array.append(transformDeviceRow(device, fieldnrs))

    return devices_array


# read subnets.csv and return subnet array
# fieldnrs: comma separated list of field nrs to be returned, default is all
# fields are returned
def getSubnetArray(fieldnrs=''):
    infile = open(environment.SUBNETSCSV, newline='')
    content = csv.reader(infile, delimiter=';', quoting=csv.QUOTE_NONE)
    subnet_array = []
    for row in content:
        # skip rows, which begin with non alphanumeric characters
        try:
            if not row[0][0:1].isalnum():
                continue
        except Exception:
            continue
        try:
            ipnet = row[0]
            router = row[1]
            if IPAddress(router) in IPNetwork(ipnet):
                # collect fields
                if fieldnrs == '':
                    row_res = row
                else:
                    row_res = []
                    for field in fieldnrs.split(','):
                        row_res.append(row[int(field)])
                subnet_array.append(row_res)
        except Exception as error:
            print(error)
            continue
    return subnet_array


def isValidMac(mac):
    try:
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower()):
            return True
        else:
            return False
    except Exception:
        return False


def isValidHostname(hostname):
    try:
        if (len(hostname) > 63 or hostname[0] == '-' or hostname[-1] == '-'):
            return False
        allowed = re.compile(r'[a-z0-9\-]*$', re.IGNORECASE)
        if allowed.match(hostname):
            return True
        else:
            return False
    except Exception:
        return False


def isValidDomainname(domainname):
    try:
        for label in domainname.split('.'):
            if not isValidHostname(label):
                return False
        return True
    except Exception:
        return False


def isValidHostIpv4(ip):
    try:
        ipv4 = IP(ip)
        if not ipv4.version() == 4:
            return False
        ipv4str = IP(ipv4).strNormal(0)
        if (int(ipv4str.split('.')[0]) == 0):
            return False
        c = 0
        for i in ipv4str.split('.'):
            c = c + 1
            if c == 1 and int(i) > 254:
                return False
            if c == 4 and int(i) > 254:
                return False
        return True
    except Exception:
        return False


# returns hostname and row from workstations file, search with ip, mac and hostname
def getHostname(devices, search):
    try:
        hostname = None
        hostrow = None
        f = open(devices, newline='')
        reader = csv.reader(f, delimiter=';', quoting=csv.QUOTE_NONE)
        for row in reader:
            # skip lines
            if not re.match(r'[a-zA-Z0-9]', row[0]):
                continue
            host = row[1]
            mac = row[3]
            ip = row[4]
            if search == ip or search.upper() == mac.upper() or search.lower() == host.lower():
                hostname = host.lower()
                hostrow = row
                break
        f.close()
    except Exception as error:
        print(error)
    return hostname, hostrow


# return detected network interfaces
def detectedInterfaces():
    iface_list = netifaces.interfaces()
    iface_list.remove('lo')
    iface_count = len(iface_list)
    if iface_count == 1:
        iface_default = iface_list[0]
    else:
        iface_default = ''
    return iface_list, iface_default


# return default network interface
def getDefaultIface():
    # first try to get a single interface
    iface_list, iface_default = detectedInterfaces()
    if iface_default != '':
        return iface_list, iface_default
    # second if more than one get it by default route
    route = "/proc/net/route"
    with open(route) as f:
        for line in f.readlines():
            try:
                iface, dest, _, flags, _, _, _, _, _, _, _, =  line.strip().split()
                if dest != '00000000' or not int(flags, 16) & 2:
                    continue
                return iface_list, iface
            except Exception:
                continue
    return iface_list, iface_default


def checkSocket(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(2)
        if sock.connect_ex((host, port)) == 0:
            return True
        else:
            return False
