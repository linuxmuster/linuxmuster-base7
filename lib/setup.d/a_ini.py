#!/usr/bin/python3
#
# a_ini.py
# thomas@linuxmuster.net
# 20170126
#

import configparser
import constants
import os
from functions import detectedInterfaces

print ('### ' + os.path.basename(__file__))

# get network interfaces
iface_list, iface_default = detectedInterfaces()

# create configparser handle
defaults = configparser.ConfigParser()
setup = configparser.ConfigParser()

# create initial inifile if no one exists
if not os.path.isfile(constants.SETUPINI):
    setup.add_section('setup')
    for value in constants.SETUPVALUES:
        setup.set('setup', value, '')
    try:
        with open(constants.SETUPINI, 'w') as outfile:
            setup.write(outfile)
    except:
        print('Cannot write ' + constants.SETUPINI + '!')

# read defaults and setup ini files, test values and fill them with defaults if empty
defaults.read(constants.DEFAULTSINI)
setup.read(constants.SETUPINI)
# read custom ini file
if os.path.isfile(constants.CUSTOMINI):
    setup.read(constants.CUSTOMINI)
    os.system('rm -f ' + constants.CUSTOMINI)

for valname in constants.SETUPVALUES:
    defval = defaults.get('defaults', valname)
    # use found interface
    if (valname == 'iface' and not iface_default == ''):
        defval = iface_default
    try:
        if setup.get('setup', valname) == '':
            setup.set('setup', valname, defval)
    except:
        setup.set('setup', valname, defval)

# write inifile finally
try:
    with open(constants.SETUPINI, 'w') as outfile:
        setup.write(outfile)
        os.system('chmod 600 ' + constants.SETUPINI)
except:
    print('Cannot write ' + constants.SETUPINI + '!')
