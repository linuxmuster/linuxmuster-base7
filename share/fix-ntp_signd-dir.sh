#!/bin/bash
#
# fix ntp_signd directory
# use this at your own risk
# 
# thomas@linuxmuster.net
# 20220912
#

# get environment
source /usr/share/linuxmuster/defaults.sh

# additional variables
NTPSOCKDIR_OLD="${NTPSOCKDIR/\/var\/lib\//\/run\/}"
conffiles="/etc/ntp.conf /etc/samba/smb.conf"
services="apparmor ntp samba-ad-dc"
timestamp="$(date +%Y%m%d%H%M)"

# provide ntpd apparmor override file
ntpd_template="$TPLDIR/ntpd.apparmor.d"
ntpd_target="$(head -1 $ntpd_template | awk '{print $2}')"
ntpd_dir="$(dirname $ntpd_target)"
if [ ! -d "$ntpd_dir" ]; then
    echo "$ntpd_dir does not exist!"
    exit 1
fi
echo "Providing $ntpd_target ..."
cp "$ntpd_template" "$ntpd_target"

# create socket directory
echo "Creating $NTPSOCKDIR ..."
mkdir -p "$NTPSOCKDIR"
chgrp ntp "$NTPSOCKDIR"
chmod 640 "$NTPSOCKDIR"

# patch config files
for item in $conffiles; do
    echo "Patching $item ..."
    cp "$item" "$item.$timestamp"
    sed -i "s|$NTPSOCKDIR_OLD|$NTPSOCKDIR|g" "$item"
done

# restart services
for item in $services; do
    echo "Restarting $item.service ..."
    systemctl restart "$item.service"
done

echo "Done!"