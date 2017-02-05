#!/usr/bin/python3
#
# g_ssl.py
# thomas@linuxmuster.net
# 20170205
#

"""
Create certificates and private keys for the 'simple' example.
from https://github.com/pyca/pyopenssl/blob/master/examples/mk_simple_certs.py
"""

from __future__ import print_function

import configparser
import constants
import os

from OpenSSL import crypto
from certgen import (
    createKeyPair,
    createCertRequest,
    createCertificate,
)
from functions import printScript

printScript('', 'begin')
printScript(os.path.basename(__file__))

# read INIFILE
i = configparser.ConfigParser()
i.read(constants.SETUPINI)
schoolname = i.get('setup', 'schoolname')
servername = i.get('setup', 'servername')

ssldir = constants.SSLDIR
caprivkeyfile = ssldir + '/CA.key'
cacertfile = ssldir + '/CA.crt'
srvprivkeyfile = ssldir + '/server.key'
srvcertfile = ssldir + '/server.crt'

cakey = createKeyPair(crypto.TYPE_RSA, 2048)
careq = createCertRequest(cakey, CN=schoolname)
# CA certificate is valid for five years.
cacert = createCertificate(careq, (careq, cakey), 0, (0, 60*60*24*365*5))

print('Creating Certificate Authority private key in "' + caprivkeyfile + '".')
with open(caprivkeyfile, 'w') as capkey:
    capkey.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, cakey).decode('utf-8'))

print('Creating Certificate Authority certificate in "' + cacertfile + '".')
with open(cacertfile, 'w') as ca:
    ca.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cacert).decode('utf-8'))

pkey = createKeyPair(crypto.TYPE_RSA, 2048)
req = createCertRequest(pkey, CN=servername)
# Certificates are valid for ten years.
cert = createCertificate(req, (cacert, cakey), 1, (0, 60*60*24*365*10))

print('Creating Certificate ' + servername + ' private key in "' + srvprivkeyfile + '".')
with open(srvprivkeyfile, 'w') as leafpkey:
    leafpkey.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey).decode('utf-8'))

print('Creating Certificate ' + servername + ' certificate in "' + srvcertfile + '".')
with open(srvcertfile, 'w') as leafcert:
    leafcert.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8'))

# permissions
os.system('chgrp -R ssl-cert ' + ssldir)
os.system('chmod 750 ' + ssldir)
os.system('chmod 640 ' + ssldir + '/*')
os.system('chmod 600 ' + caprivkeyfile)
