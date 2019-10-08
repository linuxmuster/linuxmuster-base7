#!/usr/bin/python3
#
# functions.py
#
# thomas@linuxmuster.net
# 20191008
#

import codecs
import configparser
import constants
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

from contextlib import closing
from IPy import IP
from shutil import copyfile
from subprocess import Popen, PIPE

# append stdout to logfile
class tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush() # If you want the output to be visible immediately
    def flush(self) :
        for f in self.files:
            f.flush()

# invoke system commands
def subProc(cmd, logfile=None):
    try:
        rc = True
        p = Popen(cmd, shell=True, universal_newlines=True, stdout=PIPE, stderr=PIPE)
        output, errors = p.communicate()
        if p.returncode or errors:
            rc = False
        if logfile != None:
            l = open(logfile, 'a')
            l.write('-' * 78 + '\n')
            now = str(datetime.datetime.now()).split('.')[0]
            l.write('#### ' + now + ' ' * (68 - len(now)) + ' ####\n')
            l.write('#### ' + cmd + ' ' * (68 - len(cmd)) + ' ####\n')
            l.write(output)
            if rc == False:
                l.write(errors)
            l.write('-' * 78 + '\n')
            l.close()
        return rc
    except:
        return False

# samba-tool
def sambaTool(options):
    rc, adminpw = readTextfile(constants.ADADMINSECRET)
    if rc == False:
        return rc
    logfile = constants.LOGDIR + '/samba-tool.log'
    cmd = 'samba-tool ' + options + ' --username=Administrator --password=' + adminpw
    # for debugging
    #printScript(cmd)
    rc = subProc(cmd, logfile)
    return rc

# print with or without linefeed
def printLf(msg, lf):
    if lf == True:
        print(msg)
    else:
        print(msg, end='', flush=True)

# print script output
def printScript(msg='', header='', lf=True, noleft=False, noright=False, offset=0):
    linelen = 78
    borderlen = 4
    border = '#' * borderlen
    sep = '-' * linelen
    if header == 'begin' or header == 'end':
        printLf(sep, lf)
        if msg == '':
            return True
        if header == 'begin':
            headermsg = 'startet'
        else:
            headermsg = 'finished'
        now = datetime.datetime.now()
        msg = msg + ' ' + headermsg + ' at ' + str(now).split('.')[0]
    if noleft == False:
        line = border + ' ' + msg
    else:
        line = msg
    if noright == False:
        padding = linelen - len(msg) - borderlen * 2 - 2 - offset
        if noleft == True:
            line = '.' * padding + msg + ' ' + border
        else:
            line = line + ' ' * padding + ' ' + border
    printLf(line, lf)
    if header == 'begin' or header == 'end':
        printLf(sep, lf)

# get ip addresses from setup.init
def getFromSetup():
    setupini = constants.SETUPINI
    domainname = ''
    bitmask = ''
    serverip = ''
    firewallip = ''
    opsiip = ''
    dockerip = ''
    adminpw = ''
    try:
        setup = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
        setup.read(setupini)
        domainname = setup.get('setup', 'domainname')
        bitmask = setup.get('setup', 'bitmask')
        serverip = setup.get('setup', 'serverip')
        firewallip = setup.get('setup', 'firewallip')
        opsiip = setup.get('setup', 'opsiip')
        dockerip = setup.get('setup', 'dockerip')
        adminpw = setup.get('setup', 'adminpw')
    except:
        pass
    return domainname, bitmask, serverip, firewallip, opsiip, dockerip, adminpw

# establish pw less ssh connection to ip & port
def doSshLink(ip, port, secret):
    domainname, bitmask, serverip, firewallip, opsiip, dockerip, adminpw = getFromSetup()
    msg = '* Processing ssh link to host ' + ip + ' on port ' + str(port) + ':'
    printScript(msg)
    # test connection on ip and port
    msg = '  > Testing ssh connection '
    printScript(msg, '', False, False, True)
    if checkSocket(ip, port):
        printScript(' Open!', '', True, True, False, len(msg))
    else:
        printScript(' Closed!', '', True, True, False, len(msg))
        return False
    # establish ssh connection to ip on port
    msg = '  > Establishing ssh connection '
    printScript(msg, '', False, False, True)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, port=port, username='root', password=secret)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        return False
    # deploy public key to host
    msg = '  > Deploying public key '
    sshdir = '/root/.ssh'
    printScript(msg, '', False, False, True)
    try:
        ssh.exec_command('mkdir -p ' + sshdir)
        ssh.exec_command('chmod 700 ' + sshdir)
        ftp = ssh.open_sftp()
        ftp.put(sshdir + '/id_rsa.pub', sshdir + '/authorized_keys')
        ftp.close()
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        return False
    # deploy ssl cert & key to opsi or docker
    hostname = ''
    if ip == opsiip:
        hostname = 'opsi'
    elif ip == dockerip:
        hostname = 'docker'
    profile = ''
    if hostname != '':
        msg = '  > Deploying ssl certs & key '
        profile = ' -p ' + hostname
        keyfile = constants.SSLDIR + '/' + hostname + '.key.pem'
        certfile = constants.SSLDIR + '/' + hostname + '.cert.pem'
        printScript(msg, '', False, False, True)
        try:
            ssh.exec_command('mkdir -p ' + constants.SSLDIR)
            ftp = ssh.open_sftp()
            ftp.put(constants.CACERT, constants.CACERT)
            ftp.put(keyfile, keyfile)
            ftp.put(certfile, certfile)
            ftp.close()
            ssh.exec_command('chmod 640 ' + constants.SSLDIR + '/*.key.pem')
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            return False
    # close ssh connection
    ssh.close()
    # prepare host
    if serverip != '' and adminpw != '' and hostname != '':
        msg = '  > Preparing ' + hostname + ' '
        printScript(msg, '', False, False, True)
        try:
            sshcmd = 'ssh -oNumberOfPasswordPrompts=0 -oStrictHostKeyChecking=no -p ' + str(port) + ' ' + ip + ' '
            preparecmd = sshcmd + '/usr/sbin/linuxmuster-prepare -s -u -t ' + hostname + ' -r ' + serverip + ' -a "' + adminpw + '"' + profile + ' -n ' + ip + '/' + bitmask + ' -d ' + domainname + ' -f ' + firewallip
            rebootcmd = sshcmd + '/sbin/reboot'
            logfile = constants.LOGDIR + '/setup.ssh.' + hostname + '.log'
            subProc(preparecmd, logfile)
            knownhosts = '/root/.ssh/known_hosts'
            if os.path.isfile(knownhosts):
                cmd = 'ssh-keygen -f ' + knownhosts + ' -R ' + ip
                subProc(cmd, logfile)
            subProc(rebootcmd, logfile)
            printScript(' Success!', '', True, True, False, len(msg))
        except:
            printScript(' Failed!', '', True, True, False, len(msg))
            return False
    return True

# return grub name of partition's device name
def getGrubPart(partition, systemtype):
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
        elif re.findall(r'mmcblk[0-9]p', partition):
            partnr = re.sub(r'mmcblk[0-9]p', '', partition)
            hdnr = re.search(r'mmcblk(.+?)p[0-9]', partition).group(1)
        elif re.findall(r'nvme0n[0-9]p', partition):
            partnr = re.sub(r'nvme0n[0-9]p', '', partition)
            hdnr = re.search(r'nvme0n(.+?)p[0-9]', partition).group(1)
            hdnr = str(int(hdnr) - 1)
        else:
            return None
    except:
        return None
    # return grub partition designation
    grubpart = '(hd' + hdnr + ',' + partnr + ')'
    return grubpart

# return grub ostype
def getGrubOstype(osname):
    osname = osname.lower()
    ostype_list = ['windows', 'kubuntu', 'lubuntu', 'xubuntu', 'ubuntu', 'centos', 'arch', 'linuxmint', 'fedora', 'gentoo', 'debian', 'opensuse', 'suse', 'linux']
    for ostype in ostype_list:
         if ostype in osname:
             return ostype
    return 'unknown'

# return content of text file
def readTextfile(tfile):
    if not os.path.isfile(tfile):
        return False, None
    try:
        infile = codecs.open(tfile ,'r', encoding='utf-8', errors='ignore')
        content = infile.read()
        infile.close()
        return True, content
    except:
        print('Cannot read ' + tfile + '!')
        return False, None

# write textfile
def writeTextfile(tfile, content, flag):
    try:
        outfile = open(tfile, flag)
        outfile.write(content)
        outfile.close()
        return True
    except:
        print('Failed to write ' + tfile + '!')
        return False

# replace string in file
def replaceInFile(tfile, search, replace):
    rc = False
    try:
        bakfile = tfile + '.bak'
        copyfile(tfile, bakfile)
        rc, content = readTextfile(tfile)
        rc = writeTextfile(tfile, content.replace(search, replace), 'w')
    except:
        print('Failed to write ' + tfile + '!')
        if os.path.isfile(bakfile):
            copyfile(bakfile, tfile)
    if os.path.isfile(bakfile):
        os.unlink(bakfile)
    return rc

# modify and write ini file
def modIni(inifile, section, option, value):
    try:
        i = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
        if not os.path.isfile(inifile):
            # create inifile
            writeTextfile(inifile, '[' + section + ']\n', 'w')
        i.read(inifile)
        i.set(section, option, value)
        with open(inifile, 'w') as outfile:
            i.write(outfile)
        return True
    except:
        return False

# firewall api get request
def firewallApi(request, path, data=''):
    domainname, bitmask, serverip, firewallip, opsiip, dockerip, adminpw = getFromSetup()
    fwapi = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
    fwapi.read(constants.FWAPIKEYS)
    apikey = fwapi.get('api', 'key')
    apisecret = fwapi.get('api', 'secret')
    headers = {'content-type': 'application/json'}
    url = 'https://firewall.' + domainname + '/api' + path
    if request == 'get':
        req = requests.get(url, verify=constants.FWFULLCHAIN, auth=(apikey, apisecret))
    elif request == 'post' and data == '':
        req = requests.post(url, verify=constants.FWFULLCHAIN, auth=(apikey, apisecret))
    elif request == 'post' and data != '':
        req = requests.post(url, data=data, verify=constants.FWFULLCHAIN, auth=(apikey, apisecret), headers=headers)
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

# download per sftp
def getSftp(ip, remotefile, localfile, secret=''):
    # establish connection
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if secret !='':
            ssh.connect(ip, port=22, username='root', password=secret)
        else:
            ssh.connect(ip, port=22, username='root')
    except:
        return False
    # get file
    try:
        ftp = ssh.open_sftp()
        ftp.get(remotefile, localfile)
    except:
        return False
    ftp.close()
    ssh.close()
    return True

# download firewall config.xml
def getFwConfig(firewallip, secret=''):
    printScript('Downloading firewall configuration:')
    rc = getSftp(firewallip, constants.FWCONFREMOTE, constants.FWCONFLOCAL, secret)
    if rc:
        printScript('* Download finished successfully.')
    else:
        printScript('* Download failed!')
    return rc

# upload per sftp
def putSftp(ip, localfile, remotefile, secret=''):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if secret !='':
            ssh.connect(ip, port=22, username='root', password=secret)
        else:
            ssh.connect(ip, port=22, username='root')
    except:
        return False
    try:
        ftp = ssh.open_sftp()
        ftp.put(localfile, remotefile)
    except:
        return False
    ftp.close()
    ssh.close()
    return True

# upload firewall config
def putFwConfig(firewallip, secret=''):
    printScript('Uploading firewall configuration:')
    rc = putSftp(firewallip, constants.FWCONFLOCAL, constants.FWCONFREMOTE, secret)
    if rc:
        printScript('* Upload finished successfully.')
    else:
        printScript('* Upload failed!')
    return rc

# execute ssh command
def sshExec(ip, cmd, secret=''):
    printScript('Executing ssh command on ' + ip + ':')
    printScript('* -> "' + cmd + '"')
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if secret !='':
            ssh.connect(ip, port=22, username='root', password=secret)
        else:
            ssh.connect(ip, port=22, username='root')
        printScript('* SSH connection successfully established.')
    except:
        printScript('* Unable to establish a SSH connection!')
        return False
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        printScript('* Execution finished successfully.')
    except:
        printScript('* Unable to execute command!')
        return False
    ssh.close()
    return True

# return linbo start.conf as string and modified to be used as ini file
def readStartconf(startconf):
    rc, content = readTextfile(startconf)
    if rc == False:
        return rc, None
    # [Partition] --> [Partition1]
    content = re.sub(r'\[[Pp][Aa][Rr][Tt][Ii][Tt][Ii][Oo][Nn]\]', '[Partition]', content)
    count = 1
    while '[Partition]' in content:
        content = content.replace('[Partition]', '[Partition' + str(count) + ']', 1)
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
    if rc == False:
        return None
    try:
        # read in to configparser
        s = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
        s.read_string(content)
        return s.get(section, option)
    except:
        return None

# get partition label from start.conf
def getStartconfPartlabel(startconf, partnr):
    partnr = int(partnr)
    rc, content = readStartconf(startconf)
    if rc == False:
        return ""
    count = 1
    for item in re.findall(r'\nLabel.*\n', content, re.IGNORECASE):
        if count == partnr:
            return item.split('#')[0].split('=')[1].strip()
        count = count + 1
    return ""

# get number of partition
def getStartconfPartnr(startconf, partition):
    rc, content = readStartconf(startconf)
    if rc == False:
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
    if rc == False:
        return rc
    # insert newline
    content = '\n' + content
    try:
        line = re.search(r'\n' + option + ' =.*\n', content, re.IGNORECASE).group(0)
    except:
        line = None
    if line == None:
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
    if rc == False:
        return None
    try:
        # read in to configparser
        s = configparser.RawConfigParser(inline_comment_prefixes=('#', ';'))
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
            except:
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
    except:
        return None

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
      if hasNumbers(password) == True:
          break
  return password

def isValidMac(mac):
    try:
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower()):
            return True
        else:
            return False
    except:
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
    except:
        return False

def isValidDomainname(domainname):
    try:
        for label in domainname.split('.'):
            if not isValidHostname(label):
                return False
        return True
    except:
        return False

def isValidHostIpv4(ip):
    try:
        ipv4 = IP(ip)
        if not ipv4.version() == 4:
            return False
        ipv4str = IP(ipv4).strNormal(0)
        if (int(ipv4str.split('.')[0]) == 0 or int(ipv4str.split('.')[3]) == 0):
            return False
        c = 0
        for i in ipv4str.split('.'):
            c = c + 1
            if c == 1 and int(i) > 254:
                return False
            if c == 4 and int(i) > 254:
                return False
        return True
    except:
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
    except:
        print('getHostname(): Error reading file ' + devices + '!')
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
    # searching for symbols
    if digit_error == True:
        digit_error = False
        symbol_error = re.search(r"[!#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None
    else:
        symbol_error = False
    # overall result
    password_ok = not ( length_error or digit_error or uppercase_error or lowercase_error or symbol_error )
    return password_ok

# enter password
def enterPassword(pwtype='the', validate=True, repeat=True):
    msg = '#### Enter ' + pwtype + ' password: '
    re_msg = '#### Please re-enter ' + pwtype + ' password: '
    while True:
        password = getpass.getpass(msg)
        if validate == True and not isValidPassword(password):
            printScript('Weak password! A password is considered strong if it contains:')
            printScript(' * 7 characters length or more')
            printScript(' * 1 digit or 1 symbol or more')
            printScript(' * 1 uppercase letter or more')
            printScript(' * 1 lowercase letter or more')
            continue
        elif password == '' or password == None:
            continue
        if repeat == True:
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
            except:
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
    except:
        return False
    return True
