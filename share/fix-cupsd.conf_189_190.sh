#!/bin/bash
#
# fix-cupsd.conf_189_190.sh
#
# Patches a live /etc/cups/cupsd.conf with the fixes for
#   https://github.com/linuxmuster/linuxmuster-base7/issues/189
#     (missing "@printing" on the job-management Limit in Policy default,
#     breaking printing on cups >= 2.4.7-1.2ubuntu7.9)
#   https://github.com/linuxmuster/linuxmuster-base7/issues/190
#     (missing AuthType/Require user on <Location /admin/conf>, allowing
#     unauthenticated read/write access to the raw cupsd.conf)
#
# For hosts that were set up (or last had cupsd.conf regenerated) before
# these fixes landed in the cupsd.conf template. Each fix is only applied
# if it isn't already present, so this is safe to run repeatedly - a
# second run just reports that there is nothing left to do. Only ever
# touches the file if it finds the *exact* known pre-fix wording; if
# cupsd.conf has been customized in a way this script doesn't recognize,
# it leaves that part alone rather than guessing.
#
# thomas@linuxmuster.net
# 20260811
#

CUPSDCONF="/etc/cups/cupsd.conf"

if [ ! -s "$CUPSDCONF" ]; then
	echo "$CUPSDCONF not found, nothing to do!"
	exit 1
fi


# exit 0 if the #189 fix is still missing, 1 if it's already applied or
# the expected Limit block isn't found at all (nothing safe to do then)
check_189() {
	awk '
		/^<Policy default>/ { in_policy=1 }
		/^<\/Policy>/ { in_policy=0 }
		in_policy && /^[[:space:]]*<Limit Send-Document Send-URI/ { in_limit=1; seen_limit=1 }
		in_limit && /^[[:space:]]*<\/Limit>/ { in_limit=0 }
		in_limit && /^[[:space:]]*Require user @OWNER @SYSTEM @printing[[:space:]]*$/ { already=1 }
		in_limit && /^[[:space:]]*Require user @OWNER @SYSTEM[[:space:]]*$/ { seen_line=1 }
		END {
			if (!seen_limit || already) exit 1
			exit (seen_line ? 0 : 1)
		}
	' "$CUPSDCONF"
}


# exit 0 if the #190 fix is still missing, 1 if it's already applied or
# the <Location /admin/conf> block isn't found at all
check_190() {
	awk '
		/^<Location \/admin\/conf>/ { in_loc=1; seen_loc=1 }
		in_loc && /^[[:space:]]*AuthType Default[[:space:]]*$/ { has_auth=1 }
		in_loc && /^<\/Location>/ { in_loc=0 }
		END {
			if (!seen_loc || has_auth) exit 1
			exit 0
		}
	' "$CUPSDCONF"
}


# append "@printing" to the Require line inside Policy default's
# Send-Document/... Limit, preserving its original indentation
apply_189() {
	awk '
		/^<Policy default>/ { in_policy=1 }
		/^<\/Policy>/ { in_policy=0 }
		in_policy && /^[[:space:]]*<Limit Send-Document Send-URI/ { in_limit=1 }
		in_limit && /^[[:space:]]*<\/Limit>/ { in_limit=0 }
		in_limit && /^[[:space:]]*Require user @OWNER @SYSTEM[[:space:]]*$/ {
			match($0, /^[[:space:]]*/)
			print substr($0, 1, RLENGTH) "Require user @OWNER @SYSTEM @printing"
			next
		}
		{ print }
	' "$CUPSDCONF" > "$CUPSDCONF.tmp" && cat "$CUPSDCONF.tmp" > "$CUPSDCONF" && rm -f "$CUPSDCONF.tmp"
}


# insert AuthType/Require right after the <Location /admin/conf> opening tag
apply_190() {
	awk '
		/^<Location \/admin\/conf>/ {
			print
			print "  AuthType Default"
			print "  Require user @SYSTEM"
			next
		}
		{ print }
	' "$CUPSDCONF" > "$CUPSDCONF.tmp" && cat "$CUPSDCONF.tmp" > "$CUPSDCONF" && rm -f "$CUPSDCONF.tmp"
}


needs_189=0
needs_190=0
check_189 && needs_189=1
check_190 && needs_190=1

if [ "$needs_189" = 0 -a "$needs_190" = 0 ]; then
	echo "$CUPSDCONF already contains the fixes for #189 and #190, nothing to do."
	exit 0
fi

# back up before touching anything
timestamp="$(date +%Y%m%d%H%M)"
backup="$CUPSDCONF.$timestamp"
cp -a "$CUPSDCONF" "$backup" || exit 1
echo "Backed up $CUPSDCONF to $backup."

patched=""
if [ "$needs_189" = 1 ]; then
	echo "Applying fix for #189 (missing @printing on job-management Limit) ..."
	apply_189 || exit 1
	patched="$patched #189"
fi
if [ "$needs_190" = 1 ]; then
	echo "Applying fix for #190 (missing auth on /admin/conf) ..."
	apply_190 || exit 1
	patched="$patched #190"
fi

# note in the header what was patched and when
note="# patched by $(basename "$0") ($(date '+%Y-%m-%d %H:%M:%S')):$patched"
{ echo "$note"; cat "$CUPSDCONF"; } > "$CUPSDCONF.tmp" && cat "$CUPSDCONF.tmp" > "$CUPSDCONF" && rm -f "$CUPSDCONF.tmp"

echo "Done, patched:$patched"
echo "Restarting cups.service ..."
systemctl restart cups.service
