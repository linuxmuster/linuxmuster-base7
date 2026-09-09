#!/bin/bash
#
# Filename     : fix-systemd-resolved_203.sh
# Description  : Repair systemd-resolved/systemd-networkd-wait-online.service
#                on a running Samba AD DC (issue #203)
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260909
#

# linuxmuster-release-upgrade used to mask systemd-resolved.service and
# systemd-networkd-wait-online.service outright to keep systemd-resolved's
# DNS stub listener off port 53 (which conflicts with samba-ad-dc's own
# DNS server). Verified on two independent production systems (beta forum
# https://ask.linuxmuster.net/t/beta-test-linuxmuster-net-7-4/12176/226)
# that just disabling the stub listener via a drop-in is enough, and
# cleaner - both services stay enabled, matching Ubuntu's standard setup.
#
# This repairs hosts that already went through the old (masking) upgrade
# script, and proactively brings any Samba AD DC to the same, correct
# state regardless of how it got here. Safe to run repeatedly: reports
# "nothing to do" and exits once the fix is already applied.
#
# samba-ad-dc itself is deliberately NOT restarted here (unlike during
# the release upgrade, where all three start from scratch in sequence) -
# it's already bound to port 53 and running on a live system, and
# restarting it would cause a needless AD/DNS outage. Only
# systemd-resolved and systemd-networkd-wait-online.service need to be
# fixed and restarted for the port conflict to go away.

set -e

STUB_DROPIN="/etc/systemd/resolved.conf.d/no-stub.conf"

# only relevant on a Samba AD DC - that's the only reason to touch
# systemd-resolved's DNS stub listener at all
if ! systemctl list-unit-files samba-ad-dc.service &>/dev/null; then
	echo "samba-ad-dc.service not found, nothing to do."
	exit 0
fi

is_masked() {
	[ "$(systemctl is-enabled "$1" 2>/dev/null)" = "masked" ]
}

needs_fix=0
is_masked systemd-resolved.service && needs_fix=1
is_masked systemd-networkd-wait-online.service && needs_fix=1
grep -qx "DNSStubListener=no" "$STUB_DROPIN" 2>/dev/null || needs_fix=1

if [ "$needs_fix" = 0 ]; then
	echo "systemd-resolved and systemd-networkd-wait-online.service already correctly configured, nothing to do."
	exit 0
fi

echo "Fixing systemd-resolved/systemd-networkd-wait-online.service configuration (#203) ..."

systemctl unmask systemd-resolved.service systemd-networkd-wait-online.service
systemctl enable systemd-resolved.service systemd-networkd-wait-online.service

mkdir -p "$(dirname "$STUB_DROPIN")"
cat << _EOF > "$STUB_DROPIN"
[Resolve]
DNSStubListener=no
_EOF

echo "Restarting systemd-resolved.service ..."
systemctl restart systemd-resolved.service
echo "Restarting systemd-networkd-wait-online.service ..."
systemctl restart systemd-networkd-wait-online.service

echo "Done: systemd-resolved's DNS stub listener is disabled, both units are enabled, samba-ad-dc keeps port 53 to itself."