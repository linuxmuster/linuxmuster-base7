#!/usr/bin/python3
#
# Filename     : linbo.py
# Description  : LINBO start.conf and GRUB boot configuration helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import configparser
import re
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from .files import readTextfile, writeTextfile


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
