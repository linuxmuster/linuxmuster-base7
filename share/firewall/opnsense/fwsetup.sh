#!/bin/sh
#
# install extensions and reboot
# thomas@linuxmuster.net
# 20240210
#

# install extensions
extensions="os-web-proxy-sso os-freeradius os-api-backup"
for item in $extensions; do
  pkg install -y $item
done

if [ -s /tmp/opnsense.xml ]; then
  # copy setup config
  cp /tmp/opnsense.xml /conf/config.xml

  # reboot finally
  reboot
fi