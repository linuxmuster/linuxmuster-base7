#!/usr/bin/python3
#
# renew self-signed server certs
# thomas@linuxmuster.net
# 20251117
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

        # Setup logging - redirect stdout/stderr to log file
        self.logfile = environment.LOGDIR + '/renew-certs.log'
        self._setupLogging()

        # Load configuration from setup.ini
        self._loadSetupValues()

        # Certificate paths and configuration
        self.ssldir = environment.SSLDIR  # Base SSL directory
        self.cacert = environment.CACERT  # CA certificate path
        self.cacert_crt = environment.CACERTCRT  # CA certificate in CRT format
        # CA certificate subject line with organization, domain, and realm
        self.cacert_subject = f'-subj /O="{self.schoolname}"/OU={self.sambadomain}/CN={self.realm}/subjectAltName={self.realm}/'
        self.cakey = environment.CAKEY  # CA private key path
        # Read CA key password from secret file (created during setup in g_ssl.py)
        rc, cakeypw = readTextfile(environment.CAKEYSECRET)
        self.cakeypw = cakeypw.strip()
        # Firewall configuration paths
        self.fwconftmp = environment.FWCONFLOCAL  # Temporary firewall config
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        self.fwconfbak = self.fwconftmp.replace('.xml', '-' + now + '.xml')  # Timestamped backup

    def _setupLogging(self):
        """Configure logging to file and stdout/stderr.

        Redirects both stdout and stderr to the log file while maintaining
        console output using the tee utility function.
        """
        try:
            l = open(self.logfile, 'a')
            sys.stdout = tee(sys.stdout, l)
            sys.stderr = tee(sys.stderr, l)
        except Exception as err:
            printScript('Cannot open logfile ' + self.logfile + ' !')
            printScript(err)
            sys.exit(1)

    def _loadSetupValues(self):
        """Load configuration values from setup.ini.

        Reads all required setup values including school name, server name,
        domain configuration, firewall IP, and skip_firewall flag.
        """
        msg = 'Reading setup data.'
        printScript(msg)
        try:
            self.schoolname = getSetupValue('schoolname')  # School/organization name
            self.servername = getSetupValue('servername')  # Server hostname
            self.domainname = getSetupValue('domainname')  # DNS domain name
            self.sambadomain = getSetupValue('sambadomain')  # Samba/AD domain
            self.skipfw = getSetupValue('skipfw')  # Skip firewall flag
            self.realm = getSetupValue('realm')  # Kerberos realm
            self.firewallip = getSetupValue('firewallip')  # Firewall IP address
            self.serverip = getSetupValue('serverip')  # Server IP address
        except Exception as err:
            printScript(msg + ' errors detected!')
            print(err)
            sys.exit(1)

    def validateOptions(self):
        """Validate command-line options and configuration.

        Checks for invalid option combinations and enforces constraints:
        - Dry-run requires OPNsense firewall (not skipfw)
        - Firewall cert renewal requires OPNsense firewall
        - Dry-run mode forces certain options (skip prompt, limit to ca+firewall)
        """
        # Dry-run mode requires standard OPNsense firewall
        if self.skipfw and self.dry_run:
            printScript('Dry mode runs only with standard OPNsense firewall.')
            sys.exit(1)
        # Firewall certificate renewal requires OPNsense firewall
        if self.skipfw and 'firewall' in self.cert_list:
            printScript('Renewing the firewall certificate works only with standard OPNsense firewall.')
            sys.exit(1)
        # Dry-run mode automatically enables force mode and limits to ca+firewall certs
        if self.dry_run:
            self.force = True  # Skip security prompt
            self.cert_list = ['ca', 'firewall']  # Only test these two certs

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

        This method handles the complete certificate renewal workflow:
        1. Normalize certificate name (e.g., servername -> 'server')
        2. Set up file paths for certificates, keys, and chains
        3. Test firewall certificate compatibility (if applicable)
        4. Generate new certificate (CA or signed cert)
        5. Create certificate chains and bundles
        6. Update firewall configuration with new certificate

        Args:
            item: Certificate identifier ('ca', 'server', or 'firewall')
        """
        # Normalize certificate name (servername could be custom, but we use 'server' internally)
        if item == self.servername and self.servername != 'server':
            name = 'server'
        else:
            name = item

        # Set up certificate paths based on certificate type
        if item == 'ca':
            # CA certificate only needs PEM file
            pem = self.cacert
        else:
            # Server/firewall certificates need multiple files
            key = self.ssldir + '/' + name + '.key.pem'  # Private key
            pem = self.ssldir + '/' + name + '.cert.pem'  # Certificate
            csr = self.ssldir + '/' + name + '.csr'  # Certificate signing request
            chn = self.ssldir + '/' + name + '.fullchain.pem'  # Full chain (cert + CA)
            bdl = self.ssldir + '/' + name + '.cert.bundle.pem'  # Bundle (key + cert)
            cnf_tpl = environment.TPLDIR + '/' + name + '_cert_ext.cnf'  # OpenSSL config template

        # Base64-encoded versions for firewall configuration
        b64 = pem + '.b64'  # Current base64-encoded cert
        b64_old = b64 + '_old'  # Backup of old base64-encoded cert

        # Test firewall certificate if this cert will be uploaded to firewall
        if name == 'firewall' or name == 'ca':
            self.testFwCert(item, b64)
            if self.dry_run:
                return  # Dry-run mode stops after testing

        msg = 'Renewing ' + name + ' certificate.'
        printScript(msg)
        try:
            if name == 'ca':
                # CA certificate renewal is special - it's self-signed
                printScript('Note that you have to renew and deploy also all certs which depend on cacert.')
                if not renewCaCertificate(self.cacert_subject, self.days, self.logfile):
                    raise Exception('Failed to renew CA certificate')
            else:
                # Server/firewall certificate renewal - signed by CA
                # Step 1: Create OpenSSL configuration from template
                cnf = createCnfFromTemplate(cnf_tpl)
                if not cnf:
                    raise Exception('Failed to create configuration from template')

                # Step 2: Sign the CSR with CA to create new certificate
                if not signCertificateWithCa(csr, pem, self.days, cnf, self.logfile):
                    raise Exception('Failed to sign certificate')

                # Step 3: Create full chain (cert + CA cert) for clients
                if not createCertificateChain(pem, chn):
                    raise Exception('Failed to create certificate chain')

                # Step 4: Create bundle (key + cert) for services that need both
                catFiles([key, pem], bdl)

            # Update firewall configuration if this cert is used by firewall
            if name == 'firewall' or name == 'ca':
                shutil.copyfile(b64, b64_old)  # Backup old base64 cert
                encodeCertToBase64(pem, b64)  # Encode new cert to base64
                self.patchFwCert(b64, b64_old)  # Replace in firewall config
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)

    def reorderCertList(self):
        """Ensure CA certificate is renewed first (dependencies).

        The CA certificate must be renewed before any certificates signed by it.
        This method moves 'ca' to the front of the list if present.
        """
        if 'ca' in self.cert_list and len(self.cert_list) > 1 and self.cert_list[0] != 'ca':
            self.cert_list.remove('ca')
            ordered_list = ['ca']
            for item in self.cert_list:
                ordered_list.append(item)
            self.cert_list = ordered_list

    def run(self):
        """Execute the certificate renewal process.

        Main orchestration method that coordinates the complete renewal workflow:
        1. Validate options and configuration
        2. Prompt for security confirmation (unless --force)
        3. Reorder cert list (CA first if present)
        4. Download firewall config (if needed)
        5. Renew each certificate in the list
        6. Upload updated firewall config (if changed)
        7. Optionally reboot server and/or firewall
        """
        printScript(os.path.basename(__file__), 'begin')

        # Step 1: Validate options and check for conflicts
        self.validateOptions()

        # Step 2: Security prompt (unless force mode or dry-run)
        self.promptSecurityConfirmation()

        # Step 3: Ensure CA is processed first (dependency order)
        self.reorderCertList()

        # Step 4: Download firewall config if any firewall-related certs will be renewed
        if 'firewall' in self.cert_list or 'ca' in self.cert_list:
            self.checkAndDownloadFwConfig()

        # Step 5: Process each certificate in the list
        for item in self.cert_list:
            # Skip invalid certificate types (should not happen after validation)
            if item not in self.all_certs:
                continue
            self.renewCertificate(item)

        # Step 6: Handle dry-run vs real execution
        if self.dry_run:
            printScript("Dry run finished successfully.")
        else:
            # Upload modified firewall config if firewall-related certs were renewed
            if 'firewall' in self.cert_list or 'ca' in self.cert_list:
                self.applyFwChanges()

            # Reboot server if requested via --reboot flag
            if self.reboot:
                printScript("Rebooting server.")
                with open(self.logfile, 'a') as log:
                    subprocess.run(['/sbin/reboot'], stdout=log, stderr=subprocess.STDOUT, check=False)

        printScript(os.path.basename(__file__), 'end')


def main():
    """Parse command-line arguments and initiate certificate renewal.

    Main entry point that handles:
    1. Command-line argument parsing
    2. Option validation
    3. Creation of CertificateRenewer instance
    4. Execution of renewal workflow
    """
    # Step 1: Parse command-line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:d:fhnr", ["certs=", "days=", "dry-run", "force", "help", "reboot"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    # Step 2: Initialize default values
    dry_run = False  # Test mode without applying changes
    force = False  # Skip security confirmation prompt
    reboot = False  # Reboot server and firewall after renewal
    days = '7305'  # Certificate validity (~20 years)
    all_list = ['ca', 'server', 'firewall']  # All possible certificates
    cert_list = []  # List of certs to renew (will be populated from -c option)

    # Step 3: Process command-line options
    for o, a in opts:
        if o in ("-c", "--certs"):
            # Parse certificate list: 'all' or comma-separated list
            if a == 'all':
                cert_list = all_list
            else:
                cert_list = a.split(',')
        elif o in ("-d", "--days"):
            # Custom certificate validity period
            days = str(a)
        elif o in ("-f", "--force"):
            # Skip security confirmation
            force = True
        elif o in ("-n", "--dry-run"):
            # Test mode - validate certs can be renewed without changes
            dry_run = True
        elif o in ("-r", "--reboot"):
            # Reboot after renewal
            reboot = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    # Step 4: Validate that at least one certificate was specified
    if len(cert_list) == 0:
        printScript('No certs to renew given (-c)!')
        usage()
        sys.exit(1)

    # Step 5: Create CertificateRenewer instance and execute renewal
    renewer = CertificateRenewer(cert_list, days, dry_run, force, reboot)
    renewer.run()


if __name__ == '__main__':
    main()
