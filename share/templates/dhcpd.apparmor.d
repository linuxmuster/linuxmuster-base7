# /etc/apparmor.d/local/usr.sbin.dhcpd
#
# thomas@linuxmuster.net
# 20200415
#

{
	/usr/lib/linuxmuster/dhcpd-update-samba-dns.py Ux,
}
