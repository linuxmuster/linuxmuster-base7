#!/usr/bin/python3
#
# e_samba-users.py
# thomas@linuxmuster.net
# 20170205
#

import configparser
import constants
import os
from functions import randompassword
from functions import printScript

printScript('', 'begin')
printScript(os.path.basename(__file__))

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
adminpw = i.get('setup', 'adminpw')
domainname = i.get('setup', 'domainname')

# create sophomorix admin user
sophadminpw = randompassword(16)
with open(constants.SOPHADMINSECRET, 'w') as secret:
    secret.write(sophadminpw)
os.system('chmod 600 ' + constants.SOPHADMINSECRET)
os.system('samba-tool user create sophomorix-admin "' + sophadminpw + '"')
os.system('samba-tool user setexpiry sophomorix-admin --noexpiry')
os.system('samba-tool group addmembers "Domain Admins" sophomorix-admin')

# create global-admin
os.system('sophomorix-admin --create global-admin --school global --password "' + adminpw + '"')

# create default-school, no connection to ad
os.system('sophomorix-school --create --school default-school')
