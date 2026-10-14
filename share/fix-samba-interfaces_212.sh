#!/bin/bash
#
# Filename     : fix-samba-interfaces_212.sh
# Description  : Register only the server address as Samba DC DNS records (issue #212)
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20261014
#

# Without an "interfaces" option samba_dnsupdate registers the address of
# every interface as A record of the DC (server, domain, gc._msdcs,
# DomainDnsZones, ForestDnsZones and behind <GUID>._msdcs), including docker,
# libvirt or VPN bridges. Clients and replication partners then get
# addresses they cannot reach. The smb.conf template now sets
# "interfaces = lo <serverip>"; this script brings an existing server to the
# same state on package upgrade:
#
# - adds "interfaces = lo <serverip>" to the [global] section of
#   /etc/samba/smb.conf (backup in smb.conf.<timestamp>)
# - restarts samba-ad-dc and runs samba_dnsupdate --all-names, which also
#   deletes the records of the other addresses it registered before
#
# "bind interfaces only" is deliberately NOT set: samba keeps listening on
# all addresses, only the DNS registration changes.
#
# Safe to run repeatedly: does nothing if "interfaces" is already set, also
# when an admin set it in smb.conf.admin.

set -e

# get environment
source /usr/share/linuxmuster/environment.sh

SMBCONF="/etc/samba/smb.conf"
UNIT="samba-ad-dc.service"
timestamp="$(date +%Y%m%d%H%M)"

if [ ! -s "$SMBCONF" ] || ! grep -q "^\[global\]" "$SMBCONF"; then
	echo "$SMBCONF not configured, nothing to do."
	exit 0
fi

if [ -n "$(testparm -s --parameter-name=interfaces 2>/dev/null)" ]; then
	echo "Samba interfaces already configured, nothing to do."
	exit 0
fi

# the server address must exist on this host, otherwise samba would not
# register any address at all
if [ -z "$serverip" ] || ! ip -4 -o addr show | grep -q " inet ${serverip}/"; then
	echo "Server address \"$serverip\" not found on any interface, skipping."
	exit 1
fi

echo "Restricting Samba DNS registration to $serverip (#212) ..."
cp "$SMBCONF" "$SMBCONF.$timestamp"
sed -i "/^\[global\]/a interfaces = lo $serverip" "$SMBCONF"

if ! systemctl is-active --quiet "$UNIT"; then
	echo "Done: $UNIT is not running, DNS records are updated on its next start."
	exit 0
fi

echo "Restarting $UNIT ..."
systemctl restart "$UNIT"

# wait for the internal DNS server before updating the records
for i in $(seq 1 30); do
	host -t A "$servername.$domainname" 127.0.0.1 &>/dev/null && break
	sleep 1
done

echo "Updating DC DNS records ..."
samba_dnsupdate --all-names

echo "Done: Samba registers only $serverip in DNS."
