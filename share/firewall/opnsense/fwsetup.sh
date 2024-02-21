#!/bin/sh
#
# install extensions and reboot
# thomas@linuxmuster.net
# 20240212
#

# test if necessary files are present
[ -s /tmp/opnsense.xml -a -s /tmp/pre-auth.conf ] || exit 1

# install necessary extensions
pkg install -y os-squid os-web-proxy-sso os-freeradius || exit 1

# copy squid's pre-auth.conf in place
paconf="$(head -1 /tmp/pre-auth.conf | awk '{print $2}')"
padir="$(dirname "$paconf")"
[ -d "$padir" ] || mkdir -p "$padir"
cp /tmp/pre-auth.conf "$paconf" || exit 1

# copy setup config
cp /tmp/opnsense.xml /conf/config.xml || exit 1

# reboot finally
reboot
