#!/usr/bin/python3
#
# constants.py
#
# thomas@linuxmuster.net
# 20170814
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
CAKEY = SSLDIR + '/cakey.pem'
CACERT = SSLDIR + '/cacert.pem'
CACERTCRT = SSLDIR + '/cacert.crt'
CACERTB64 = CACERT + '.b64'
SERVERKEY = SSLDIR + '/server.key.pem'
SERVERCERT = SSLDIR + '/server.cert.pem'
FWKEY = SSLDIR + '/firewall.key.pem'
FWCERT = SSLDIR + '/firewall.cert.pem'
FWKEYB64 = FWKEY + '.b64'
FWCERTB64 = FWCERT + '.b64'
MAILKEY = SSLDIR + '/mail.key.pem'
MAILCERT = SSLDIR + '/mail.cert.pem'
SSHPUBKEY = '/root/.ssh/id_rsa.pub'
SSHPUBKEYB64 = SSHPUBKEY + '.b64'
SECRETDIR = SYSDIR + '/.secret'
BINDUSERSECRET = SECRETDIR + '/global-binduser'
SOPHADMINSECRET = SECRETDIR + '/sophomorix-admin'
ADADMINSECRET = SECRETDIR + '/administrator'
CAKEYSECRET = SECRETDIR + '/cakey'
LIBDIR = '/usr/lib/linuxmuster'
SHAREDIR = '/usr/share/linuxmuster'
EXAMPLEDIR = SHAREDIR + '/examples'
CACHEDIR = '/var/cache/linuxmuster'
VARDIR = '/var/lib/linuxmuster'
LOGDIR = '/var/log/linuxmuster'
SETUPLOG = LOGDIR + '/setup.log'
SETUPDIR = LIBDIR + '/setup.d'
TPLDIR = SHAREDIR + '/templates'
CUSTOMINI = CACHEDIR + '/custom.ini'
FWOSCONFTPL = SHAREDIR + '/firewall/opnsense/config.xml.tpl'
SETUPINI = VARDIR + '/setup.ini'
DEFAULTSINI = SHAREDIR + '/setupdefaults.ini'
LINBODIR = '/srv/linbo'
LINBOGRUBDIR = LINBODIR + '/boot/grub'
LINBOLOGDIR = LOGDIR + '/linbo'
LINBOSHAREDIR = SHAREDIR + '/linbo'
LINBOTPLDIR = LINBOSHAREDIR + '/templates'
LINBOCACHEDIR = CACHEDIR + '/linbo'
DHCPDEVCONF = '/etc/dhcp/devices.conf'
OPSIPXEFILE = 'linux/pxelinux.0'
MANAGEDSTR = '### managed by linuxmuster.net ###'

# grub stuff
GRUBCOMMONMODS = 'all_video boot chain configfile cpuid echo net ext2 extcmd fat \
gettext gfxmenu gfxterm gzio http ntfs linux linux16 loadenv minicmd net part_gpt \
part_msdos png progress read reiserfs search sleep terminal test tftp'
# arch specific netboot modules
GRUBEFIMODS = GRUBCOMMONMODS + ' efi_gop efi_uga efinet linuxefi'
GRUBI386MODS = GRUBCOMMONMODS + ' biosdisk gfxterm_background normal ntldr pxe'
GRUBISOMODS = 'iso9660 usb'
GRUBFONT = 'unicode'
