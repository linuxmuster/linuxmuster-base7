#!/usr/bin/python3
#
# Filename     : g_ssl.py
# Description  : Create SSL certificates
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260915
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

from linuxmuster_base7.functions import buildCaSubjectAndSan, createServerCert, \
    encodeCertToBase64, mySetupLogfile, randomPassword, printScript, writeCaCertificate, \
    writeSecretFile
from linuxmuster_base7.setup.helpers import runWithLog, CERT_VALIDITY_DAYS

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

# substring with sha and validation duration
days = str(CERT_VALIDITY_DAYS)

# ca key password
cakeypw = randomPassword(16)

# create ca stuff
msg = 'Creating private CA key & certificate '
# subj/addext construction and the actual req/CRT/trust-store handling are
# shared with renew_certs.py's CA renewal via functions/certs.py, so both
# stay in sync (#204: renewal used to build the DN/SAN differently, in a
# way that didn't work at all, and skipped installing the result into the
# system trust store)
subj, addext = buildCaSubjectAndSan(schoolname, sambadomain, realm)
printScript(msg, '', False, False, True)
try:
    writeSecretFile(environment.CAKEYSECRET, cakeypw, 0o400)
    runWithLog(['openssl', 'genrsa', '-out', environment.CAKEY, '-aes128',
                '-passout', 'pass:' + cakeypw, '2048'],
               logfile, checkErrors=False, maskSecrets=[cakeypw])
    if not writeCaCertificate(subj, addext, days, cakeypw, logfile):
        raise Exception('Failed to create CA certificate')
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