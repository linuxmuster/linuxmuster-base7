#!/usr/bin/python3
#
# g_ssl.py
# thomas@linuxmuster.net
# 20170212
#

"""
Create certificates and private keys for the 'simple' example.
from https://github.com/pyca/pyopenssl/blob/master/examples/mk_simple_certs.py
"""

from __future__ import print_function

import configparser
import constants
import os
import sys

from OpenSSL import crypto
from certgen import (
    createKeyPair,
    createCertRequest,
    createCertificate,
)
from functions import printScript
from functions import subProc

title = os.path.basename(__file__).replace('.py', '').split('_')[1]
logfile = constants.LOGDIR + '/setup.' + title + '.log'

printScript('', 'begin')
printScript(title)

# read setup ini
msg = 'Reading setup data '
printScript(msg, '', False, False, True)
setupini = constants.SETUPINI
try:
    setup = configparser.ConfigParser()
    setup.read(setupini)
    schoolname = setup.get('setup', 'schoolname')
    servername = setup.get('setup', 'servername')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# key & cert files to create
ssldir = constants.SSLDIR
caprivkeyfile = ssldir + '/CA.key'
cacertfile = ssldir + '/CA.crt'
srvprivkeyfile = ssldir + '/server.key'
srvcertfile = ssldir + '/server.crt'

# CA cert stuff
cakey = createKeyPair(crypto.TYPE_RSA, 2048)
careq = createCertRequest(cakey, CN=schoolname)
# CA certificate is valid for five years.
cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*5))

msg = 'Creating private CA key '
printScript(msg, '', False, False, True)
try:
    with open(caprivkeyfile, 'w') as capkey:
        capkey.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey).decode('utf-8'))
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

msg = 'Creating CA certificate '
printScript(msg, '', False, False, True)
try:
    with open(cacertfile, 'w') as ca:
        ca.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert).decode('utf-8'))
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# server cert stuff
pkey = createKeyPair(crypto.TYPE_RSA, 2048)
req = createCertRequest(pkey, CN=servername)
# Certificates are valid for ten years.
cert = createCertificate(req, (cacert, cakey), 1, (0, 60*60*24*365*10))

msg = 'Creating private server key '
printScript(msg, '', False, False, True)
try:
    with open(srvprivkeyfile, 'w') as leafpkey:
        leafpkey.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey).decode('utf-8'))
    printScript( 'Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

msg = 'Creating server certificate '
printScript(msg, '', False, False, True)
try:
    with open(srvcertfile, 'w') as leafcert:
        leafcert.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8'))
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# permissions
msg = 'Ensure key and certificate permissions '
printScript(msg, '', False, False, True)
try:
    subProc('chgrp -R ssl-cert ' + ssldir, logfile)
    subProc('chmod 750 ' + ssldir, logfile)
    subProc('chmod 640 ' + ssldir + '/*', logfile)
    subProc('chmod 600 ' + caprivkeyfile, logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
