#!/usr/bin/python3
#
# renew self-signed server certs
# thomas@linuxmuster.net
# 20251114
#

"""
Certificate renewal utility for linuxmuster.net.

This module provides functionality to renew self-signed SSL/TLS certificates
for the CA, server, and firewall components. It supports:
- Renewing individual certificates or all at once
- Testing certificate renewal without applying changes (dry-run mode)
- Updating firewall configuration with new certificates
- Optional server and firewall reboot after renewal
"""

import datetime
import environment
import getopt
import os
import shutil
import subprocess
import sys

from linuxmuster_base7.functions import catFiles, checkFwMajorVer, createCertificateChain, createCnfFromTemplate, \
    encodeCertToBase64, getFwConfig, getSetupValue, printScript, putFwConfig, readTextfile, renewCaCertificate, \
    replaceInFile, signCertificateWithCa, sshExec, tee


def usage():
    """Print command-line usage information."""
    print('Usage: linuxmuster-renew-certs [options]')
    print(' [options] may be:')
    print(' -c <list>, --certs=<list> : Comma separated list of certificates to be renewed')
    print('                             ("ca", "server" and/or "firewall" or "all"). Mandatory.')
    print(' -d <#>,    --days=<#>     : Set number of days (default: 7305).')
    print(' -f,        --force        : Skip security prompt.')
    print(' -n,        --dry-run      : Test only if the firewall certs can be renewed.')
    print(' -r,        --reboot       : Reboot server and firewall finally.')
    print(' -h,        --help         : Print this help.')


class CertificateRenewer:
    """
    Manages SSL/TLS certificate renewal for linuxmuster.net infrastructure.

    This class handles the renewal of CA, server, and firewall certificates,
    including validation, firewall configuration updates, and optional reboots.
    """

    def __init__(self, cert_list, days='7305', dry_run=False, force=False, reboot=False):
        """
        Initialize the certificate renewer.

        Args:
            cert_list: List of certificates to renew ('ca', 'server', 'firewall')
            days: Certificate validity in days (default: 7305 = ~20 years)
            dry_run: Test mode without applying changes
            force: Skip security prompts
            reboot: Reboot server and firewall after renewal
        """
        self.cert_list = cert_list
        self.days = str(days)
        self.dry_run = dry_run
        self.force = force
        self.reboot = reboot
        self.all_certs = ['ca', 'server', 'firewall']

        # Setup logging
        self.logfile = environment.LOGDIR + '/renew-certs.log'
        self._setup_logging()

        # Load configuration
        self._load_setup_values()

        # Certificate paths and configuration
        self.ssldir = environment.SSLDIR
        self.cacert = environment.CACERT
        self.cacert_crt = environment.CACERTCRT
        self.cacert_subject = f'-subj /O="{self.schoolname}"/OU={self.sambadomain}/CN={self.realm}/subjectAltName={self.realm}/'
        self.cakey = environment.CAKEY
        # Read CA key password from secret file (created during setup in g_ssl.py)
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        self.cakeypw = cakeypw.strip()
        self.fwconftmp = environment.FWCONFLOCAL
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        self.fwconfbak = self.fwconftmp.replace('.xml', '-' + now + '.xml')

    def _setup_logging(self):
        """Configure logging to file and stdout/stderr."""
        try:
            l = open(self.logfile, 'a')
            sys.stdout = tee(sys.stdout, l)
            sys.stderr = tee(sys.stderr, l)
        except Exception as err:
            printScript('Cannot open logfile ' + self.logfile + ' !')
            printScript(err)
            sys.exit(1)

    def _load_setup_values(self):
        """Load configuration values from setup.ini."""
        msg = 'Reading setup data.'
        printScript(msg)
        try:
            self.schoolname = getSetupValue('schoolname')
            self.servername = getSetupValue('servername')
            self.domainname = getSetupValue('domainname')
            self.sambadomain = getSetupValue('sambadomain')
            self.skipfw = getSetupValue('skipfw')
            self.realm = getSetupValue('realm')
            self.firewallip = getSetupValue('firewallip')
            self.serverip = getSetupValue('serverip')
        except Exception as err:
            printScript(msg + ' errors detected!')
            print(err)
            sys.exit(1)

    def validateOptions(self):
        """Validate command-line options and configuration."""
        if self.skipfw and self.dry_run:
            printScript('Dry mode runs only with standard OPNsense firewall.')
            sys.exit(1)
        if self.skipfw and 'firewall' in self.cert_list:
            printScript('Renewing the firewall certificate works only with standard OPNsense firewall.')
            sys.exit(1)
        if self.dry_run:
            self.force = True
            self.cert_list = ['ca', 'firewall']

    def promptSecurityConfirmation(self):
        """Prompt user for security confirmation unless force mode is enabled."""
        if not self.force:
            msg = 'Attention! Please confirm the renewing of the server certificates.'
            printScript(msg)
            answer = input("Answer \"YES\" to proceed: ")
            if answer != "YES":
                sys.exit(1)

    def testFwCert(self, item, b64):
        """
        Test if firewall certificate can be renewed.

        Args:
            item: Certificate name (e.g., 'ca', 'firewall')
            b64: Path to base64-encoded certificate file
        """
        if self.skipfw:
            return
        msg = 'Test if ' + item + ' cert can be renewed:'
        printScript(msg)
        try:
            rc, b64_test = readTextfile(b64)
            with open(self.fwconftmp) as fwconf:
                if b64_test in fwconf.read():
                    printScript('* Success!')
                else:
                    printScript('* Failed, certificate is unknown!')
                    sys.exit(1)
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)

    def patchFwCert(self, new, old):
        """
        Patch firewall configuration with new certificate.

        Args:
            new: Path to new certificate file
            old: Path to old certificate file to replace
        """
        msg = 'Patching firewall config with ' + os.path.basename(new) + '.'
        printScript(msg)
        try:
            rc, cert_old = readTextfile(old)
            rc, cert_new = readTextfile(new)
            replaceInFile(self.fwconftmp, cert_old, cert_new)
        except Exception as err:
            printScript('* Failed!')
            print(err)
            return False

    def checkAndDownloadFwConfig(self):
        """Check firewall version and download current configuration."""
        if self.skipfw:
            return
        try:
            checkFwMajorVer()
            getFwConfig(self.firewallip)
            shutil.copyfile(self.fwconftmp, self.fwconfbak)
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)

    def applyFwChanges(self):
        """Upload updated configuration to firewall and optionally reboot."""
        if self.skipfw:
            return
        try:
            putFwConfig(self.firewallip)
            if self.reboot:
                sshExec(self.firewallip, '/sbin/reboot')
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)

    def renewCertificate(self, item):
        """
        Renew a specific certificate.

        Args:
            item: Certificate identifier ('ca', 'server', or 'firewall')
        """
        # Normalize certificate name
        if item == self.servername and self.servername != 'server':
            name = 'server'
        else:
            name = item

        # Set up certificate paths
        if item == 'ca':
            pem = self.cacert
        else:
            key = self.ssldir + '/' + name + '.key.pem'
            pem = self.ssldir + '/' + name + '.cert.pem'
            csr = self.ssldir + '/' + name + '.csr'
            chn = self.ssldir + '/' + name + '.fullchain.pem'
            bdl = self.ssldir + '/' + name + '.cert.bundle.pem'
            cnf_tpl = environment.TPLDIR + '/' + name + '_cert_ext.cnf'

        b64 = pem + '.b64'
        b64_old = b64 + '_old'

        # Test firewall certificate if applicable
        if name == 'firewall' or name == 'ca':
            self.testFwCert(item, b64)
            if self.dry_run:
                return

        msg = 'Renewing ' + name + ' certificate.'
        printScript(msg)
        try:
            if name == 'ca':
                # Renew CA certificate using shared function
                printScript('Note that you have to renew and deploy also all certs which depend on cacert.')
                if not renewCaCertificate(self.cacert_subject, self.days, self.logfile):
                    raise Exception('Failed to renew CA certificate')
            else:
                # Renew server or firewall certificate using shared functions
                cnf = createCnfFromTemplate(cnf_tpl)
                if not cnf:
                    raise Exception('Failed to create configuration from template')

                if not signCertificateWithCa(csr, pem, self.days, cnf, self.logfile):
                    raise Exception('Failed to sign certificate')

                # Create certificate chains
                if not createCertificateChain(pem, chn):
                    raise Exception('Failed to create certificate chain')

                # Create bundle with key + cert
                catFiles([key, pem], bdl)

            # Update firewall configuration if needed
            if name == 'firewall' or name == 'ca':
                shutil.copyfile(b64, b64_old)
                encodeCertToBase64(pem, b64)
                self.patchFwCert(b64, b64_old)
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)

    def reorderCertList(self):
        """Ensure CA certificate is renewed first (dependencies)."""
        if 'ca' in self.cert_list and len(self.cert_list) > 1 and self.cert_list[0] != 'ca':
            self.cert_list.remove('ca')
            ordered_list = ['ca']
            for item in self.cert_list:
                ordered_list.append(item)
            self.cert_list = ordered_list

    def run(self):
        """Execute the certificate renewal process."""
        printScript(os.path.basename(__file__), 'begin')

        # Validate options
        self.validateOptions()

        # Security prompt
        self.promptSecurityConfirmation()

        # Ensure CA is processed first if in list
        self.reorderCertList()

        # Check firewall and download config if needed
        if 'firewall' in self.cert_list or 'ca' in self.cert_list:
            self.checkAndDownloadFwConfig()

        # Process each certificate
        for item in self.cert_list:
            # Process only valid certificate types
            if item not in self.all_certs:
                continue
            self.renewCertificate(item)

        # Handle dry-run mode
        if self.dry_run:
            printScript("Dry run finished successfully.")
        else:
            # Apply firewall changes
            if 'firewall' in self.cert_list or 'ca' in self.cert_list:
                self.applyFwChanges()

            # Reboot server if requested
            if self.reboot:
                printScript("Rebooting server.")
                with open(self.logfile, 'a') as log:
                    subprocess.run(['/sbin/reboot'], stdout=log, stderr=subprocess.STDOUT, check=False)

        printScript(os.path.basename(__file__), 'end')


def main():
    """Parse command-line arguments and initiate certificate renewal."""
    # Parse command-line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:d:fhnr", ["certs=", "days=", "dry-run", "force", "help", "reboot"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    # Default values
    dry_run = False
    force = False
    reboot = False
    days = '7305'
    all_list = ['ca', 'server', 'firewall']
    cert_list = []

    # Evaluate options
    for o, a in opts:
        if o in ("-c", "--certs"):
            if a == 'all':
                cert_list = all_list
            else:
                cert_list = a.split(',')
        elif o in ("-d", "--days"):
            days = str(a)
        elif o in ("-f", "--force"):
            force = True
        elif o in ("-n", "--dry-run"):
            dry_run = True
        elif o in ("-r", "--reboot"):
            reboot = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    # Validate required arguments
    if len(cert_list) == 0:
        printScript('No certs to renew given (-c)!')
        usage()
        sys.exit(1)

    # Create renewer instance and run
    renewer = CertificateRenewer(cert_list, days, dry_run, force, reboot)
    renewer.run()


if __name__ == '__main__':
    main()
