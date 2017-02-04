#!/usr/bin/python3
#
# constants.py
#
# thomas@linuxmuster.net
# 20170201
#

# don't change this file

# global variables
ROOTMNTOPTS = 'user_xattr,acl,usrquota,usrjquota=aquota.user,grpquota,grpjquota=aquota.group,jqfmt=vfsv0,errors=remount-ro,barrier=1'
SYSDIR = '/etc/linuxmuster'
SOPHOSYSDIR = SYSDIR + '/sophomorix'
DEFAULTSCHOOL = SOPHOSYSDIR + '/default-school'
SCHOOLCONF = DEFAULTSCHOOL + '/school.conf'
WIMPORTDATA = DEFAULTSCHOOL + '/devices.csv'
SSLDIR = SYSDIR + '/ssl'
SECRETDIR = SYSDIR + '/.secret'
BINDUSERSECRET = SECRETDIR + '/bind-user'
SOPHADMINSECRET = SECRETDIR + '/sophomorix-admin'
ADADMINSECRET = SECRETDIR + '/administrator'
LIBDIR = '/usr/lib/linuxmuster'
SHAREDIR = '/usr/share/linuxmuster'
CACHEDIR = '/var/cache/linuxmuster'
VARDIR = '/var/lib/linuxmuster'
LOGDIR = '/var/log/linuxmuster'
SETUPDIR = LIBDIR + '/setup.d'
TPLDIR = SHAREDIR + '/templates'
CUSTOMINI = CACHEDIR + '/custom.ini'
SETUPINI = VARDIR + '/setup.ini'
DEFAULTSINI = SHAREDIR + '/setupdefaults.ini'
LINBODIR = '/var/linbo'
LINBOGRUBDIR = LINBODIR + '/boot/grub'
LINBOLOGDIR = LOGDIR + '/linbo'
LINBOSHAREDIR = SHAREDIR + '/linbo'
LINBOTPLDIR = LINBOSHAREDIR + '/templates'
LINBOCACHEDIR = CACHEDIR + '/linbo'
DHCPDEVCONF = '/etc/dhcp/devices.conf'
OPSIPXEFILE = 'linux/pxelinux.0'
MANAGEDSTR = '### managed by linuxmuster.net ###'

# list of setup values
SETUPVALUES = ['servername', 'domainname', 'basedn', 'serverip', 'opsiip', \
                'smtprelay', 'gatewayip', 'firewallip', 'netmask', \
                'network', 'broadcast', 'dhcprange', 'iface', 'adminpw', \
                'sambadomain', 'schoolname', 'location', 'country', 'state']
