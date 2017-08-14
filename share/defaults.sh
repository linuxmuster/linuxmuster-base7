# defaults.sh
#
# thomas@linuxmuster.net
# GPL v3
# 20170812
#
# sources system constants and setup values for shell scripts

# read constants
CONSTANTS="/usr/lib/linuxmuster/constants.py"
eval "$(sed -e :a -e '/\\$/N; s/\\\n//; ta' "$CONSTANTS" | grep ^[A-Z] | \
        sed "s| = |=|g
             s| + ||g
             s|=\([A-Z]\)|=$\1|g
             s|\[||g
             s|\]||g
             s|\([A-Z]\)=|\1=|g")"

# read setup values
if [ -e "$SETUPINI" ]; then
 eval "$(grep ^[a-z] "$SETUPINI" | sed 's| = |="|g' | sed 's|$|"|g')"
fi
