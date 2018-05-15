#!/usr/bin/python3
#
# create ssl certificates
# thomas@linuxmuster.net
# 20180515
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
certlist = [servername, 'firewall', 'mail', 'docker', 'opsi']

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

# iterate through certlist
for item in certlist:
    fqdn = item + '.' + domainname
    csrfile = constants.SSLDIR + '/' + item + '.csr'
    keyfile = constants.SSLDIR + '/' + item + '.key.pem'
    certfile = constants.SSLDIR + '/' + item + '.cert.pem'
    b64keyfile = keyfile + '.b64'
    b64certfile = certfile + '.b64'
    subj = subjbase + fqdn + '/'
    msg = 'Creating private ' + item + ' key & certificate '
    printScript(msg, '', False, False, True)
    try:
        subProc('openssl genrsa -out ' + keyfile + ' 2048', logfile)
        subProc('openssl req -batch ' + subj + ' -new -key ' + keyfile + ' -out ' + csrfile, logfile)
        subProc('openssl x509 -req -in ' + csrfile + ' -CA ' + constants.CACERT + passin + ' -CAkey ' + constants.CAKEY + ' -CAcreateserial -out ' + certfile + shadays, logfile)
        # cert links for cups on server
        if item == servername:
            subProc('ln -sf ' + certfile + ' /etc/cups/ssl/server.crt', logfile)
            subProc('ln -sf ' + keyfile + ' /etc/cups/ssl/server.key', logfile)
            subProc('service cups restart', logfile)
        if item == 'firewall':
            # create base64 encoded version for opnsense's config.xml
            subProc('base64 ' + keyfile + ' > ' + b64keyfile, logfile)
            subProc('base64 ' + certfile + ' > ' + b64certfile, logfile)
            rc = replaceInFile(b64keyfile, '\n', '')
            rc = replaceInFile(b64certfile, '\n', '')
        printScript( 'Success!', '', True, True, False, len(msg))
    except:
        printScript(' Failed!', '', True, True, False, len(msg))
        sys.exit(1)

# concenate firewall fullchain cert
subProc('cat ' + constants.FWFULLCHAIN.replace('.fullchain.', '.cert.') + ' ' + constants.CACERT + ' > ' + constants.FWFULLCHAIN, logfile)

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
