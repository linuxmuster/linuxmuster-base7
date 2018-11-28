REM /var/lib/samba/sysvol/@@domainname@@/scripts/default-school/windows/login.cmd
REM
REM example netlogon script for windows
REM
REM thomas@linuxmuster.net
REM 20181128
REM

C:

set NUOPT=/PERSISTENT:NO
REM set NUOPT=/PERSISTENT:YES
net use * /DELETE /YES

REM home
net use %HOMEDRIVE% %HOMESHARE% /YES %NUOPT% > NUL

REM pgm
net use K: \\%USERDNSDOMAIN%\pgm /YES %NUOPT% > NUL

REM share
net use T: \\%USERDNSDOMAIN%\share /YES %NUOPT% > NUL

REM cdrom
net use R: \\%USERDNSDOMAIN%\cdrom /YES %NUOPT% > NUL
