#!/usr/bin/python3
#
# create ssl certificates
# thomas@linuxmuster.net
# 20240219
#

from __future__ import print_function

import configparser
import constants
import glob
import os
import subprocess
import sys

from functions import createServerCert, mySetupLogfile, randomPassword
from functions import replaceInFile, printScript, subProc, writeTextfile

logfile = mySetupLogfile(__file__)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.RawConfigParser(
        delimiters=('='), inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    schoolname = setup.get('setup', 'schoolname')
    servername = setup.get('setup', 'servername')
    domainname = setup.get('setup', 'domainname')
    sambadomain = setup.get('setup', 'sambadomain')
    skipfw = setup.getboolean('setup', 'skipfw')
    realm = setup.get('setup', 'realm')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# basic subject string
subjbase = '-subj /O="' + schoolname + '"/OU=' + sambadomain + '/CN='

# substring with sha and validation duration
shadays = ' -sha256 -days 3650'

# ca key password & string
cakeypw = randomPassword(16)
passin = ' -passin pass:' + cakeypw

# create ca stuff
msg = 'Creating private CA key & certificate '
subj = subjbase + realm + '/subjectAltName=' + realm + '/'
printScript(msg, '', False, False, True)
try:
    writeTextfile(constants.CAKEYSECRET, cakeypw, 'w')
    os.chmod(constants.CAKEYSECRET, 0o400)
    subProc('openssl genrsa -out ' + constants.CAKEY
            + ' -aes128 -passout pass:' + cakeypw + ' 2048', logfile)
    subProc('openssl req -batch -x509 ' + subj + ' -new -nodes ' + passin
            + ' -key ' + constants.CAKEY + shadays + ' -out ' + constants.CACERT, logfile)
    subProc('openssl x509 -in ' + constants.CACERT
            + ' -inform PEM -out ' + constants.CACERTCRT, logfile)
    # install crt
    subProc('ln -sf ' + constants.CACERTCRT
            + ' /usr/local/share/ca-certificates/linuxmuster_cacert.crt', logfile)
    subProc('update-ca-certificates', logfile)
    # create base64 encoded version for opnsense's config.xml
    cacertb64 = subprocess.check_output(['base64', constants.CACERT]).decode('utf-8').replace('\n', '')
    writeTextfile(constants.CACERTB64, cacertb64, 'w')
    if not os.path.isfile(constants.CACERTB64):
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# create server and firewall certificates
for item in [servername, 'firewall']:
    if skipfw and item == 'firewall':
        # no cert for firewall if skipped by setup option
        continue
    createServerCert(item, logfile)


# copy cacert.pem to sysvol for clients
sysvoltlsdir = constants.SYSVOLTLSDIR.replace('@@domainname@@', domainname)
sysvolpemfile = sysvoltlsdir + '/' + os.path.basename(constants.CACERT)
subProc('mkdir -p ' + sysvoltlsdir, logfile)
subProc('cp ' + constants.CACERT + ' ' + sysvolpemfile, logfile)

# permissions
msg = 'Ensure key and certificate permissions '
printScript(msg, '', False, False, True)
try:
    subProc('chgrp -R ssl-cert ' + constants.SSLDIR, logfile)
    os.chmod(constants.SSLDIR, 0o750)
    for file in glob.glob(constants.SSLDIR + '/*'):
        os.chmod(file, 0o640)
    for file in glob.glob(constants.SSLDIR + '/*key*'):
        os.chmod(file, 0o600)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
