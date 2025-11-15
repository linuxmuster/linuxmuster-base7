#!/usr/bin/python3
#
# linuxmuster-import-devices
# thomas@linuxmuster.net
# 20251115
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

# Constants for device field mappings
# Field numbers correspond to columns in devices.csv:
# 1=hostname, 2=group, 3=mac, 4=ip, 7=dhcpopts, 8=computertype, 10=pxeflag
DEVICE_FIELDS_DHCP = '1,2,3,4,7,8,10'  # Fields needed for DHCP config
DEVICE_FIELDS_LINKS = '1,2,3,4,10'      # Fields needed for LINBO symlinks


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


# Module-level execution code has been moved to main() function below


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


# Helper functions for grub configuration
# These functions split the complex grub configuration generation into manageable pieces

def getCachePartitionInfo(startconf):
    """Extract cache partition information from start.conf.

    Args:
        startconf: Path to start.conf file

    Returns:
        Tuple of (cacheroot, cachelabel, partnr) or (None, None, None) if cache not configured
    """
    # Read cache partition setting from LINBO section
    cache = getStartconfOption(startconf, 'LINBO', 'Cache')
    # Get partition number and convert to grub format
    partnr = getStartconfPartnr(startconf, cache)
    cacheroot = getGrubPart(cache)  # e.g., converts /dev/sda1 to (hd0,1)
    cachelabel = getStartconfPartlabel(startconf, partnr)
    return (cacheroot, cachelabel, partnr)


def createGrubGlobalSection(grubcfg, group, cacheroot, cachelabel, kopts):
    """Create global section of grub config from template.

    Args:
        grubcfg: Path to grub config file
        group: Device group name
        cacheroot: Grub partition name for cache
        cachelabel: Partition label for cache
        kopts: Kernel options

    Returns:
        True if successful, False otherwise
    """
    # Load global grub template (contains menu structure and basic settings)
    globaltpl = environment.LINBOTPLDIR + '/grub.cfg.global'
    rc, content = readTextfile(globaltpl)
    if not rc:
        return False

    # Replace template variables with actual values
    replace_list = [('@@group@@', group), ('@@cachelabel@@', cachelabel),
                    ('@@cacheroot@@', cacheroot), ('@@kopts@@', kopts)]
    for item in replace_list:
        content = content.replace(item[0], item[1])

    # Write global section (mode 'w' overwrites any existing file)
    rc = writeTextfile(grubcfg, content, 'w')
    return rc


def createGrubOsSection(grubcfg, startconf, group, cacheroot, cachelabel, kopts):
    """Create OS-specific sections of grub config from templates.

    Args:
        grubcfg: Path to grub config file
        startconf: Path to start.conf file
        group: Device group name
        cacheroot: Grub partition name for cache
        cachelabel: Partition label for cache
        kopts: Kernel options

    Returns:
        True if successful, False otherwise
    """
    # Get list of all OS definitions from start.conf
    oslists = getStartconfOsValues(startconf)
    if oslists is None:
        return False

    # Process each OS (Windows, Linux, etc.) and create boot menu entries
    ostpl_pre = environment.LINBOTPLDIR + '/grub.cfg.os'
    for oslist in oslists:
        # Unpack OS configuration: name, image file, partition, kernel, initrd, kernel params, OS number
        osname, baseimage, partition, kernel, initrd, kappend, osnr = oslist
        osroot = getGrubPart(partition)  # Convert partition to grub format
        ostype = getGrubOstype(osname)   # Detect OS type (linux, windows, etc.)
        partnr = getStartconfPartnr(startconf, partition)
        oslabel = getStartconfPartlabel(startconf, partnr)

        # Select template: different template for ISO-based live systems vs. installed OS
        imagename, ext = os.path.splitext(baseimage)
        if ext == '.iso':
            ostpl = ostpl_pre + '-iso'  # Use ISO boot template
        else:
            ostpl = ostpl_pre  # Use standard OS template

        # Add root parameter to kernel command line if not already present
        # (not needed for ISO boots which have their own root mechanism)
        if 'root=' not in kappend and ext != '.iso':
            try:
                kappend = kappend + ' root=LABEL=' + oslabel  # Prefer label-based root
            except Exception as error:
                kappend = kappend + ' root=' + partition  # Fallback to device path

        # Load OS-specific template
        rc, content = readTextfile(ostpl)
        if not rc:
            return False

        # Replace all template placeholders with actual OS configuration
        replace_list = [('@@group@@', group), ('@@cachelabel@@', cachelabel),
                        ('@@baseimage@@', baseimage), ('@@cacheroot@@', cacheroot),
                        ('@@osname@@', osname), ('@@osnr@@', osnr),
                        ('@@ostype@@', ostype), ('@@oslabel@@', oslabel),
                        ('@@osroot@@', osroot), ('@@partnr@@', partnr),
                        ('@@kernel@@', kernel), ('@@initrd@@', initrd),
                        ('@@kopts@@', kopts), ('@@append@@', kappend)]
        for item in replace_list:
            content = content.replace(item[0], str(item[1]))

        # Append OS section to grub config (mode 'a' appends to existing file)
        rc = writeTextfile(grubcfg, content, 'a')
        if not rc:
            return False

    return True


def doGrubCfg(startconf, group, kopts):
    """Write grub configuration file for a device group.

    Args:
        startconf: Path to start.conf file
        group: Device group name
        kopts: Kernel options

    Returns:
        Status message: 'present', 'not yet configured!', 'created', 'replaced', or 'error!'
    """
    grubcfg = environment.LINBOGRUBDIR + '/' + group + '.cfg'

    # Check if grub config exists and is managed
    rc, content = readTextfile(grubcfg)
    if rc and environment.MANAGEDSTR not in content:
        return 'present'

    # Get cache partition information
    cacheroot, cachelabel, partnr = getCachePartitionInfo(startconf)

    # If cache is not defined provide a forced netboot cfg
    if cacheroot is None:
        netboottpl = environment.LINBOTPLDIR + '/grub.cfg.forced_netboot'
        shutil.copy2(netboottpl, grubcfg)
        return 'not yet configured!'

    # Determine status message
    if os.path.isfile(grubcfg):
        msg = 'replaced'
    else:
        msg = 'created'

    # Create global section of grub config
    if not createGrubGlobalSection(grubcfg, group, cacheroot, cachelabel, kopts):
        return 'error!'

    # Create OS-specific sections
    if not createGrubOsSection(grubcfg, startconf, group, cacheroot, cachelabel, kopts):
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


# Helper functions for DHCP configuration
# These functions reduce nesting and improve readability of DHCP config generation

def buildDhcpHostDeclaration(hostname, group, mac, ip, dhcpopts, pxeflag):
    """Build DHCP host declaration for a single device.

    Args:
        hostname: Device hostname
        group: Device group name
        mac: MAC address
        ip: IP address or 'DHCP'
        dhcpopts: DHCP options string (comma-separated)
        pxeflag: PXE boot flag (0=no PXE, 1/2/3=different PXE modes)

    Returns:
        String containing complete DHCP host declaration
    """
    # Start with basic host declaration template
    host_decl_tpl = """host @@hostname@@ {
  option host-name "@@hostname@@";
  hardware ethernet @@mac@@;
"""
    host_decl = host_decl_tpl.replace('@@mac@@', mac).replace('@@hostname@@', hostname)

    # Add fixed IP address if not using DHCP
    if ip != 'DHCP':
        host_decl = host_decl + '  fixed-address ' + ip + ';\n'

    # Add PXE-specific options for network boot clients
    if int(pxeflag) != 0:
        # extensions-path and nis-domain tell client which LINBO group config to use
        host_decl = host_decl + '  option extensions-path "' + group + '";\n  option nis-domain "' + group + '";\n'
        # Add custom DHCP options if provided (minimum 5 chars for validation)
        if len(dhcpopts) > 4:
            for opt in dhcpopts.split(','):
                host_decl = host_decl + '  ' + opt + ';\n'

    # Close host declaration block
    host_decl = host_decl + '}\n'
    return host_decl


def writeSubnetHeader(outfile, subnet):
    """Write subnet header comment to DHCP config file.

    Args:
        outfile: File handle to write to
        subnet: Subnet identifier or 'DHCP'
    """
    if subnet == 'DHCP':
        outfile.write('# dynamic ip hosts\n')
        printScript('* dynamic ip hosts:')
    else:
        outfile.write('# subnet ' + subnet + '\n')
        printScript('* in subnet ' + subnet + ':')


def processDevicesForSubnet(outfile, subnet, school):
    """Process all devices in a subnet and write DHCP declarations.

    Args:
        outfile: File handle to write to
        subnet: Subnet identifier (e.g., '10.0.0.0/24' or 'DHCP')
        school: School name

    Returns:
        Number of devices processed
    """
    device_count = 0
    headline_written = False

    # Query all devices in this subnet from devices.csv
    for device_array in getDevicesArray(fieldnrs=DEVICE_FIELDS_DHCP, subnet=subnet, school=school):
        # Write subnet header only once when first device is encountered
        if not headline_written:
            writeSubnetHeader(outfile, subnet)
            headline_written = True

        # Unpack device fields (see DEVICE_FIELDS_DHCP constant for field mapping)
        hostname, group, mac, ip, dhcpopts, computertype, pxeflag = device_array
        # Truncate long computer type names for clean output
        if len(computertype) > 15:
            computertype = computertype[0:15]

        # Print device info to console for user feedback
        row = [hostname, ip, computertype, pxeflag]
        printScript("  {: <15} | {: <15} | {: <15} | {: <1}".format(*row))

        # Generate and write DHCP host declaration
        host_decl = buildDhcpHostDeclaration(hostname, group, mac, ip, dhcpopts, pxeflag)
        outfile.write(host_decl)
        device_count += 1

    return device_count


# write dhcp subnet devices config
def writeDhcpDevicesConfig(school='default-school'):
    """Generate DHCP device configuration for a school.

    Args:
        school: School name (default: 'default-school')

    Returns:
        False on error, None on success
    """
    printScript('', 'begin')
    msg = 'Working on dhcp configuration for devices'
    printScript(msg)
    log_to_file(msg)

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
                processDevicesForSubnet(outfile, subnet, school)

        # open devices.conf for append
        with open(baseConfigFilePath, 'a') as outfile:
            for devicesConf in listdir(devicesConfigBasedir):
                outfile.write("include \"{0}/{1}\";\n".format(devicesConfigBasedir, devicesConf))

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

        for device_array in getDevicesArray(fieldnrs=DEVICE_FIELDS_LINKS, subnet='all', pxeflag='1,2,3', school=school):
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


def main():
    """Main entry point for CLI tool.

    This function orchestrates the complete device import workflow:
    1. Parses command-line arguments
    2. Runs sophomorix-device syntax check
    3. Generates DHCP configuration for all devices
    4. Creates LINBO/GRUB boot configurations
    5. Executes post-import hooks
    6. Restarts DHCP service
    """
    # Parse command-line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:", ["school="])
    except getopt.GetoptError as err:
        print(err)  # e.g., "option -a not recognized"
        usage()
        sys.exit(2)

    # Set default values
    school = 'default-school'

    # Process command-line options
    for o, a in opts:
        if o in ("-s", "--school"):
            school = a

    # Get devices.csv path (currently unused, kept for compatibility)
    devices = environment.WIMPORTDATA

    # Read required setup configuration values
    serverip = getSetupValue('serverip')
    domainname = getSetupValue('domainname')

    # Log import start
    printScript(os.path.basename(__file__), 'begin')
    log_to_file('=' * 78)
    log_to_file('linuxmuster-import-devices started')
    log_to_file('School: ' + school)

    # Step 1: Run sophomorix-device to validate devices.csv syntax
    msg = 'Starting sophomorix-device syntax check:'
    printScript(msg)
    log_to_file(msg)
    try:
        # Run sophomorix-device and log detailed output to file (not console)
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

    # Step 2: Generate DHCP configuration for all devices
    writeDhcpDevicesConfig(school=school)

    # Step 3: Generate LINBO/GRUB boot configuration
    linbo_version = int(getLinboVersion().split('.')[0])
    printScript('', 'begin')
    msg = 'Working on linbo/grub configuration for devices:'
    printScript(msg)
    log_to_file(msg)

    # Create symlinks from devices to their group configurations
    pxe_groups = doSchoolSpecificGroupLinksAndGetPxeGroups(school=school)

    # Resolve and place all symlinks for all schools
    doAllGroupLinks()

    # Generate grub configs for each PXE boot group
    printScript('', 'begin')
    msg = 'Working on linbo/grub configuration for groups:'
    printScript(msg)
    log_to_file(msg)
    printScript("  {: <15} | {: <20} | {: <20}".format(
        *[' ', 'linbo start.conf', 'grub cfg']))
    printScript("  {: <15}+{: <20}+{: <20}".format(*['-'*16, '-'*22, '-'*21]))
    for group in pxe_groups:
        doLinboStartconf(group)

    # Step 4: Execute post-import hooks (if any exist)
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

    # Step 5: Restart DHCP service to apply new configuration
    printScript('', 'begin')
    msg = 'Finally restarting dhcp service.'
    printScript(msg)
    log_to_file(msg)
    result = subprocess.run(['service', 'isc-dhcp-server', 'restart'],
                           shell=False, check=False)
    log_to_file(f'DHCP service restart: return code {result.returncode}')

    # Log completion
    printScript(os.path.basename(__file__), 'end')
    log_to_file('linuxmuster-import-devices completed')
    log_to_file('=' * 78)


if __name__ == '__main__':
    main()
