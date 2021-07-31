# defaults.sh
#
# thomas@linuxmuster.net
# GPL v3
# 20210731
#
# sources system constants and setup values for shell scripts

# read constants
CONSTANTS="/usr/lib/linuxmuster/constants.py"
eval "$(sed -e :a -e '/\\$/N; s/\\\n//; ta' "$CONSTANTS" | grep ^'[A-Z]' | \
        sed "s| = |=|g
             s| + ||g
             s|=\([A-Z]\)|=$\1|g
             s|\[||g
             s|\]||g
             s|\([A-Z]\)=|\1=|g")"

# read setup values
if [ -e "$SETUPINI" ]; then
 eval "$(grep ^'[a-z]' "$SETUPINI" | sed 's| = |="|g' | sed 's|$|"|g')"
fi

# get linbo-version
LINBOVERSION="$(awk '{print $2}' "$LINBOVERFILE" | awk -F: '{print $1}')"
