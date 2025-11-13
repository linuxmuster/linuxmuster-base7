#!/usr/bin/python3
#
# create ssl certificates
# thomas@linuxmuster.net
# 20251112
#

from __future__ import print_function

import configparser
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import glob
import os
import subprocess
import datetime
import sys

from linuxmuster_base7.functions import createServerCert, mySetupLogfile, randomPassword, \
    printScript, writeTextfile

logfile = mySetupLogfile(__file__)

# Helper function to run command with logging
def run_with_log(cmd_list, cmd_desc, logfile):
    result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
    if logfile and (result.stdout or result.stderr):
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
            log.write('#### ' + cmd_desc + ' ####\n')
            if result.stdout:
                log.write(result.stdout)
            if result.stderr:
                log.write(result.stderr)
            log.write('-' * 78 + '\n')
    return result


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
days = '3650'
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
    run_with_log(['openssl', 'genrsa', '-out', environment.CAKEY, '-aes128',
                  '-passout', 'pass:' + cakeypw, '2048'],
                 'openssl genrsa -out ' + environment.CAKEY + ' -aes128 -passout pass:****** 2048',
                 logfile)
    # Parse subj for openssl req
    run_with_log(['openssl', 'req', '-batch', '-x509', '-subj', subj, '-new', '-nodes',
                  '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                  '-sha256', '-days', days, '-out', environment.CACERT],
                 'openssl req -batch -x509 ... -out ' + environment.CACERT,
                 logfile)
    run_with_log(['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                  '-out', environment.CACERTCRT],
                 'openssl x509 -in ' + environment.CACERT + ' -inform PEM -out ' + environment.CACERTCRT,
                 logfile)
    # install crt
    run_with_log(['ln', '-sf', environment.CACERTCRT,
                  '/usr/local/share/ca-certificates/linuxmuster_cacert.crt'],
                 'ln -sf ' + environment.CACERTCRT + ' /usr/local/share/ca-certificates/linuxmuster_cacert.crt',
                 logfile)
    run_with_log(['update-ca-certificates'], 'update-ca-certificates', logfile)
    # create base64 encoded version for opnsense's config.xml
    cacertb64 = subprocess.check_output(['base64', '-w0', environment.CACERT]).decode('utf-8')
    writeTextfile(environment.CACERTB64, cacertb64, 'w')
    if not os.path.isfile(environment.CACERTB64):
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
run_with_log(['mkdir', '-p', sysvoltlsdir], 'mkdir -p ' + str(sysvoltlsdir), logfile)
run_with_log(['cp', environment.CACERT, sysvolpemfile], 'cp ' + str(environment.CACERT) + ' ' + str(sysvolpemfile), logfile)

# permissions
msg = 'Ensure key and certificate permissions '
printScript(msg, '', False, False, True)
try:
    run_with_log(['chgrp', '-R', 'ssl-cert', environment.SSLDIR],
                 'chgrp -R ssl-cert ' + environment.SSLDIR, logfile)
    os.chmod(environment.SSLDIR, 0o750)
    for file in glob.glob(environment.SSLDIR + '/*'):
        os.chmod(file, 0o640)
    for file in glob.glob(environment.SSLDIR + '/*key*'):
        os.chmod(file, 0o600)
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)