#!/usr/bin/python3
#
# functions.py
#
# thomas@linuxmuster.net
# 20250729
#

from subprocess import Popen, PIPE
from shutil import copyfile
from netaddr import IPNetwork, IPAddress
from ldap3 import Server, Connection
from IPy import IP
from contextlib import closing
import codecs
import configparser
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import csv
import datetime
import getpass
import json
import netifaces
import os
import paramiko
import random
import re
import requests
import shutil
import socket
import string
import subprocess
import time
import urllib3
import warnings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings(action='ignore', module='.*paramiko.*')


# append stdout to logfile
class tee(object):

    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()  # If you want the output to be visible immediately

    def flush(self):
        for f in self.files:
            f.flush()


# REMOVED: subProc() function - replaced with secure subprocess.run() calls throughout codebase
# This function was using shell=True which is vulnerable to command injection
# All calls have been converted to use subprocess.run() with array-based arguments


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


# print with or without linefeed
def printLf(msg, lf):
    if lf:
        print(msg)
    else:
        print(msg, end='', flush=True)


# print script output
def printScript(msg='', header='', lf=True, noleft=False, noright=False,
                offset=0):
    linelen = 78
    borderlen = 4
    border = '#' * borderlen
    sep = '-' * linelen
    if header == 'begin' or header == 'end':
        printLf(sep, lf)
        if msg == '':
            return True
        if header == 'begin':
            headermsg = 'started'
        else:
            headermsg = 'finished'
        now = datetime.datetime.now()
        msg = msg + ' ' + headermsg + ' at ' + str(now).split('.')[0]
    if not noleft:
        line = border + ' ' + msg
    else:
        line = msg
    if not noright:
        padding = linelen - len(msg) - borderlen * 2 - 2 - offset
        if noleft:
            line = '.' * padding + msg + ' ' + border
        else:
            line = line + ' ' * padding + ' ' + border
    printLf(line, lf)
    if header == 'begin' or header == 'end':
        printLf(sep, lf)


# get key value from setup.ini
def getSetupValue(keyname):
    setupini = environment.SETUPINI
    try:
        setup = configparser.RawConfigParser(delimiters=('='))
        setup.read(setupini)
        rc = setup.get('setup', keyname)
        if rc == 'False':
            rc = False
        elif rc == 'True':
            rc = True
    except Exception as error:
        print(error)
        return ''
    return rc


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


# return grub name of partition's device name
def getGrubPart(partition):
    try:
        partition = partition.replace('/dev/', '')
        if re.findall(r'[hsv]d[a-z]', partition):
            partnr = re.sub(r'[hsv]d[a-z]', '', partition)
            hdchar = re.search(r'[hsv]d(.+?)[0-9]', partition).group(1)
            hdnr = str(ord(hdchar) - 97)
        elif re.findall(r'xvd[a-z]', partition):
            partnr = re.sub(r'xvd[a-z]', '', partition)
            hdchar = re.search(r'xvd(.+?)[0-9]', partition).group(1)
            hdnr = str(ord(hdchar) - 97)
        elif re.findall(r'disk[0-9]p', partition):
            partnr = re.sub(r'disk[0-9]p', '', partition)
            hdnr = re.search(r'disk(.+?)p[0-9]', partition).group(1)
        elif re.findall(r'mmcblk[0-9]p', partition):
            partnr = re.sub(r'mmcblk[0-9]p', '', partition)
            hdnr = re.search(r'mmcblk(.+?)p[0-9]', partition).group(1)
        elif re.findall(r'nvme0n[0-9]p', partition):
            partnr = re.sub(r'nvme0n[0-9]p', '', partition)
            hdnr = re.search(r'nvme0n(.+?)p[0-9]', partition).group(1)
            hdnr = str(int(hdnr) - 1)
        else:
            return None
    except Exception as error:
        print(error)
        return None
    # return grub partition designation
    grubpart = '(hd' + hdnr + ',' + partnr + ')'
    return grubpart


# return grub ostype
def getGrubOstype(osname):
    osname = osname.lower()
    if 'windows 10' in osname:
        return 'win10'
    if 'windows' in osname:
        return 'win'
    if 'mint' in osname:
        return 'linuxmint'
    ostype_list = ['win10', 'win', 'kubuntu', 'lubuntu', 'xubuntu', 'ubuntu',
                   'centos', 'arch', 'linuxmint', 'fedora', 'gentoo', 'debian',
                   'opensuse', 'suse', 'linux']
    for ostype in ostype_list:
        if ostype in osname:
            return ostype
    return 'unknown'


# concatenate files safely without shell injection risk
def catFiles(filelist, outfile):
    """
    Concatenate multiple files into a single output file.

    Uses binary mode to preserve file contents exactly (important for certificates).
    Avoids shell injection by using native Python file operations instead of subprocess.

    Args:
        filelist: List of file paths to concatenate
        outfile: Output file path where concatenated content will be written
    """
    import shutil
    with open(outfile, 'wb') as out:
        for filepath in filelist:
            with open(filepath, 'rb') as infile:
                shutil.copyfileobj(infile, out)


# return content of text file
def readTextfile(tfile):
    if not os.path.isfile(tfile):
        return False, None
    try:
        infile = codecs.open(tfile, 'r', encoding='utf-8', errors='ignore')
        content = infile.read()
        infile.close()
        return True, content
    except Exception as error:
        print(error)
        return False, None


# write textfile
def writeTextfile(tfile, content, flag):
    try:
        outfile = open(tfile, flag)
        outfile.write(content)
        outfile.close()
        return True
    except Exception as error:
        print(error)
        return False


# replace string in file
def replaceInFile(tfile, search, replace):
    rc = False
    try:
        bakfile = tfile + '.bak'
        copyfile(tfile, bakfile)
        rc, content = readTextfile(tfile)
        rc = writeTextfile(tfile, content.replace(search, replace), 'w')
    except Exception as error:
        print(error)
        if os.path.isfile(bakfile):
            copyfile(bakfile, tfile)
    if os.path.isfile(bakfile):
        os.unlink(bakfile)
    return rc


# modify and write ini file
def modIni(inifile, section, option, value):
    try:
        i = configparser.RawConfigParser(delimiters=('='))
        if not os.path.isfile(inifile):
            # create inifile
            writeTextfile(inifile, '[' + section + ']\n', 'w')
        i.read(inifile)
        i.set(section, option, value)
        with open(inifile, 'w') as outfile:
            i.write(outfile)
        return True
    except Exception as error:
        print(error)
        return False


# return my setup logfile path
def mySetupLogfile(fpath):
    myname = os.path.splitext(os.path.basename(fpath))[0].split('_')[1]
    logfile = environment.LOGDIR + '/setup.' + myname + '.log'
    return logfile


# wait for firewall to come up, after timeout seconds loop will be canceled
def waitForFw(timeout=300, wait=0):
    printScript('Waiting for opnsense to come up')
    firewallip = getSetupValue('firewallip')
    time.sleep(wait)
    count = 0
    while True:
        if count > timeout:
            # cancel if it lasts longer than timeout
            printScript('Timeout!')
            return False
        if sshExec(firewallip, 'exit'):
            return True
        else:
            count = count + 2
            time.sleep(2)


# firewall api get request
def firewallApi(request, path, data=''):
    domainname = getSetupValue('domainname')
    fwapi = configparser.RawConfigParser(delimiters=('='))
    fwapi.read(environment.FWAPIKEYS)
    apikey = fwapi.get('api', 'key')
    apisecret = fwapi.get('api', 'secret')
    headers = {'content-type': 'application/json'}
    url = 'https://firewall.' + domainname + '/api' + path
    if request == 'get':
        req = requests.get(url, auth=(apikey, apisecret), verify=False)
    elif request == 'post' and data == '':
        req = requests.post(url, auth=(apikey, apisecret), verify=False)
    elif request == 'post' and data != '':
        req = requests.post(url, data=data, auth=(
            apikey, apisecret), headers=headers, verify=False)
    else:
        return None
    # get response
    if req.status_code == 200:
        res = json.loads(req.text)
        return res
    else:
        printScript('Connection / Authentication issue, response received:')
        print(req.text)
        return None


def encodeCertToBase64(certpath, outpath=None):
    """
    Encode certificate file to base64 format (for OPNsense config.xml).

    Args:
        certpath: Path to certificate file to encode
        outpath: Optional output path (defaults to certpath + '.b64')

    Returns:
        True on success, False on failure
    """
    if outpath is None:
        outpath = certpath + '.b64'
    try:
        with open(outpath, 'wb') as f:
            subprocess.run(['base64', '-w0', certpath], stdout=f, check=True)
        return True
    except Exception:
        return False


def renewCaCertificate(cacert_subject, days, logfile=None):
    """
    Renew CA certificate using password-protected CA key.

    Args:
        cacert_subject: OpenSSL subject string for CA certificate
        days: Certificate validity in days
        logfile: Optional path to log file

    Returns:
        True on success, False on failure
    """
    try:
        # Read CA key password
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        cakeypw = cakeypw.strip()

        # Renew CA certificate
        if logfile:
            with open(logfile, 'a') as log:
                subprocess.run(['openssl', 'req', '-batch', '-x509', cacert_subject, '-new', '-nodes',
                              '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                              '-sha256', '-days', str(days), '-out', environment.CACERT],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'req', '-batch', '-x509', cacert_subject, '-new', '-nodes',
                          '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                          '-sha256', '-days', str(days), '-out', environment.CACERT],
                         check=True, capture_output=True)

        # Convert to CRT format
        if logfile:
            with open(logfile, 'a') as log:
                subprocess.run(['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                              '-out', environment.CACERTCRT],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                          '-out', environment.CACERTCRT],
                         check=True, capture_output=True)

        return True
    except Exception:
        return False


def signCertificateWithCa(csrfile, certfile, days, cnffile, logfile=None):
    """
    Sign a certificate signing request (CSR) with the CA certificate.

    Args:
        csrfile: Path to CSR file
        certfile: Path where signed certificate will be written
        days: Certificate validity in days
        cnffile: Path to OpenSSL extension configuration file
        logfile: Optional path to log file

    Returns:
        True on success, False on failure
    """
    try:
        # Read CA key password
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        cakeypw = cakeypw.strip()

        # Sign certificate
        if logfile:
            with open(logfile, 'a') as log:
                subprocess.run(['openssl', 'x509', '-req', '-in', csrfile,
                              '-CA', environment.CACERT, '-passin', 'pass:' + cakeypw,
                              '-CAkey', environment.CAKEY, '-CAcreateserial',
                              '-out', certfile, '-sha256', '-days', str(days),
                              '-extfile', cnffile],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'x509', '-req', '-in', csrfile,
                          '-CA', environment.CACERT, '-passin', 'pass:' + cakeypw,
                          '-CAkey', environment.CAKEY, '-CAcreateserial',
                          '-out', certfile, '-sha256', '-days', str(days),
                          '-extfile', cnffile],
                         check=True, capture_output=True)

        return True
    except Exception:
        return False


def createCertificateChain(certfile, chainfile):
    """
    Create certificate chain by concatenating certificate and CA certificate.

    Args:
        certfile: Path to certificate file
        chainfile: Path where full chain will be written

    Returns:
        True on success, False on failure
    """
    try:
        catFiles([certfile, environment.CACERT], chainfile)
        return True
    except Exception:
        return False


def createCnfFromTemplate(cnf_tpl):
    """
    Create OpenSSL configuration file from template with variable replacement.

    Args:
        cnf_tpl: Path to configuration template file

    Returns:
        Path to created configuration file, or None on failure
    """
    try:
        # Read template file
        rc, filedata = readTextfile(cnf_tpl)

        # Replace placeholders with actual values
        replacements = {
            '@@domainname@@': getSetupValue('domainname'),
            '@@firewallip@@': getSetupValue('firewallip'),
            '@@realm@@': getSetupValue('realm'),
            '@@sambadomain@@': getSetupValue('sambadomain'),
            '@@schoolname@@': getSetupValue('schoolname'),
            '@@servername@@': getSetupValue('servername'),
            '@@serverip@@': getSetupValue('serverip'),
        }
        for placeholder, value in replacements.items():
            filedata = filedata.replace(placeholder, value)

        # Extract target path from first line
        firstline = filedata.split('\n')[0]
        cnf = firstline.partition(' ')[2]

        # Write configuration file
        with open(cnf, 'w') as outfile:
            outfile.write(filedata)

        return cnf
    except Exception:
        return None


# creates server cert
def createServerCert(item, days, logfile):
    domainname = getSetupValue('domainname')
    fqdn = item + '.' + domainname
    csrfile = environment.SSLDIR + '/' + item + '.csr'
    keyfile = environment.SSLDIR + '/' + item + '.key.pem'
    certfile = environment.SSLDIR + '/' + item + '.cert.pem'
    if item == 'firewall':
        cnffile = environment.SSLDIR + '/' + item + '_cert_ext.cnf'
    else:
        cnffile = environment.SSLDIR + '/server_cert_ext.cnf'
    fullchain = environment.SSLDIR + '/' + item + '.fullchain.pem'
    subj = '-subj /CN=' + fqdn + '/'
    shadays = ' -sha256 -days ' + days
    msg = 'Creating private ' + item + ' key & certificate '
    printScript(msg, '', False, False, True)
    try:
        # Generate RSA key
        result = subprocess.run(['openssl', 'genrsa', '-out', keyfile, '2048'],
                               capture_output=True, text=True, check=False)
        if logfile and (result.stdout or result.stderr):
            with open(logfile, 'a') as log:
                log.write('-' * 78 + '\n')
                log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
                log.write('#### openssl genrsa -out ' + keyfile + ' 2048 ####\n')
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write('-' * 78 + '\n')

        # Generate CSR
        result = subprocess.run(['openssl', 'req', '-batch', '-subj', '/CN=' + fqdn + '/',
                                '-new', '-key', keyfile, '-out', csrfile],
                               capture_output=True, text=True, check=False)
        if logfile and (result.stdout or result.stderr):
            with open(logfile, 'a') as log:
                log.write('-' * 78 + '\n')
                log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
                log.write('#### openssl req -batch ... ####\n')
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write('-' * 78 + '\n')

        # Sign certificate using shared function
        if not signCertificateWithCa(csrfile, certfile, days, cnffile, logfile):
            raise Exception('Failed to sign certificate')

        # Create certificate chain using shared function
        if not createCertificateChain(certfile, fullchain):
            raise Exception('Failed to create certificate chain')

        if item == 'firewall':
            # create base64 encoded version for opnsense's config.xml
            encodeCertToBase64(keyfile)
            encodeCertToBase64(certfile)
        if item == 'server':
            # cert links for cups on server
            subprocess.run(['ln', '-sf', certfile, '/etc/cups/ssl/server.crt'], check=False)
            subprocess.run(['ln', '-sf', keyfile, '/etc/cups/ssl/server.key'], check=False)
            subprocess.run(['service', 'cups', 'restart'], check=False)
        printScript('Success!', '', True, True, False, len(msg))
        return True
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        return False


# file transfer per scp
def scpTransfer(ip, mode, sourcefile, targetfile, secret='', sshuser='root'):
    """
    Transfer files via SCP (Secure Copy Protocol).

    Args:
        ip: Remote host IP address
        mode: 'get' (download) or 'put' (upload)
        sourcefile: Source file path
        targetfile: Target file path
        secret: SSH password (empty string for key-based auth)
        sshuser: SSH username (default: 'root')

    Returns:
        True on success, False on failure
    """
    if mode == 'get' or mode == 'put':
        printScript(mode + ' ' + ip + ' ' + sourcefile + ' ' + targetfile)
    else:
        print('Usage: scpTransfer(ip, mode, sourcefile, targetfile, secret, sshuser)')
        return 1
    # passwordless transfer using ssh keys
    if secret == '':
        # build ssh/scp command arguments as list (no shell injection risk)
        sshopts = ['-q', '-oNumberOfPasswordPrompts=0', '-oStrictHostkeyChecking=no']
        # test ssh connection first
        try:
            subprocess.run(['ssh'] + sshopts + ['-l', sshuser, ip, 'exit'],
                          check=True, capture_output=True)
        except subprocess.CalledProcessError as error:
            print(error)
            return False
        # file transfer with scp
        try:
            if mode == 'put':
                targetfile = sshuser + '@' + ip + ':' + targetfile
            if mode == 'get':
                sourcefile = sshuser + '@' + ip + ':' + sourcefile
            subprocess.run(['scp'] + sshopts + [sourcefile, targetfile],
                          check=True, capture_output=True)
        except subprocess.CalledProcessError as error:
            print(error)
            return False
    # transfer with password
    else:
        # test ssh connection
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=22, username=sshuser, password=secret)
        except Exception as error:
            print(error)
            return False
        # file upload
        try:
            ftp = ssh.open_sftp()
            if mode == 'put':
                ftp.put(sourcefile, targetfile)
            if mode == 'get':
                ftp.get(sourcefile, targetfile)
        except Exception as error:
            print(error)
            return False
        ftp.close()
        ssh.close()
    # return success
    return True


# download per sftp
def getSftp(ip, remotefile, localfile, secret='', sshuser='root'):
    rc = scpTransfer(ip, 'get', remotefile, localfile, secret, sshuser)
    return rc


# download firewall config.xml
def getFwConfig(firewallip, secret=''):
    printScript('Downloading firewall configuration:')
    rc = getSftp(firewallip, environment.FWCONFREMOTE,
                 environment.FWCONFLOCAL, secret)
    if rc:
        printScript('* Download finished successfully.')
    else:
        printScript('* Download failed!')
    return rc


# upload per sftp
def putSftp(ip, localfile, remotefile, secret='', sshuser='root'):
    rc = scpTransfer(ip, 'put', localfile, remotefile, secret, sshuser)
    return rc


# upload firewall config
def putFwConfig(firewallip, fwconf=environment.FWCONFREMOTE, secret=''):
    printScript('Uploading firewall configuration:')
    rc = putSftp(firewallip, environment.FWCONFLOCAL,
                 fwconf, secret)
    if rc:
        printScript('* Upload finished successfully.')
    else:
        printScript('* Upload failed!')
    return rc


# check firewall's major version
def checkFwMajorVer():
    try:
        firewallip = getSetupValue('firewallip')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(firewallip, port=22, username='root', password=environment.ROOTPW)
        stdin, stdout, stderr = ssh.exec_command('opnsense-version')
        output = stdout.readlines()[0]
        fver = output.split()[1]
        mver = int(fver.split('.')[0])
        if mver == environment.FWMAJORVER:
            return True
        else:
            print('Firewall version ' + fver + ' does not match ' + str(environment.FWMAJORVER) + '.*!')
            return False
    except Exception as error:
        print(error)
        return False


# execute ssh command
# note: paramiko key based connection is obviously broken in 18.04, so we use
#   ssh shell command
def sshExec(ip, cmd, secret=''):
    """
    Execute command on remote host via SSH.

    Args:
        ip: Remote host IP address
        cmd: Command to execute remotely
        secret: SSH password (empty string for key-based auth)

    Returns:
        True on success, False on failure
    """
    printScript('Executing ssh command on ' + ip + ':')
    printScript('* -> "' + cmd + '"')
    sshopts = ['-q', '-oNumberOfPasswordPrompts=0', '-oStrictHostkeyChecking=no']
    # first test connection
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if secret == '':
            # key-based auth: test connection with subprocess (no shell=True)
            subprocess.run(['ssh'] + sshopts + ['-l', 'root', ip, 'exit'],
                          check=True, stdout=subprocess.DEVNULL)
        else:
            # password auth: test connection with paramiko
            ssh.connect(ip, port=22, username='root', password=secret)
        printScript('* SSH connection successfully established.')
        if cmd == 'exit':
            return True
    except (subprocess.CalledProcessError, Exception) as error:
        print(error)
        return False
    # second execute command
    try:
        if secret != '':
            # password auth: use paramiko for command execution
            stdin, stdout, stderr = ssh.exec_command(cmd)
        else:
            # key-based auth: use subprocess with command as separate argument
            subprocess.run(['ssh'] + sshopts + ['-l', 'root', ip, cmd],
                          check=True, capture_output=True)
        printScript('* SSH command execution finished successfully.')
    except (subprocess.CalledProcessError, Exception) as error:
        print(error)
        return False
    if secret != '':
        ssh.close()
    return True


# return linbo start.conf as string and modified to be used as ini file
def readStartconf(startconf):
    rc, content = readTextfile(startconf)
    if not rc:
        return rc, None
    # [Partition] --> [Partition1]
    content = re.sub(
        r'\[[Pp][Aa][Rr][Tt][Ii][Tt][Ii][Oo][Nn]\]', '[Partition]', content)
    count = 1
    while '[Partition]' in content:
        content = content.replace(
            '[Partition]', '[Partition' + str(count) + ']', 1)
        count = count + 1
    # replace os sections to make them unique
    content = re.sub(r'\[[Oo][Ss]\]', '[OS]', content)
    count = 1
    while '[OS]' in content:
        content = content.replace('[OS]', '[OS' + str(count) + ']', 1)
        count = count + 1
    return True, content


# get global options from startconf
def getStartconfOption(startconf, section, option):
    rc, content = readStartconf(startconf)
    if not rc:
        return None
    try:
        # read in to configparser
        s = configparser.RawConfigParser(delimiters=('='), inline_comment_prefixes=('#', ';'))
        s.read_string(content)
        return s.get(section, option)
    except Exception as error:
        print(error)
        return None


# get partition label from start.conf
def getStartconfPartlabel(startconf, partnr):
    partnr = int(partnr)
    rc, content = readStartconf(startconf)
    if not rc:
        return ''
    count = 1
    for item in re.findall(r'\nLabel.*\n', content, re.IGNORECASE):
        if count == partnr:
            return item.split('#')[0].split('=')[1].strip()
        count = count + 1
    return ''


# get number of partition
def getStartconfPartnr(startconf, partition):
    rc, content = readStartconf(startconf)
    if not rc:
        return 0
    count = 1
    for item in re.findall(r'\nDev.*\n', content, re.IGNORECASE):
        if item.split('#')[0].split('=')[1].strip() == partition:
            return str(count)
        count = count + 1
    return 0


# write global options to startconf
def setGlobalStartconfOption(startconf, option, value):
    rc, content = readTextfile(startconf)
    if not rc:
        return rc
    # insert newline
    content = '\n' + content
    try:
        line = re.search(r'\n' + option + ' =.*\n',
                         content, re.IGNORECASE).group(0)
    except Exception:
        line = None
    if line is None:
        line = re.search(r'\n\[LINBO\].*\n', content, re.IGNORECASE).group(0)
        content = content.replace(line, line + option + ' = ' + value + '\n')
    else:
        content = content.replace(line, '\n' + option + ' = ' + value + '\n')
    # remove inserted newline
    content = content[1:]
    # write start.conf
    rc = writeTextfile(startconf, content, 'w')
    return rc


# return os values from linbo start.conf as list
def getStartconfOsValues(startconf):
    rc, content = readStartconf(startconf)
    if not rc:
        return None
    try:
        # read in to configparser
        s = configparser.RawConfigParser(delimiters=('='), inline_comment_prefixes=('#', ';'))
        s.read_string(content)
        count = 1
        oslists = {}
        while True:
            try:
                oslists[count] = []
                name = s.get('OS' + str(count), 'name').split('#')[0]
                if name != '':
                    name = name.strip()
                oslists[count].append(name)
                baseimage = s.get('OS' + str(count), 'baseimage').split('#')[0]
                if baseimage != '':
                    baseimage = baseimage.strip()
                oslists[count].append(baseimage)
                root = s.get('OS' + str(count), 'root').split('#')[0]
                if root != '':
                    root = root.strip()
                oslists[count].append(root)
                kernel = s.get('OS' + str(count), 'kernel').split('#')[0]
                if kernel != '':
                    kernel = kernel.strip()
                oslists[count].append(kernel)
                initrd = s.get('OS' + str(count), 'initrd').split('#')[0]
                if initrd != '':
                    initrd = initrd.strip()
                oslists[count].append(initrd)
                kappend = s.get('OS' + str(count), 'append').split('#')[0]
                if kappend != '':
                    kappend = kappend.strip()
                oslists[count].append(kappend)
                oslists[count].append(str(count))
                count = count + 1
            except Exception:
                break
        if oslists[1] == []:
            return None
        maxcount = count
        count = 1
        result = []
        while count < maxcount:
            result.append(oslists[count])
            count = count + 1
        return result
    except Exception as error:
        print(error)
        return None


def getLinboVersion():
    rc, content = readTextfile(environment.LINBOVERFILE)
    if not rc:
        return
    content = content.split(' ')[1]
    return content.split(':')[0]


def checkSocket(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(2)
        if sock.connect_ex((host, port)) == 0:
            return True
        else:
            return False


def hasNumbers(password):
    return any(char.isdigit() for char in password)


def randomPassword(size):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    while True:
        password = ''.join(random.choice(chars) for x in range(size))
        if hasNumbers(password) is True:
            break
    return password


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


def isValidPassword(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        7 characters length or more
        1 digit or 1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """
    # calculating the length
    length_error = len(password) < 7
    # searching for digits
    digit_error = re.search(r"\d", password) is None
    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None
    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None
    # no $ in pw
    unwanted_error = re.search(r"\$", password) is not None
    # searching for symbols
    if digit_error is True:
        digit_error = False
        symbol_error = re.search(r"[@!#%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None
    else:
        symbol_error = False
    # overall result
    password_ok = not (
        length_error or digit_error or uppercase_error or lowercase_error
        or symbol_error or unwanted_error
        )
    return password_ok


# enter password
def enterPassword(pwtype='the', validate=True, repeat=True):
    msg = '#### Enter ' + pwtype + ' password: '
    re_msg = '#### Please re-enter ' + pwtype + ' password: '
    while True:
        password = getpass.getpass(msg)
        if validate and not isValidPassword(password):
            printScript(
                'Weak password! A password is considered strong if it contains:')
            printScript(' * 7 characters length or more')
            printScript(' * 1 digit or 1 symbol or more')
            printScript(' * 1 uppercase letter or more')
            printScript(' * 1 lowercase letter or more')
            continue
        elif password == '' or password is None:
            continue
        if repeat:
            password_repeated = getpass.getpass(re_msg)
            if password != password_repeated:
                printScript('Passwords do not match!')
                continue
            else:
                break
        else:
            break
    return password


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


# return datetime string
def dtStr():
    return "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())


# return setup comment for modified configfiles
def setupComment():
    msg = '# modified by linuxmuster-setup at ' + dtStr() + '\n'
    return msg


# backup config file
def backupCfg(configfile):
    if not os.path.isfile(configfile):
        return False
    backupfile = configfile + '.' + dtStr()
    try:
        shutil.copy(configfile, backupfile)
    except Exception as error:
        print(error)
        return False
    return True
