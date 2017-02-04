#!/usr/bin/python3
#
# e_samba-users.py
# thomas@linuxmuster.net
# 20170204
#

import configparser
import constants
import os
from functions import randompassword

print ('### ' + os.path.basename(__file__))

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
os.system('samba-tool user create sophomorix-admin ' + sophadminpw + ' --given-name=Admin --surname=Sophomorix --description="Sophomorix Admin" --company=' + domainname)

# create global-admin
os.system('sophomorix-admin --create global-admin --school global --password ' + adminpw)

# create default-school, no connection to ad
os.system('sophomorix-school --create --school default-school')
