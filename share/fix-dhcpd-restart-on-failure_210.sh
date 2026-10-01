#!/bin/bash
#
# Filename     : fix-dhcpd-restart-on-failure_210.sh
# Description  : Make isc-dhcp-server retry when it fails at boot (issue #210)
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20261001
#

# At boot isc-dhcp-server can start before the server's static address is
# configured and then exits with "Not configured to listen on any
# interfaces!". The unit has no Restart= so dhcpd stays down. The package
# ships /usr/lib/systemd/system/isc-dhcp-server.service.d/linuxmuster.conf
# (Restart=on-failure, RestartSec=5); this script brings an existing host to
# the same state on package upgrade, regardless of how it got here:
#
# - reloads systemd so the shipped drop-in takes effect (also needed when
#   the drop-in is already there but was not loaded yet)
# - writes the same drop-in to /etc as a fallback if the unit still has no
#   Restart= after that (e.g. the shipped file is missing)
# - starts isc-dhcp-server if it is in the failed state right now, i.e. it
#   died at the last boot. A unit that was stopped on purpose is not
#   "failed" and is left alone.
#
# Safe to run repeatedly: reports "nothing to do" and exits once the fix is
# already applied. A running dhcpd is deliberately NOT restarted - that
# would only drop leases/offers for no gain, Restart= applies on its next
# failure.

set -e

UNIT="isc-dhcp-server.service"
DROPIN="/etc/systemd/system/${UNIT}.d/linuxmuster.conf"

if ! systemctl cat "$UNIT" &>/dev/null; then
	echo "$UNIT not found, nothing to do."
	exit 0
fi

# pick up a freshly shipped drop-in before judging the effective state
systemctl daemon-reload

has_restart() {
	case "$(systemctl show -p Restart --value "$UNIT" 2>/dev/null)" in
		on-failure|always) return 0 ;;
		*) return 1 ;;
	esac
}

needs_fix=0
has_restart || needs_fix=1
systemctl is-failed --quiet "$UNIT" && needs_fix=1

if [ "$needs_fix" = 0 ]; then
	echo "$UNIT already restarts on failure, nothing to do."
	exit 0
fi

echo "Fixing $UNIT restart behaviour (#210) ..."

if ! has_restart; then
	mkdir -p "$(dirname "$DROPIN")"
	cat << _EOF > "$DROPIN"
[Service]
Restart=on-failure
RestartSec=5
_EOF
	systemctl daemon-reload
fi

if systemctl is-failed --quiet "$UNIT"; then
	echo "Starting $UNIT, which failed earlier ..."
	systemctl reset-failed "$UNIT"
	systemctl start "$UNIT"
fi

echo "Done: $UNIT restarts on failure."
