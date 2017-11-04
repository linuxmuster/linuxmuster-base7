#!/usr/bin/python3
#
# create ssl certificates
# thomas@linuxmuster.net
# 20170813
#

from __future__ import print_function

import configparser
import constants
import os
import sys

from functions import randomPassword
from functions import replaceInFile
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
    setup = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
    setup.read(setupini)
    schoolname = setup.get('setup', 'schoolname')
    servername = setup.get('setup', 'servername')
    domainname = setup.get('setup', 'domainname')
    sambadomain = setup.get('setup', 'sambadomain')
    realm = setup.get('setup', 'realm')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# key & cert files to create
sfqdn = servername + '.' + domainname
ffqdn = 'firewall.' + domainname
mfqdn = 'mail.' + domainname

# basic subject string
subjbase = '-subj /O=' + schoolname + '/OU=' + sambadomain + '/CN='

# substring with sha and validation duration
shadays = ' -sha256 -days 3650'

# ca key password & string
cakeypw = randomPassword(16)
passin = ' -passin pass:' + cakeypw

# create ca stuff
msg = 'Creating private CA key & certificate '
subj = subjbase + realm + '/'
printScript(msg, '', False, False, True)
try:
    with open(constants.CAKEYSECRET, 'w') as secret:
        secret.write(cakeypw)
    subProc('chmod 400 ' + constants.CAKEYSECRET, logfile)
    subProc('openssl genrsa -out ' + constants.CAKEY + ' -aes128 -passout pass:' + cakeypw + ' 2048', logfile)
    subProc('openssl req -batch -x509 ' + subj + ' -new -nodes ' + passin + ' -key ' + constants.CAKEY + shadays + ' -out ' + constants.CACERT, logfile)
    subProc('openssl x509 -in ' + constants.CACERT + ' -inform PEM -out ' + constants.CACERTCRT, logfile)
    # install crt
    subProc('ln -sf ' + constants.CACERTCRT + ' /usr/local/share/ca-certificates/linuxmuster_cacert.crt', logfile)
    subProc('update-ca-certificates', logfile)
    # create base64 encoded version for opnsense's config.xml
    subProc('base64 ' + constants.CACERT + ' > ' + constants.CACERTB64, logfile)
    rc = replaceInFile(constants.CACERTB64, '\n', '')
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# server cert stuff
csrfile = constants.SSLDIR + '/server.csr'
subj = subjbase + sfqdn + '/'
msg = 'Creating private server key & certificate '
printScript(msg, '', False, False, True)
try:
    subProc('openssl genrsa -out ' + constants.SERVERKEY + ' 2048', logfile)
    subProc('openssl req -batch ' + subj + ' -new -key ' + constants.SERVERKEY + ' -out ' + csrfile, logfile)
    subProc('openssl x509 -req -in ' + csrfile + ' -CA ' + constants.CACERT + passin + ' -CAkey ' + constants.CAKEY + ' -CAcreateserial -out ' + constants.SERVERCERT + shadays, logfile)
    # cert links for cups
    subProc('ln -sf ' + constants.SERVERCERT + ' /etc/cups/ssl/server.crt', logfile)
    subProc('ln -sf ' + constants.SERVERKEY + ' /etc/cups/ssl/server.key', logfile)
    subProc('service cups restart', logfile)
    printScript( 'Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# firewall cert stuff
csrfile = constants.SSLDIR + '/firewall.csr'
subj = subjbase + ffqdn + '/'
msg = 'Creating private firewall key & certificate '
printScript(msg, '', False, False, True)
try:
    subProc('openssl genrsa -out ' + constants.FWKEY + ' 2048', logfile)
    subProc('openssl req -batch ' + subj + ' -new -key ' + constants.FWKEY + ' -out ' + csrfile, logfile)
    subProc('openssl x509 -req -in ' + csrfile + ' -CA ' + constants.CACERT + passin + ' -CAkey ' + constants.CAKEY + ' -CAcreateserial -out ' + constants.FWCERT + shadays, logfile)
    # create base64 encoded version for opnsense's config.xml
    subProc('base64 ' + constants.FWKEY + ' > ' + constants.FWKEYB64, logfile)
    subProc('base64 ' + constants.FWCERT + ' > ' + constants.FWCERTB64, logfile)
    rc = replaceInFile(constants.FWKEYB64, '\n', '')
    rc = replaceInFile(constants.FWCERTB64, '\n', '')
    printScript( 'Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# mail cert stuff
csrfile = constants.SSLDIR + '/mail.csr'
subj = subjbase + mfqdn + '/'
msg = 'Creating private mail key & certificate '
printScript(msg, '', False, False, True)
try:
    subProc('openssl genrsa -out ' + constants.MAILKEY + ' 2048', logfile)
    subProc('openssl req -batch ' + subj + ' -new -key ' + constants.MAILKEY + ' -out ' + csrfile, logfile)
    subProc('openssl x509 -req -in ' + csrfile + ' -CA ' + constants.CACERT + passin + ' -CAkey ' + constants.CAKEY + ' -CAcreateserial -out ' + constants.MAILCERT + shadays, logfile)
    printScript( 'Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)

# permissions
msg = 'Ensure key and certificate permissions '
printScript(msg, '', False, False, True)
try:
    subProc('chgrp -R ssl-cert ' + constants.SSLDIR, logfile)
    subProc('chmod 750 ' + constants.SSLDIR, logfile)
    subProc('chmod 640 ' + constants.SSLDIR + '/*', logfile)
    subProc('chmod 600 ' + constants.SSLDIR + '/*key*', logfile)
    printScript(' Success!', '', True, True, False, len(msg))
except:
    printScript(' Failed!', '', True, True, False, len(msg))
    sys.exit(1)
