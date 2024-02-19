#!/usr/bin/python3
#
# constants.py: linuxmuster environment
# don't change this
# thomas@linuxmuster.net
# 20240219
#

# firewall major version to match
FWMAJORVER = 24

# global variables
ROOTMNTOPTS = 'user_xattr,acl,usrquota,usrjquota=aquota.user,grpquota,grpjquota=aquota.group,jqfmt=vfsv0,errors=remount-ro,barrier=1'
SYSDIR = '/etc/linuxmuster'
SUBNETSCSV = SYSDIR + '/subnets.csv'
SOPHOSYSDIR = SYSDIR + '/sophomorix'
DEFAULTSCHOOL = SOPHOSYSDIR + '/default-school'
SCHOOLCONF = DEFAULTSCHOOL + '/school.conf'
SCHOOLSSHARE = '/srv/samba/schools'
WIMPORTDATA = DEFAULTSCHOOL + '/devices.csv'
NTPSOCKDIR = '/var/lib/samba/ntp_signd'
SYSVOLDIR = '/var/lib/samba/sysvol'
SYSVOLTLSDIR = SYSVOLDIR + '/@@domainname@@/tls'
SSLDIR = SYSDIR + '/ssl'
SSLCNF = SSLDIR + '/server_cert_ext.cnf'
CAKEY = SSLDIR + '/cakey.pem'
CACERT = SSLDIR + '/cacert.pem'
CACERTCRT = SSLDIR + '/cacert.crt'
CACERTB64 = CACERT + '.b64'
SSHPUBKEY = '/root/.ssh/id_rsa.pub'
SSHPUBKEYB64 = SSHPUBKEY + '.b64'
SECRETDIR = SYSDIR + '/.secret'
BINDUSERSECRET = SECRETDIR + '/global-binduser'
RADIUSSECRET = SECRETDIR + '/radiussecret'
ADADMINSECRET = SECRETDIR + '/administrator'
DNSADMINSECRET = SECRETDIR + '/dns-admin'
CAKEYSECRET = SECRETDIR + '/cakey'
FWAPIKEYS = SECRETDIR + '/firewall.api.ini'
FWFULLCHAIN = SSLDIR + '/firewall.fullchain.pem'
LIBDIR = '/usr/lib/linuxmuster'
SHAREDIR = '/usr/share/linuxmuster'
EXAMPLEDIR = SHAREDIR + '/examples'
CACHEDIR = '/var/cache/linuxmuster'
VARDIR = '/var/lib/linuxmuster'
HOOKSDIR = VARDIR + '/hooks'
POSTDEVIMPORT = HOOKSDIR + '/device-import.post.d'
LOGDIR = '/var/log/linuxmuster'
SETUPLOG = LOGDIR + '/setup.log'
SETUPDIR = LIBDIR + '/setup.d'
TPLDIR = SHAREDIR + '/templates'
CUSTOMINI = CACHEDIR + '/custom.ini'
FWSHAREDIR = SHAREDIR + '/firewall/opnsense'
FWAUTHCFG = FWSHAREDIR + '/pre-auth.conf'
FWOSCONFTPL = FWSHAREDIR + '/config.xml.tpl'
FWCONFLOCAL = CACHEDIR + '/opnsense.xml'
FWCONFREMOTE = '/conf/config.xml'
GW_LAN = 'GW_LAN'
SETUPINI = VARDIR + '/setup.ini'
DEFAULTSINI = SHAREDIR + '/setupdefaults.ini'
PREPINI = VARDIR + '/prepare.ini'
LINBODIR = '/srv/linbo'
LINBOVERFILE = LINBODIR + '/linbo-version'
LINBOIMGDIR = LINBODIR + '/images'
LINBOGRUBDIR = LINBODIR + '/boot/grub'
LINBOLOGDIR = LOGDIR + '/linbo'
LINBOSHAREDIR = SHAREDIR + '/linbo'
LINBOTPLDIR = LINBOSHAREDIR + '/templates'
LINBOCACHEDIR = CACHEDIR + '/linbo'
LINBOSYSDIR = SYSDIR + '/linbo'
LINBOVARDIR = VARDIR + '/linbo'
DHCPDEVCONF = '/etc/dhcp/devices.conf'
DHCPSUBCONF = '/etc/dhcp/subnets.conf'
NETCFG = '/etc/netplan/01-netcfg.yaml'
MANAGEDSTR = '### managed by linuxmuster.net ###'
ROOTPW = 'Muster!'

# grub stuff
GRUBCOMMONMODS = 'all_video boot chain configfile cpuid echo net ext2 extcmd fat \
gettext gfxmenu gfxterm gzio http ntfs linux linux16 loadenv minicmd net part_gpt \
part_msdos png progress read reiserfs search sleep terminal test tftp'
# arch specific netboot modules
GRUBEFIMODS = GRUBCOMMONMODS + ' efi_gop efi_uga efinet linuxefi'
GRUBI386MODS = GRUBCOMMONMODS + ' biosdisk gfxterm_background normal ntldr pxe'
GRUBISOMODS = 'iso9660 usb'
GRUBFONT = 'unicode'
