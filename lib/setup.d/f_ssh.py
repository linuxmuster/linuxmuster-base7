#!/usr/bin/python3
#
# f_ssh.py
# thomas@linuxmuster.net
# 20170129
#

import configparser
import constants
import getpass
import os
import re
import paramiko

from functions import setupComment
from functions import backupCfg
from functions import check_socket

print ('### ' + os.path.basename(__file__))

# enter firewall password
def enterFwPassword():
    global firewallpw
    firewallpw = getpass.getpass('Please enter your firewall password: ')

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
firewallip = i.get('setup', 'firewallip')
try:
    firewallpw = i.get('setup', 'firewallpw')
except:
    enterFwPassword()

# variables
hostkey = '/etc/ssh/ssh_host_'
sshdir = '/root/.ssh'
rootkey = sshdir + '/id_'
rsapubkey = rootkey + 'rsa.pub'
known_hosts = sshdir + '/known_hosts'
authorized_keys = sshdir + '/authorized_keys'
crypto_list = ['dsa', 'ecdsa', 'ed25519', 'rsa']

# delete old ssh keys
os.system('rm -f /etc/ssh/*key* ' + sshdir + '/id*')

# create keys
for a in crypto_list:
    try:
        os.system('ssh-keygen -t ' + a + ' -f ' + hostkey + a + '_key -N ""')
        os.system('ssh-keygen -t ' + a + ' -f ' + rootkey + a + ' -N ""')
    except:
        print('Cannot create ' + a + ' ssh keys!')
        quit()

# restart ssh service
os.system('service ssh restart')

# remove public firewall keys
if os.path.isfile(known_hosts):
    for k in ['firewall', firewallip]:
        os.system('ssh-keygen -f ' + known_hosts + ' -R [' + k + ']:222 &> /dev/null')
        os.system('ssh-keygen -f ' + known_hosts + ' -R [' + k + ']:22 &> /dev/null')

# test ssh connection
fwssh = 'false'
for p in [22, 222]:
    print('Testing SSH-Port ' + str(p) + ' ...')
    if check_socket(firewallip, p):
        print('SSH-Port ' + str(p) + ' is open.')
        fwssh = 'true'
        sshport = p
        break
if fwssh == 'false':
    quit()

# establish ssh connection to firewall
print('Establishing a ssh connection to the firewall ...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect(firewallip, port=sshport, username='root', password=firewallpw)
    print(' ... success!')
except:
    print(' ... failed!')
    quit()

# create .ssh dir
print('Create ssh dir on firewall.')
stdin, stdout, stderr = ssh.exec_command('mkdir -p ' + sshdir)

# copy new public key to firewall
print('Copy ssh key to firewall.')
ftp = ssh.open_sftp()
ftp.put(rsapubkey, authorized_keys)
ftp.close()

# close connection
ssh.close()
