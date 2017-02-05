#!/usr/bin/python3
#
# d_templates.py
# thomas@linuxmuster.net
# 20170205
#

import configparser
import constants
import os
import sys

from functions import setupComment
from functions import backupCfg
from functions import printScript

printScript('', 'begin')
printScript(os.path.basename(__file__))

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
iface = i.get('setup', 'iface')

# stop network interface
os.system('ifconfig ' + iface + ' 0.0.0.0 down')

# templates, whose corresponding configfiles must not be overwritten
do_not_overwrite = 'dhcpd.custom.conf'
# templates, whose corresponding configfiles must not be backed up
do_not_backup = [ 'interfaces.linuxmuster', 'dovecot.linuxmuster.conf']

for f in os.listdir(constants.TPLDIR):
    source = constants.TPLDIR + '/' + f
    try:
        with open(source, 'r') as infile:
            firstline = infile.readline().rstrip('\n')
            infile.seek(0)
            filedata = infile.read()
    except IOError:
        print('Cannot read ' + source + '!')
        sys.exit(1)
    target = firstline.partition(' ')[2]
    # do not overwrite specified configfiles if they exist
    if (f in do_not_overwrite and os.path.isfile(target)):
        continue
    for value in constants.SETUPVALUES:
        filedata = filedata.replace('@@' + value + '@@', i.get('setup', value))
    try:
        if f not in do_not_backup:
            backupCfg(target)
        with open(target, 'w') as outfile:
            outfile.write(setupComment())
            outfile.write(filedata)
    except IOError:
        print('Cannot write ' + target)
        sys.exit(1)

# compatibility link
os.system('ln -sf ' + constants.WIMPORTDATA + ' ' + constants.SYSDIR + '/workstations')

# start network interface
os.system('service networking restart')
