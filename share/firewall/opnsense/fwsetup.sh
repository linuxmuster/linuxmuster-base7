#!/bin/sh
#
# install extensions and reboot
# thomas@linuxmuster.net
# 20200311
#

# install extensions
extensions="os-web-proxy-sso os-freeradius os-api-backup"
for item in $extensions; do
  pkg install -y $item
done

# reboot
configctl firmware reboot
