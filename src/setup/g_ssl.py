#!/usr/bin/python3
#
# create ssl certificates
# thomas@linuxmuster.net
# 20251112
#

"""
Setup module g_ssl: Generate SSL/TLS certificates for server and services.

This module:
- Creates root CA (Certificate Authority) for the domain
- Generates server certificate signed by CA
- Creates firewall certificate for OPNsense
- Generates OPSI certificate if OPSI is enabled
- Encodes certificates to base64 for configuration files
- Sets proper file permissions (600 for private keys)
- Stores certificates in /etc/linuxmuster/ssl/

Certificates are valid for the number of days defined in CERT_VALIDITY_DAYS
and are essential for secure LDAP, HTTPS, and other encrypted services.
"""

from __future__ import print_function

import configparser
import datetime
import glob
import os
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from functions import createServerCert, encodeCertToBase64, mySetupLogfile, \
    randomPassword, printScript, writeTextfile
from setup.helpers import runWithLog, CERT_VALIDITY_DAYS

logfile = mySetupLogfile(__file__)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = environment.SETUPINI
try:
    setup = configparser.RawConfigParser(delimiters=('='))
    setup.read(setupini)
    schoolname = setup.get('setup', 'schoolname')
    servername = setup.get('setup', 'servername')
    domainname = setup.get('setup', 'domainname')
    sambadomain = setup.get('setup', 'sambadomain')
    skipfw = setup.getboolean('setup', 'skipfw')
    realm = setup.get('setup', 'realm')
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# basic subject string
subjbase = '/O="' + schoolname + '"/OU=' + sambadomain + '/CN='

# substring with sha and validation duration
days = str(CERT_VALIDITY_DAYS)
shadays = ' -sha256 -days ' + days

# ca key password & string
cakeypw = randomPassword(16)
passin = ' -passin pass:' + cakeypw

# create ca stuff
msg = 'Creating private CA key & certificate '
subj = subjbase + realm + '/subjectAltName=' + realm + '/'
printScript(msg, '', False, False, True)
try:
    writeTextfile(environment.CAKEYSECRET, cakeypw, 'w')
    os.chmod(environment.CAKEYSECRET, 0o400)
    runWithLog(['openssl', 'genrsa', '-out', environment.CAKEY, '-aes128',
                '-passout', 'pass:' + cakeypw, '2048'],
               logfile, checkErrors=False, maskSecrets=[cakeypw])
    # Parse subj for openssl req
    runWithLog(['openssl', 'req', '-batch', '-x509', '-subj', subj, '-new', '-nodes',
                '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                '-sha256', '-days', days, '-out', environment.CACERT],
               logfile, checkErrors=False, maskSecrets=[cakeypw])
    runWithLog(['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                '-out', environment.CACERTCRT],
               logfile, checkErrors=False)
    # install crt
    runWithLog(['ln', '-sf', environment.CACERTCRT,
                '/usr/local/share/ca-certificates/linuxmuster_cacert.crt'],
               logfile, checkErrors=False)
    runWithLog(['update-ca-certificates'], logfile, checkErrors=False)
    # create base64 encoded version for opnsense's config.xml using shared function
    if not encodeCertToBase64(environment.CACERT, environment.CACERTB64):
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)

# create server and firewall certificates
for item in [servername, 'firewall']:
    if skipfw and item == 'firewall':
        # no cert for firewall if skipped by setup option
        continue
    createServerCert(item, days, logfile)


# copy cacert.pem to sysvol for clients
sysvoltlsdir = environment.SYSVOLTLSDIR.replace('@@domainname@@', domainname)
sysvolpemfile = sysvoltlsdir + '/' + os.path.basename(environment.CACERT)
runWithLog(['mkdir', '-p', sysvoltlsdir], logfile, checkErrors=False)
runWithLog(['cp', environment.CACERT, sysvolpemfile], logfile, checkErrors=False)

# permissions
msg = 'Ensure key and certificate permissions '
printScript(msg, '', False, False, True)
try:
    runWithLog(['chgrp', '-R', 'ssl-cert', environment.SSLDIR],
               logfile, checkErrors=False)
    os.chmod(environment.SSLDIR, 0o750)
    for file in glob.glob(environment.SSLDIR + '/*'):
        os.chmod(file, 0o640)
    for file in glob.glob(environment.SSLDIR + '/*key*'):
        os.chmod(file, 0o600)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)