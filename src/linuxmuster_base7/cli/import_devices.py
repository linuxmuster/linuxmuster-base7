#!/usr/bin/python3
#
# linuxmuster-import-devices
# thomas@linuxmuster.net
# 20251113
#

import configparser
import csv
import datetime
import fnmatch
import getopt
import os
import shutil
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from os import listdir
from os.path import isfile, join
from pathlib import Path

from linuxmuster_base7.functions import getDevicesArray, getGrubOstype, getGrubPart, getSetupValue, getStartconfOsValues, \
    getStartconfOption, getStartconfPartnr, getStartconfPartlabel, getSubnetArray, \
    getLinboVersion, printScript, readTextfile, writeTextfile

# Setup logging
logfile = environment.LOGDIR + '/import-devices.log'


def log_to_file(message):
    """Write message to logfile with timestamp."""
    try:
        with open(logfile, 'a') as f:
            timestamp = str(datetime.datetime.now()).split('.')[0]
            f.write(f'[{timestamp}] {message}\n')
    except Exception:
        pass


def usage():
    print('Usage: linuxmuster-import-devices [options]')
    print(' [options] may be:')
    print(' -s <schoolname>,   --school=<schoolname>   : Select a school other than default-school.')


# read commandline arguments
# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "s:", ["school="])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err)  # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default valued
school = 'default-school'

# evaluate options
for o, a in opts:
    if o in ("-s", "--school"):
        school = a

# default school's devices.csv
devices = environment.WIMPORTDATA

# read setup values
serverip = getSetupValue('serverip')
domainname = getSetupValue('domainname')

# start message
printScript(os.path.basename(__file__), 'begin')
log_to_file('=' * 78)
log_to_file('linuxmuster-import-devices started')
log_to_file('School: ' + school)

# do sophomorix-devices first
msg = 'Starting sophomorix-device syntax check:'
printScript(msg)
log_to_file(msg)
try:
    # Run sophomorix-device and log output to file only
    with open(logfile, 'a') as log:
        log.write('-' * 78 + '\n')
        log.write('sophomorix-device --sync output:\n')
        log.write('-' * 78 + '\n')
        log.flush()
        result = subprocess.run(['sophomorix-device', '--sync'],
                              stdout=log, stderr=subprocess.STDOUT,
                              shell=False, check=False)

    if result.returncode == 0:
        msg = 'sophomorix-device finished OK!'
        printScript(msg)
        log_to_file(msg)
    else:
        msg = f'sophomorix-device finished with return code {result.returncode}'
        printScript(msg)
        log_to_file(msg)
except Exception as err:
    msg = 'sophomorix-device errors detected!'
    printScript(msg)
    log_to_file(msg + ' ' + str(err))
    print(err)
    sys.exit(1)


# functions begin


# delete symlinks
def delSymlinksByPattern(directory, pattern):
    # check if dir exists
    if not os.path.exists(directory):
        #print(f"Directory '{directory}' does not exist.")  # debug
        return
    # iterate through dir
    for root, dirs, files in os.walk(directory):
        for name in files + dirs:
            path = os.path.join(root, name)
            # test for symlink
            if os.path.islink(path) and fnmatch.fnmatch(name, pattern):
                try:
                    os.unlink(path)  # delete symlink
                    #print(f"Symlink deleted: {path}")  # debug
                except Exception as err:
                    continue
                    #print(f"Deletion of {path} failed: {err}")  # debug


# write grub cfgs
def doGrubCfg(startconf, group, kopts):
    grubcfg = environment.LINBOGRUBDIR + '/' + group + '.cfg'
    rc, content = readTextfile(grubcfg)
    if rc and environment.MANAGEDSTR not in content:
        return 'present'
    # get grub partition name of cache
    cache = getStartconfOption(startconf, 'LINBO', 'Cache')
    partnr = getStartconfPartnr(startconf, cache)
    cacheroot = getGrubPart(cache)
    cachelabel = getStartconfPartlabel(startconf, partnr)
    # if cache is not defined provide a forced netboot cfg
    if cacheroot is None:
        netboottpl = environment.LINBOTPLDIR + '/grub.cfg.forced_netboot'
        shutil.copy2(netboottpl, grubcfg)
        return 'not yet configured!'
    # create return message
    if os.path.isfile(grubcfg):
        msg = 'replaced'
    else:
        msg = 'created'
    # create gobal part for group cfg
    globaltpl = environment.LINBOTPLDIR + '/grub.cfg.global'
    rc, content = readTextfile(globaltpl)
    if not rc:
        return 'error!'
    replace_list = [('@@group@@', group), ('@@cachelabel@@', cachelabel),
                    ('@@cacheroot@@', cacheroot), ('@@kopts@@', kopts)]
    for item in replace_list:
        content = content.replace(item[0], item[1])
    rc = writeTextfile(grubcfg, content, 'w')
    # get os infos from group's start.conf
    oslists = getStartconfOsValues(startconf)
    if oslists is None:
        return 'error!'
    # write os parts to grub cfg
    ostpl_pre = environment.LINBOTPLDIR + '/grub.cfg.os'
    for oslist in oslists:
        osname, baseimage, partition, kernel, initrd, kappend, osnr = oslist
        osroot = getGrubPart(partition)
        ostype = getGrubOstype(osname)
        partnr = getStartconfPartnr(startconf, partition)
        oslabel = getStartconfPartlabel(startconf, partnr)
        # different grub.cfg template for os. which is booted from live iso
        imagename, ext = os.path.splitext(baseimage)
        if ext == '.iso':
            ostpl = ostpl_pre + '-iso'
        else:
            ostpl = ostpl_pre
        # add root to kernel append
        if 'root=' not in kappend and ext != '.iso':
            try:
                kappend = kappend + ' root=LABEL=' + oslabel
            except Exception as error:
                kappend = kappend + ' root=' + partition
        rc, content = readTextfile(ostpl)
        if not rc:
            return 'error!'
        replace_list = [('@@group@@', group), ('@@cachelabel@@', cachelabel),
                        ('@@baseimage@@', baseimage), ('@@cacheroot@@', cacheroot),
                        ('@@osname@@', osname), ('@@osnr@@', osnr),
                        ('@@ostype@@', ostype), ('@@oslabel@@', oslabel),
                        ('@@osroot@@', osroot), ('@@partnr@@', partnr),
                        ('@@kernel@@', kernel), ('@@initrd@@', initrd),
                        ('@@kopts@@', kopts), ('@@append@@', kappend)]
        for item in replace_list:
            content = content.replace(item[0], str(item[1]))
        rc = writeTextfile(grubcfg, content, 'a')
        if not rc:
            return 'error!'
    return msg


# write linbo start configuration file
def doLinboStartconf(group):
    startconf = environment.LINBODIR + '/start.conf.' + group
    # provide unconfigured start.conf if there is none for this group
    if os.path.isfile(startconf):
        if getStartconfOption(startconf, 'LINBO', 'Cache') is None:
            msg1 = 'not yet configured!'
        else:
            msg1 = 'present'
    else:
        msg1 = 'not yet configured!'
        shutil.copy2(environment.LINBODIR + '/start.conf', startconf)
    # read kernel options from start.conf
    kopts = getStartconfOption(startconf, 'LINBO', 'KernelOptions')
    # process grub cfgs
    msg2 = doGrubCfg(startconf, group, kopts)
    # format row in columns for output
    row = [group, msg1, msg2]
    printScript("  {: <15} | {: <20} | {: <20}".format(*row))


# write dhcp subnet devices config
def writeDhcpDevicesConfig(school='default-school'):
    printScript('', 'begin')
    msg = 'Working on dhcp configuration for devices'
    printScript(msg)
    log_to_file(msg)
    host_decl_tpl = """host @@hostname@@ {
  option host-name "@@hostname@@";
  hardware ethernet @@mac@@;
"""
    baseConfigFilePath = environment.DHCPDEVCONF
    devicesConfigBasedir = "/etc/dhcp/devices"
    Path(devicesConfigBasedir).mkdir(parents=True, exist_ok=True)

    cfgfile = devicesConfigBasedir + "/" + school + ".conf"
    if os.path.isfile(cfgfile):
        os.unlink(cfgfile)
    if os.path.isfile(baseConfigFilePath):
        os.unlink(baseConfigFilePath)
    try:
        # open devices/<school>.conf for append
        with open(cfgfile, 'a') as outfile:
            # iterate over the defined subnets
            subnets = getSubnetArray('0')
            subnets.append(['DHCP'])
            for item in subnets:
                subnet = item[0]
                # iterate over devices per subnet
                headline = False
                for device_array in getDevicesArray(fieldnrs='1,2,3,4,7,8,10', subnet=subnet, school=school):
                    if not headline:
                        # write corresponding subnet as a comment
                        if subnet == 'DHCP':
                            outfile.write('# dynamic ip hosts\n')
                            printScript('* dynamic ip hosts:')
                        else:
                            outfile.write('# subnet ' + subnet + '\n')
                            printScript('* in subnet ' + subnet + ':')
                        headline = True
                    hostname, group, mac, ip, dhcpopts, computertype, pxeflag = device_array
                    if len(computertype) > 15:
                        computertype = computertype[0:15]
                    # format row in columns for output
                    row = [hostname, ip, computertype, pxeflag]
                    printScript(
                        "  {: <15} | {: <15} | {: <15} | {: <1}".format(*row))
                    # begin host declaration
                    host_decl = host_decl_tpl.replace(
                        '@@mac@@', mac).replace('@@hostname@@', hostname)
                    # fixed ip
                    if ip != 'DHCP':
                        host_decl = host_decl + '  fixed-address ' + ip + ';\n'
                    # only for pxe clients
                    if int(pxeflag) != 0:
                        host_decl = host_decl + '  option extensions-path "' + group + '";\n  option nis-domain "' + group + '";\n'
                        # dhcp options have to be 5 chars minimum to get processed
                        if len(dhcpopts) > 4:
                            for opt in dhcpopts.split(','):
                                host_decl = host_decl + '  ' + opt + ';\n'
                    # finish host declaration
                    host_decl = host_decl + '}\n'
                    # finally write host declaration
                    outfile.write(host_decl)

        # open devices.conf for append
        with open(baseConfigFilePath, 'a') as outfile:
            for devicesConf in listdir(devicesConfigBasedir):
                outfile.write(
                    "include \"{0}/{1}\";\n".format(devicesConfigBasedir, devicesConf))

    except Exception as error:
        print(error)
        return False


# Create necessary host-based symlinks
def doSchoolSpecificGroupLinksAndGetPxeGroups(school='default-school'):
    pxe_groups = []

    # clean up
    linksFileBasepath = environment.LINBODIR + "/boot/links"
    Path(linksFileBasepath).mkdir(parents=True, exist_ok=True)
    linksFile = linksFileBasepath + "/" + school + ".csv"
    if os.path.isfile(linksFile):
        os.unlink(linksFile)

    with open(linksFile, "w+") as csvfile:
        csvWriter = csv.writer(csvfile, delimiter=';',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for device_array in getDevicesArray(fieldnrs='1,2,3,4,10', subnet='all', pxeflag='1,2,3', school=school):
            host, group, mac, ip, pxeflag = device_array
            # collect groups with pxe for later use
            if group not in pxe_groups:
                pxe_groups.append(group)

            # format row in columns for output
            printScript("  {: <15} | {: <15}".format(host, group))

            # start.conf
            linkSource = 'start.conf.' + group
            linkTarget = environment.LINBODIR + '/start.conf-'
            if ip == 'DHCP':
                linkTarget += mac.lower()
            else:
                linkTarget += ip
            csvWriter.writerow([linkSource, linkTarget])

            # Grub.cfg
            linkSource = '../' + group + '.cfg'
            linkTarget = environment.LINBOGRUBDIR + '/hostcfg/' + host + '.cfg'
            csvWriter.writerow([linkSource, linkTarget])

    return pxe_groups


# look up all links for all schools and place them in the correct place
def doAllGroupLinks():
    # delete old config links
    delSymlinksByPattern(environment.LINBODIR, "start.conf-*")
    delSymlinksByPattern(environment.LINBOGRUBDIR + "/hostcfg", "*.cfg")

    linksConfBasedir = environment.LINBODIR + "/boot/links"
    for schoolLinksConf in listdir(linksConfBasedir):
        schoolLinksConfPath = linksConfBasedir + "/" + schoolLinksConf
        if not os.path.isfile(schoolLinksConfPath) or not schoolLinksConf.endswith(".csv"):
            continue

        with open(schoolLinksConfPath, newline='') as csvfile:
            csvReader = csv.reader(csvfile, delimiter=';', quotechar='"')
            for row in csvReader:
                os.symlink(row[0], row[1])

# functions end


# write dhcp devices.conf
writeDhcpDevicesConfig(school=school)


# linbo stuff
linbo_version = int(getLinboVersion().split('.')[0])
printScript('', 'begin')
msg = 'Working on linbo/grub configuration for devices:'
printScript(msg)
log_to_file(msg)

pxe_groups = doSchoolSpecificGroupLinksAndGetPxeGroups(school=school)

# resolve all links and place them
doAllGroupLinks()

# write pxe configs for collected groups
printScript('', 'begin')
msg = 'Working on linbo/grub configuration for groups:'
printScript(msg)
log_to_file(msg)
printScript("  {: <15} | {: <20} | {: <20}".format(
    *[' ', 'linbo start.conf', 'grub cfg']))
printScript("  {: <15}+{: <20}+{: <20}".format(*['-'*16, '-'*22, '-'*21]))
for group in pxe_groups:
    doLinboStartconf(group)


# execute post hooks
hookpath = environment.POSTDEVIMPORT
hookscripts = [f for f in listdir(hookpath) if isfile(
    join(hookpath, f)) and os.access(join(hookpath, f), os.X_OK)]
if len(hookscripts) > 0:
    printScript('', 'begin')
    msg = 'Executing post hooks:'
    printScript(msg)
    log_to_file(msg)
    for h in hookscripts:
        hookscript = hookpath + '/' + h
        msg = '* ' + h + ' '
        printScript(msg, '', False, False, True)
        log_to_file('Executing hook: ' + h)
        output = subprocess.check_output([hookscript, "-s", school]).decode('utf-8')
        if output != '':
            print(output)
            log_to_file('Hook output: ' + output.strip())

# restart services
printScript('', 'begin')
msg = 'Finally restarting dhcp service.'
printScript(msg)
log_to_file(msg)
result = subprocess.run(['service', 'isc-dhcp-server', 'restart'],
                       shell=False, check=False)
log_to_file(f'DHCP service restart: return code {result.returncode}')

# end message
printScript(os.path.basename(__file__), 'end')
log_to_file('linuxmuster-import-devices completed')
log_to_file('=' * 78)



def main():
    """Main entry point for CLI tool."""
    pass


if __name__ == '__main__':
    main()
