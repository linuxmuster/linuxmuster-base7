#!/usr/bin/python3
#
# functions.py
#
# thomas@linuxmuster.net
# 20170211
#

import configparser
import datetime
import getpass
import netifaces
import os
import paramiko
import re
import random
import shutil
import socket
import string

from contextlib import closing
from IPy import IP
from subprocess import Popen, PIPE, STDOUT

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

def subProc(cmd, logfile=None):
    try:
        if logfile != None:
            l = open(logfile, 'a')
            l.write('-' * 78 + '\n')
            now = str(datetime.datetime.now()).split('.')[0]
            l.write('#### ' + now + ' ' * (68 - len(now)) + ' ####\n')
            l.write('#### ' + cmd + ' ' * (68 - len(cmd)) + ' ####\n')
            l.write('-' * 78 + '\n')
            l.flush()
            p = Popen(cmd, shell=True, universal_newlines=True, stdout=l, stderr=STDOUT)
        else:
            p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        p.wait()
        if logfile != None:
            l.close()
        return True
    except:
        return False

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

# establish pw less ssh connection to ip & port
def doSshLink(ip, port, secret):
    msg = '* Processing ssh link to host ' + ip + ' on port ' + str(port) + ':'
    printScript(msg)
    # test connection on ip and port
    msg = '  > Testing connection '
    printScript(msg, '', False, False, True)
    if checkSocket(ip, port):
        printScript(' Open!', '', True, True, False, len(msg))
    else:
        printScript(' Closed!', '', True, True, False, len(msg))
        return False
    # establish ssh connection to ip on port
    msg = '  > Establishing connection '
    printScript(msg, '', False, False, True)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(ip, port=port, username='root', password=secret)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        return False
    # create .ssh dir on remote host
    sshdir = '/root/.ssh'
    msg = '  > Creating ' + sshdir + ' '
    printScript(msg, '', False, False, True)
    try:
        stdin, stdout, stderr = ssh.exec_command('mkdir -p ' + sshdir)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        return False
    # copy public key to firewall
    pubkey = sshdir + '/id_ecdsa.pub'
    authorized_keys = sshdir + '/authorized_keys'
    msg = '  > Transfering public key '
    printScript(msg, '', False, False, True)
    try:
        ftp = ssh.open_sftp()
        ftp.put(pubkey, authorized_keys)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        return False
    # close connections
    ftp.close()
    ssh.close()
    return True

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
        elif re.findall(r'mmcblk[0-9]p', partition):
            partnr = re.sub(r'mmcblk[0-9]p', '', partition)
            hdnr = re.search(r'mmcblk(.+?)p[0-9]', partition).group(1)
        elif re.findall(r'nvme0n[0-9]p', partition):
            partnr = re.sub(r'nvme0n[0-9]p', '', partition)
            hdnr = re.search(r'nvme0n(.+?)p[0-9]', partition).group(1)
        else:
            return None
    except:
        return None
    return '(hd' + hdnr + ',' + partnr + ')'

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
        infile = open(tfile , 'r')
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

# modify ini file
def modIni(inifile, section, option, value):
    try:
        i = configparser.ConfigParser()
        i.read(inifile)
        i.set(section, option, value)
        with open(inifile, 'w') as outfile:
            i.write(outfile)
        return True
    except:
        return False

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
        s = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        s.read_string(content)
        return s.get(section, option)
    except:
        return None

# get number of partition
def getStartconfPartnr(startconf, partition):
    rc, content = readStartconf(startconf)
    if rc == False:
        return rc
    count = 1
    for item in re.findall(r'\nDev.*\n', content, re.IGNORECASE):
        if item.split('#')[0].split('=')[1].strip() == partition:
            return str(count)
        count = count + 1
    return False

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
        s = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
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
        for i in ipv4str.split('.'):
            if int(i) > 254:
                return False
        return True
    except:
        return False

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
    route = "/proc/net/route"
    with open(route) as f:
        for line in f.readlines():
            try:
                iface, dest, _, flags, _, _, _, _, _, _, _, =  line.strip().split()
                if dest != '00000000' or not int(flags, 16) & 2:
                    continue
                return iface
            except:
                continue
    return None

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
