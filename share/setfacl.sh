#!/bin/sh
#
# /usr/share/linuxmuster/setfacl.sh user:group aclstring path
#
# thomas@linuxmuster.net
# 20180627
#

[ -n "$1" ] || exit 1
[ -n "$2" ] || exit 1
[ -e "$3" ] || exit 1

chown "$1" "$3"
setfacl -m "$2" "$3"
