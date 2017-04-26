#!/usr/bin/python3
#
# linuxmuster-import-devices.py
# thomas@linuxmuster.net
# 20170426
#

import configparser
import constants
import csv
import getopt
import os
import re
import sys

from functions import getGrubOstype
from functions import getGrubPart
from functions import getStartconfOsValues
from functions import getStartconfOption
from functions import getStartconfPartnr
from functions import printScript
from functions import readTextfile
from functions import setGlobalStartconfOption
from functions import writeTextfile

# default devices.csv
devices = constants.WIMPORTDATA

# read INIFILE
setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
setup.read(constants.SETUPINI)
serverip = setup.get('setup', 'serverip')
opsiip = setup.get('setup', 'opsiip')
domainname = setup.get('setup', 'domainname')

# start message
printScript(os.path.basename(__file__), 'begin')

# do sophomorix-devices first
msg = 'Processing sophomorix-device:'
printScript(msg)
result = os.system('sophomorix-device')
msg = 'sophomorix-device finished '
if result != 0:
    printScript(msg + 'with errors!')
    sys.exit(result)
else:
    printScript(msg + 'successfully!')

# write grub cfgs
def doGrubCfg(startconf, group, kopts):
    grubcfg = constants.LINBOGRUBDIR + '/' + group + '.cfg'
    rc, content = readTextfile(grubcfg)
    if rc == True and not constants.MANAGEDSTR in content:
        printScript('  > Keeping pxe configuration.')
        return True
    # get grub partition name of cache
    cache = getStartconfOption(startconf, 'LINBO', 'Cache')
    cacheroot = getGrubPart(cache)
    # if cache is not defined provide a forced netboot cfg
    if cacheroot == None:
        netboottpl = constants.LINBOTPLDIR + '/grub.cfg.forced_netboot'
        printScript('  > Creating minimal pxe configuration. start.conf is incomplete!')
        rc = os.system('cp ' + netboottpl + ' ' + grubcfg)
        return
    else:
        printScript('  > Creating pxe configuration.')
    # create gobal part for group cfg
    globaltpl = constants.LINBOTPLDIR + '/grub.cfg.global'
    rc, content = readTextfile(globaltpl)
    if rc == False:
        return rc
    replace_list = [('@@group@@', group), ('@@cacheroot@@', cacheroot), ('@@kopts@@', kopts)]
    for item in replace_list:
        content = content.replace(item[0], item[1])
    rc = writeTextfile(grubcfg, content, 'w')
    # get os infos from group's start.conf
    oslists = getStartconfOsValues(startconf)
    if oslists == None:
        return False
    # write os parts to grub cfg
    ostpl = constants.LINBOTPLDIR + '/grub.cfg.os'
    for oslist in oslists:
        osname, partition, kernel, initrd, kappend, osnr = oslist
        osroot = getGrubPart(partition)
        ostype = getGrubOstype(osname)
        partnr = getStartconfPartnr(startconf, partition)
        rc, content = readTextfile(ostpl)
        if rc == False:
            return rc
        replace_list = [('@@group@@', group), ('@@cacheroot@@', cacheroot),
            ('@@osname@@', osname), ('@@osnr@@', osnr), ('@@ostype@@', ostype),
            ('@@osroot@@', osroot), ('@@partition@@', partition),
            ('@@partnr@@', partnr), ('@@kernel@@', kernel), ('@@initrd@@', initrd),
            ('@@kopts@@', kopts), ('@@append@@', kappend)]
        for item in replace_list:
            content = content.replace(item[0], item[1])
        rc = writeTextfile(grubcfg, content, 'a')
        if rc == False:
            return rc

# write linbo start configuration file
def doLinboStartconf(group):
    startconf = constants.LINBODIR + '/start.conf.' + group
    # provide simple start.conf if there is none for this group
    if not os.path.isfile(startconf):
        msg = '  > Creating minimal start.conf. Further configuration is necessary!'
        printScript(msg, '', True)
        os.system('cp ' + constants.LINBODIR + '/start.conf ' + startconf)
    # read values from start.conf
    group_s = getStartconfOption(startconf, 'LINBO', 'Group')
    serverip_s = getStartconfOption(startconf, 'LINBO', 'Server')
    kopts_s = getStartconfOption(startconf, 'LINBO', 'KernelOptions')
    try:
        serverip_k = re.findall(r'server=[^ ]*', kopts_s, re.IGNORECASE)[0].split('=')[1]
    except:
        serverip_k = None
    # determine whether global values from start conf have to changed
    if serverip_k != None and isValidHostIpv4(serverip_k) == True:
        serverip_r = serverip_k
    else:
        serverip_r = serverip
    if kopts_s == None:
        kopts_r = 'splash quiet'
    else:
        kopts_r = kopts_s
    if group_s != group:
        group_r = group
    else:
        group_r = group
    # change global startconf options if necessary
    if serverip_s != serverip_r:
        rc = setGlobalStartconfOption(startconf, 'Server', serverip_r)
        if rc == False:
            return rc
    if kopts_s != kopts_r:
        rc = setGlobalStartconfOption(startconf, 'KernelOptions', kopts_r)
        if rc == False:
            return rc
    if group_s != group_r:
        rc = setGlobalStartconfOption(startconf, 'Group', group_r)
        if rc == False:
            return rc
    # process grub cfgs
    doGrubCfg(startconf, group, kopts_r)

# iterate over devices
printScript('', 'begin')
printScript('Processing dhcp clients:')
f = open(devices, newline='')
reader = csv.reader(f, delimiter=';', quoting=csv.QUOTE_NONE)
d = open(constants.DHCPDEVCONF, 'w')
pxe_groups = []
for row in reader:
    try:
        room, host, group, mac, ip, field6, field7, field8, field9, field10, pxe = row
    except:
        continue
    if room[:1] == '#' or room[:1] == ';':
        continue
    if (pxe == '3' or pxe == '2') and isValidHostIpv4(opsiip) == False:
        pxe = '1'
    if pxe == '0':
        htype = 'IP-Host : '
    else:
        htype = 'PXE-Host: '
    printScript('* ' + htype + host)
    # write conf for dhcp clients
    d.write('host ' + ip + ' {\n')
    d.write('  hardware ethernet ' + mac + ';\n')
    d.write('  fixed-address ' + ip + ';\n')
    d.write('  option host-name "' + host + '";\n')
    if pxe == '1' or pxe == '2' or pxe == '22':
        d.write('  option extensions-path "' + group + '";\n')
    elif pxe == '3':
        d.write('  next-server ' + opsiip + ';\n')
        d.write('  filename "' + constants.OPSIPXEFILE + '";\n')
    d.write('}\n')
    # link group's start.conf to host's one
    if pxe != '0':
        groupconf = 'start.conf.' + group
        hostlink = constants.LINBODIR + '/start.conf-' + ip
        os.system('ln -sf ' + groupconf + ' ' + hostlink)
    # collect groups with pxe for later use
    if not group in pxe_groups and pxe != '0':
        pxe_groups.append(group)
d.close()
f.close()

# write pxe configs for collected groups
printScript('', 'begin')
printScript('Processing pxe groups:')
for group in pxe_groups:
    msg = '* ' + group
    printScript(msg)
    doLinboStartconf(group)

# restart services
printScript('', 'begin')
printScript('Restarting services:')
maxlen = 17
RC = 0
for service in ['isc-dhcp-server', 'linbo-bittorrent', 'linbo-multicast']:
    gaplen = maxlen - len(service)
    msg = '* ' + service + ' '
    printScript(msg, '', False, False, True)
    for action in ['stop', 'start']:
        result = os.system('service ' + service + ' ' + action)
        if result != 0:
            RC = result
    if RC == 0:
        printScript(' OK!', '', True, True, False, len(msg))
    else:
        printScript(' Failed!', '', True, True, False, len(msg))

# end message
printScript(os.path.basename(__file__), 'end')

sys.exit(RC)
