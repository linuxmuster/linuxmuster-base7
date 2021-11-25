#!/bin/sh
# /etc/profile.d/Z99-linuxmuster.sh
#
# thomas@linuxmuster.net
# credits to joanna
# 20211125
#

upSeconds="$(/usr/bin/cut -d. -f1 /proc/uptime)"
secs=$((${upSeconds}%60))
mins=$((${upSeconds}/60%60))
hours=$((${upSeconds}/3600%24))
days=$((${upSeconds}/86400))
UPTIME=`printf "%d days, %02dh%02dm%02ds" "$days" "$hours" "$mins" "$sec"`
MEM=`free -m | awk 'NR==2{printf "%s/%sMB (%.2f", $3,$2,$3*100/$2 }'`
IPint=`ip a | grep glo | awk '{print $2}' | head -1 | cut -f1 -d/`
IPext=`wget -q -O - http://icanhazip.com/ | tail`
VRESIONbase7=`dpkg --status linuxmuster-base7 | grep ^Version | awk '{print $2}'`
VERSIONlinbo7=`dpkg --status linuxmuster-linbo7 | grep ^Version | awk '{print $2}'`
VERSIONwebui7=`dpkg --status linuxmuster-webui7 | grep ^Version | awk '{print $2}'`
VERSIONsophomorix=`dpkg --status sophomorix-samba | grep ^Version | awk '{print $2}'`


printf "\e[38;5;208m
  ███               ███      \e[4m\e[38;5;15mWELCOME TO LINUXMUSTER.NET 7.1 - prerelease\e[38;5;208m\e[24m
 █████             █████    \e[38;5;15m `date +"%A, %e %B %Y, %T"`\e[38;5;208m
  ███               ███
      ███       ███         \e[38;5;15m Uptime..........: \e[38;5;208m${UPTIME}\e[38;5;208m
     █████     █████        \e[38;5;15m Memory..........: \e[38;5;208m${MEM}"%%\)"\e[38;5;208m
      ███       ███         \e[38;5;15m IP Internal.....: \e[38;5;208m${IPint}\e[38;5;24m
           ███              \e[38;5;15m IP External.....: \e[38;5;208m${IPext}\e[38;5;24m
          █████
           ███              \e[38;5;208m
      ███       ███         \e[38;5;15m linuxmuster.net packages:\e[38;5;208m
     █████     █████        \e[38;5;15m -Base...........: \e[38;5;208m${VRESIONbase7}
      ███       ███         \e[38;5;15m -Linbo..........: \e[38;5;208m${VERSIONlinbo7}\e[38;5;208m
  ███               ███     \e[38;5;15m -WebUI..........: \e[38;5;208m${VERSIONwebui7}\e[38;5;208m
 █████             █████    \e[38;5;15m -Sophomorix.....: \e[38;5;208m${VERSIONsophomorix}\e[38;5;208m
  ███               ███
\e[0m
"
