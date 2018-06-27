#!/usr/bin/python3
#
# process config templates
# thomas@linuxmuster.net
# 20180627
#

import configparser
import constants
import datetime
import os
import sys

from functions import setupComment
from functions import backupCfg
from functions import printScript
from functions import readTextfile
from functions import replaceInFile
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup data
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    # setupdefaults.ini
    defaults = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    defaults.read(constants.DEFAULTSINI)
    # setup.ini
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    adminpw = setup.get('setup', 'adminpw')
    bitmask = setup.get('setup', 'bitmask')
    broadcast = setup.get('setup', 'broadcast')
    dhcprange = setup.get('setup', 'dhcprange')
    dhcprange1 = dhcprange.split(' ')[0]
    dhcprange2 = dhcprange.split(' ')[1]
    domainname = setup.get('setup', 'domainname')
    firewallip = setup.get('setup', 'firewallip')
    linbodir = constants.LINBODIR
    netbiosname = setup.get('setup', 'netbiosname')
    netmask = setup.get('setup', 'netmask')
    network = setup.get('setup', 'network')
    realm = setup.get('setup', 'realm')
    sambadomain = setup.get('setup', 'sambadomain')
    servername = setup.get('setup', 'servername')
    serverip = setup.get('setup', 'serverip')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# templates, whose corresponding configfiles must not be overwritten
do_not_overwrite = 'dhcpd.custom.conf'
# templates, whose corresponding configfiles must not be backed up
do_not_backup = [ 'interfaces.linuxmuster', 'dovecot.linuxmuster.conf', 'smb.conf']

printScript('Processing config templates:')
for f in os.listdir(constants.TPLDIR):
    source = constants.TPLDIR + '/' + f
    msg = '* ' + f + ' '
    printScript(msg, '', False, False, True)
    try:
        # read template file
        rc, filedata = readTextfile(source)
        # replace placeholders with values
        filedata = filedata.replace('@@bitmask@@', bitmask)
        filedata = filedata.replace('@@broadcast@@', broadcast)
        filedata = filedata.replace('@@dhcprange@@', dhcprange)
        filedata = filedata.replace('@@dhcprange1@@', dhcprange1)
        filedata = filedata.replace('@@dhcprange2@@', dhcprange2)
        filedata = filedata.replace('@@domainname@@', domainname)
        filedata = filedata.replace('@@firewallip@@', firewallip)
        filedata = filedata.replace('@@linbodir@@', linbodir)
        filedata = filedata.replace('@@netbiosname@@', netbiosname)
        filedata = filedata.replace('@@netmask@@', netmask)
        filedata = filedata.replace('@@network@@', network)
        filedata = filedata.replace('@@realm@@', realm)
        filedata = filedata.replace('@@sambadomain@@', sambadomain)
        filedata = filedata.replace('@@servername@@', servername)
        filedata = filedata.replace('@@serverip@@', serverip)
        # get target path
        firstline = filedata.split('\n')[0]
        target = firstline.partition(' ')[2]
        # do not overwrite specified configfiles if they exist
        if (f in do_not_overwrite and os.path.isfile(target)):
            printScript(' Success!', '', True, True, False, len(msg))
            continue
        # create target directory
        subProc('mkdir -p ' + os.path.dirname(target), logfile)
        # backup file
        if f not in do_not_backup:
            backupCfg(target)
        with open(target, 'w') as outfile:
            outfile.write(setupComment())
            outfile.write(filedata)
        printScript(' Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# restart network interface
msg = 'Network setup '
printScript(msg, '', False, False, True)
try:
    subProc('/usr/sbin/linuxmuster-prepare -x -s -u -p server -f ' + firewallip + ' -n ' + serverip + '/' + bitmask + ' -d ' + domainname + ' -t ' + servername + ' -r ' + serverip + ' -a "' + adminpw + '"', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# restart network interface
#msg = 'Restarting network '
#printScript(msg, '', False, False, True)
#try:
#    subProc('service networking restart', logfile)
#    printScript(' Success!', '', True, True, False, len(msg))
#except:
#    printScript(' Failed!', '', True, True, False, len(msg))
#    sys.exit(1)

# set server time
msg = 'Adjusting server time '
printScript(msg, '', False, False, True)
subProc('service ntp stop', logfile)
subProc('ntpdate pool.ntp.org', logfile)
subProc('service ntp start', logfile)
now = str(datetime.datetime.now()).split('.')[0]
printScript(' ' + now, '', True, True, False, len(msg))
