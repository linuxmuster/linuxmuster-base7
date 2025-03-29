#!/usr/bin/python3
#
# create web proxy sso authentication config
# thomas@linuxmuster.net
# 20200311
#

import environment
import os
import sys

from functions import datetime
from functions import getSetupValue
from functions import printScript
from functions import readTextfile
from functions import writeTextfile


now = str(datetime.datetime.now()).split('.')[0]
printScript('create-auth-config.py ' + now)


# get setup values
printScript('Reading setup values.')
servername = getSetupValue('servername')
domainname = getSetupValue('domainname')
realm = getSetupValue('realm')
rc, bindpw = readTextfile(environment.BINDUSERSECRET)
if not rc:
    sys.exit(1)

# read config template
printScript('Reading config template.')
rc, content = readTextfile(environment.FWAUTHCFG)
if not rc:
    sys.exit(1)

# replace placeholders
content = content.replace('@@servername@@', servername)
content = content.replace('@@domainname@@', domainname)
content = content.replace('@@realm@@', realm)
content = content.replace('@@bindpw@@', bindpw)

# write outfile
outfile = '/tmp/' + os.path.basename(environment.FWAUTHCFG)
printScript('Writing ' + outfile + '.')
rc = writeTextfile(outfile, content, 'w')
if not rc:
    printScript('Error writing file.')
    sys.exit(1)
else:
    printScript('Finished successfully.')
