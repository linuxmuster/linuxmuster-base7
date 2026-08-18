#!/usr/bin/python3
#
# Filename     : certs.py
# Description  : SSL/TLS certificate generation, signing and renewal helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import datetime
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from .core import getSetupValue, printScript
from .files import readTextfile, catFiles


def encodeCertToBase64(certpath, outpath=None):
    """
    Encode certificate file to base64 format (for OPNsense config.xml).

    Args:
        certpath: Path to certificate file to encode
        outpath: Optional output path (defaults to certpath + '.b64')

    Returns:
        True on success, False on failure
    """
    if outpath is None:
        outpath = certpath + '.b64'
    try:
        with open(outpath, 'wb') as f:
            subprocess.run(['base64', '-w0', certpath], stdout=f, check=True)
        return True
    except Exception:
        return False


def renewCaCertificate(cacert_subject, days, logfile=None):
    """
    Renew CA certificate using password-protected CA key.

    Args:
        cacert_subject: OpenSSL subject string for CA certificate
        days: Certificate validity in days
        logfile: Optional path to log file

    Returns:
        True on success, False on failure
    """
    try:
        # Read CA key password
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        cakeypw = cakeypw.strip()

        # Renew CA certificate
        if logfile:
            with open(logfile, 'a') as log:
                subprocess.run(['openssl', 'req', '-batch', '-x509', cacert_subject, '-new', '-nodes',
                              '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                              '-sha256', '-days', str(days), '-out', environment.CACERT],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'req', '-batch', '-x509', cacert_subject, '-new', '-nodes',
                          '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                          '-sha256', '-days', str(days), '-out', environment.CACERT],
                         check=True, capture_output=True)

        # Convert to CRT format
        if logfile:
            with open(logfile, 'a') as log:
                subprocess.run(['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                              '-out', environment.CACERTCRT],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                          '-out', environment.CACERTCRT],
                         check=True, capture_output=True)

        return True
    except Exception:
        return False


def signCertificateWithCa(csrfile, certfile, days, cnffile, logfile=None):
    """
    Sign a certificate signing request (CSR) with the CA certificate.

    Args:
        csrfile: Path to CSR file
        certfile: Path where signed certificate will be written
        days: Certificate validity in days
        cnffile: Path to OpenSSL extension configuration file
        logfile: Optional path to log file

    Returns:
        True on success, False on failure
    """
    try:
        # Read CA key password
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        cakeypw = cakeypw.strip()

        # Sign certificate
        if logfile:
            with open(logfile, 'a') as log:
                subprocess.run(['openssl', 'x509', '-req', '-in', csrfile,
                              '-CA', environment.CACERT, '-passin', 'pass:' + cakeypw,
                              '-CAkey', environment.CAKEY, '-CAcreateserial',
                              '-out', certfile, '-sha256', '-days', str(days),
                              '-extfile', cnffile],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'x509', '-req', '-in', csrfile,
                          '-CA', environment.CACERT, '-passin', 'pass:' + cakeypw,
                          '-CAkey', environment.CAKEY, '-CAcreateserial',
                          '-out', certfile, '-sha256', '-days', str(days),
                          '-extfile', cnffile],
                         check=True, capture_output=True)

        return True
    except Exception:
        return False


def createCertificateChain(certfile, chainfile):
    """
    Create certificate chain by concatenating certificate and CA certificate.

    Args:
        certfile: Path to certificate file
        chainfile: Path where full chain will be written

    Returns:
        True on success, False on failure
    """
    try:
        catFiles([certfile, environment.CACERT], chainfile)
        return True
    except Exception:
        return False


def createCnfFromTemplate(cnf_tpl):
    """
    Create OpenSSL configuration file from template with variable replacement.

    Args:
        cnf_tpl: Path to configuration template file

    Returns:
        Path to created configuration file, or None on failure
    """
    try:
        # Read template file
        rc, filedata = readTextfile(cnf_tpl)

        # Replace placeholders with actual values
        replacements = {
            '@@domainname@@': getSetupValue('domainname'),
            '@@firewallip@@': getSetupValue('firewallip'),
            '@@realm@@': getSetupValue('realm'),
            '@@sambadomain@@': getSetupValue('sambadomain'),
            '@@schoolname@@': getSetupValue('schoolname'),
            '@@servername@@': getSetupValue('servername'),
            '@@serverip@@': getSetupValue('serverip'),
        }
        for placeholder, value in replacements.items():
            filedata = filedata.replace(placeholder, value)

        # Extract target path from first line
        firstline = filedata.split('\n')[0]
        cnf = firstline.partition(' ')[2]

        # Write configuration file
        with open(cnf, 'w') as outfile:
            outfile.write(filedata)

        return cnf
    except Exception:
        return None


# creates server cert
def createServerCert(item, days, logfile):
    domainname = getSetupValue('domainname')
    fqdn = item + '.' + domainname
    csrfile = environment.SSLDIR + '/' + item + '.csr'
    keyfile = environment.SSLDIR + '/' + item + '.key.pem'
    certfile = environment.SSLDIR + '/' + item + '.cert.pem'
    if item == 'firewall':
        cnffile = environment.SSLDIR + '/' + item + '_cert_ext.cnf'
    else:
        cnffile = environment.SSLDIR + '/server_cert_ext.cnf'
    fullchain = environment.SSLDIR + '/' + item + '.fullchain.pem'
    subj = '-subj /CN=' + fqdn + '/'
    shadays = ' -sha256 -days ' + days
    msg = 'Creating private ' + item + ' key & certificate '
    printScript(msg, '', False, False, True)
    try:
        # Generate RSA key
        result = subprocess.run(['openssl', 'genrsa', '-out', keyfile, '2048'],
                               capture_output=True, text=True, check=False)
        if logfile and (result.stdout or result.stderr):
            with open(logfile, 'a') as log:
                log.write('-' * 78 + '\n')
                log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
                log.write('#### openssl genrsa -out ' + keyfile + ' 2048 ####\n')
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write('-' * 78 + '\n')

        # Generate CSR
        result = subprocess.run(['openssl', 'req', '-batch', '-subj', '/CN=' + fqdn + '/',
                                '-new', '-key', keyfile, '-out', csrfile],
                               capture_output=True, text=True, check=False)
        if logfile and (result.stdout or result.stderr):
            with open(logfile, 'a') as log:
                log.write('-' * 78 + '\n')
                log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')
                log.write('#### openssl req -batch ... ####\n')
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write('-' * 78 + '\n')

        # Sign certificate using shared function
        if not signCertificateWithCa(csrfile, certfile, days, cnffile, logfile):
            raise Exception('Failed to sign certificate')

        # Create certificate chain using shared function
        if not createCertificateChain(certfile, fullchain):
            raise Exception('Failed to create certificate chain')

        if item == 'firewall':
            # create base64 encoded version for opnsense's config.xml
            encodeCertToBase64(keyfile)
            encodeCertToBase64(certfile)
        if item == 'server':
            # cert links for cups on server
            subprocess.run(['ln', '-sf', certfile, '/etc/cups/ssl/server.crt'], check=False)
            subprocess.run(['ln', '-sf', keyfile, '/etc/cups/ssl/server.key'], check=False)
            subprocess.run(['service', 'cups', 'restart'], check=False)
        printScript('Success!', '', True, True, False, len(msg))
        return True
    except Exception as error:
        printScript(f' Failed: {error}', '', True, True, False, len(msg))
        return False
