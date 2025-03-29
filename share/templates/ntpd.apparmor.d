# /etc/apparmor.d/local/usr.sbin.ntpd
#
# thomas@linuxmuster.net
# 20250328
#

# samba4 ntp signing socket
/var/lib/samba/ntp_signd/socket rw,
