#!/usr/bin/python3
#
# Filename     : certs.py
# Description  : SSL/TLS certificate generation, signing and renewal helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260915
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


def buildCaSubjectAndSan(schoolname, sambadomain, realm):
    """
    Build the CA certificate's Distinguished Name and SAN extension value.

    Shared by both initial CA creation (g_ssl.py) and CA renewal
    (renew_certs.py), so the DN/SAN format only needs to change in one
    place. Returns a plain DN string (no "-subj" flag baked in - pass it
    to openssl req's own -subj argument) and a value for -addext, the
    correct way to add a SAN to a self-signed (req -x509) certificate (a
    previous version baked "-subj " plus a bogus "/subjectAltName=.../"
    RDN into a single string, which not only produced no real SAN
    extension but - once also passed as a single subprocess.run() list
    element instead of separate arguments - made openssl fail outright).

    Args:
        schoolname: School/organization name (O=)
        sambadomain: Samba/AD domain (OU=)
        realm: Kerberos realm (CN=, and the SAN's DNS name)

    Returns:
        (subj, addext) tuple
    """
    subj = f'/O="{schoolname}"/OU={sambadomain}/CN={realm}/'
    addext = f'subjectAltName=DNS:{realm}'
    return subj, addext


def writeCaCertificate(subj, addext, days, cakeypw, logfile=None):
    """
    Self-sign the CA certificate with the (already existing) CA key, then
    install it as a trusted system CA.

    Shared by both initial CA creation (g_ssl.py, right after generating
    a fresh CAKEY) and CA renewal (renewCaCertificate() below, reusing
    the existing CAKEY) - the actual cert/trust-store handling is
    identical either way, only how CAKEY/cakeypw came to exist differs.
    Consolidating this avoids exactly the kind of divergence that let
    CA renewal skip the trust-store update below for a long time (#204).

    Args:
        subj: OpenSSL Distinguished Name string, see buildCaSubjectAndSan()
        addext: value for openssl's -addext flag, see buildCaSubjectAndSan()
        days: Certificate validity in days
        cakeypw: CA private key password
        logfile: Optional path to log file

    Returns:
        True on success, False on failure
    """
    try:
        req_cmd = ['openssl', 'req', '-batch', '-x509', '-subj', subj, '-new', '-nodes',
                   '-passin', 'pass:' + cakeypw, '-key', environment.CAKEY,
                   '-addext', addext,
                   '-sha256', '-days', str(days), '-out', environment.CACERT]
        crt_cmd = ['openssl', 'x509', '-in', environment.CACERT, '-inform', 'PEM',
                   '-out', environment.CACERTCRT]
        # symlink the freshly written CRT into the system CA trust store and
        # refresh it, so clients on this host trust the new CA immediately -
        # renewCaCertificate() used to skip this entirely (#204)
        install_cmd = ['ln', '-sf', environment.CACERTCRT,
                        '/usr/local/share/ca-certificates/linuxmuster_cacert.crt']
        update_cmd = ['update-ca-certificates']

        if logfile:
            with open(logfile, 'a') as log:
                for cmd in (req_cmd, crt_cmd, install_cmd, update_cmd):
                    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            for cmd in (req_cmd, crt_cmd, install_cmd, update_cmd):
                subprocess.run(cmd, check=True, capture_output=True)

        return True
    except Exception:
        return False


def renewCaCertificate(subj, addext, days, logfile=None):
    """
    Renew CA certificate using the existing, password-protected CA key.

    Args:
        subj: OpenSSL Distinguished Name string, see buildCaSubjectAndSan()
        addext: value for openssl's -addext flag, see buildCaSubjectAndSan()
        days: Certificate validity in days
        logfile: Optional path to log file

    Returns:
        True on success, False on failure
    """
    try:
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        cakeypw = cakeypw.strip()
    except Exception:
        return False

    return writeCaCertificate(subj, addext, days, cakeypw, logfile)


def signCertificateWithCa(csrfile, certfile, days, cnffile, logfile=None):
    """
    Sign a certificate signing request (CSR) with the CA certificate.

    Args:
        csrfile: Path to CSR file
        certfile: Path where signed certificate will be written
        days: Certificate validity in days
        cnffile: Path to OpenSSL extension configuration file - its
            subjectAltName/keyUsage/extendedKeyUsage live under a named
            [req_ext] section (see server_cert_ext.cnf/firewall_cert_ext.cnf),
            which requires -extensions req_ext below to actually be read;
            `openssl x509 -req -extfile` alone only looks at the file's
            unnamed top-level section, which here is empty - without
            -extensions, none of these extensions (including the SAN
            customers were missing) were ever applied to the signed
            certificate.
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
                              '-extfile', cnffile, '-extensions', 'req_ext'],
                             stdout=log, stderr=subprocess.STDOUT, check=True)
        else:
            subprocess.run(['openssl', 'x509', '-req', '-in', csrfile,
                          '-CA', environment.CACERT, '-passin', 'pass:' + cakeypw,
                          '-CAkey', environment.CAKEY, '-CAcreateserial',
                          '-out', certfile, '-sha256', '-days', str(days),
                          '-extfile', cnffile, '-extensions', 'req_ext'],
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
