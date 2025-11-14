#
# Common helper functions for setup scripts
# thomas@linuxmuster.net
# 20251114
#

"""
Helper functions and constants for linuxmuster-base7 setup scripts.

This module provides:
- Common subprocess execution with logging
- IP address manipulation utilities
- Template variable replacement
- Shared constants

Usage:
    from linuxmuster_base7.setup.helpers import runWithLog, buildIp, DHCP_RANGE_START_SUFFIX
"""

import datetime
import shlex
import subprocess
from typing import Dict, List, Optional, Union


# Constants
# =========

# DHCP Configuration
DHCP_RANGE_START_SUFFIX = 201
DHCP_RANGE_END_SUFFIX = 250
DHCP_RANGE_START_LARGE_NET = '255.1'
DHCP_RANGE_END_LARGE_NET = '255.254'

# Certificate Configuration
CERT_VALIDITY_DAYS = 3650  # 10 years

# LINBO Configuration
DEFAULT_LINBO_IP = '10.0.0.1'

# Crypto Types
CRYPTO_TYPES = ['dsa', 'ecdsa', 'ed25519', 'rsa']

# Files that should not be overwritten during template processing
DO_NOT_OVERWRITE_FILES = ['dhcpd.custom.conf']
DO_NOT_BACKUP_FILES = ['interfaces.linuxmuster', 'dovecot.linuxmuster.conf', 'smb.conf']


# Functions
# =========

def runWithLog(
    cmd: Union[str, List[str]],
    logfile: str,
    checkErrors: bool = True,
    maskSecrets: Optional[List[str]] = None
) -> subprocess.CompletedProcess:
    """
    Execute command with output captured to logfile.

    Args:
        cmd: Command string or list of arguments
        logfile: Path to log file
        checkErrors: Raise exception on non-zero return code (default: True)
        maskSecrets: List of strings to mask in logs (e.g., passwords)

    Returns:
        CompletedProcess instance

    Raises:
        subprocess.CalledProcessError: If checkErrors=True and command fails

    Example:
        >>> runWithLog(['ls', '-la'], '/var/log/setup.log')
        >>> runWithLog('systemctl restart samba', '/var/log/setup.log',
        ...            maskSecrets=['mypassword'])
    """
    # Convert string command to list
    cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd

    # Execute command
    result = subprocess.run(
        cmd_args,
        capture_output=True,
        text=True,
        check=False,
        shell=False
    )

    # Write to log if specified
    if logfile and (result.stdout or result.stderr):
        with open(logfile, 'a') as log:
            log.write('-' * 78 + '\n')
            log.write('#### ' + str(datetime.datetime.now()).split('.')[0] + ' ####\n')

            # Prepare command string for logging
            cmd_str = cmd if isinstance(cmd, str) else ' '.join(cmd_args)

            # Mask secrets if provided
            if maskSecrets:
                for secret in maskSecrets:
                    if secret:  # Only mask non-empty strings
                        cmd_str = cmd_str.replace(secret, '******')

            log.write('#### ' + cmd_str + ' ####\n')

            # Write output (masked if needed)
            stdout = result.stdout or ''
            stderr = result.stderr or ''

            if maskSecrets:
                for secret in maskSecrets:
                    if secret:
                        stdout = stdout.replace(secret, '******')
                        stderr = stderr.replace(secret, '******')

            if stdout:
                log.write(stdout)
            if stderr:
                log.write(stderr)
            log.write('-' * 78 + '\n')

    # Check for errors if requested
    if checkErrors and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd_args, result.stdout, result.stderr
        )

    return result


def buildIp(octets: List[Union[str, int]]) -> str:
    """
    Build IP address string from list of octets.

    Args:
        octets: List of octets (strings or integers)

    Returns:
        IP address string

    Example:
        >>> buildIp(['10', '16', '1', '1'])
        '10.16.1.1'
        >>> buildIp([192, 168, 0, 1])
        '192.168.0.1'
    """
    return '.'.join(str(o) for o in octets)


def getNetworkPrefix(ip: str, numOctets: int = 3) -> str:
    """
    Get first N octets of IP address.

    Args:
        ip: IP address string
        numOctets: Number of octets to return (default: 3)

    Returns:
        Network prefix (e.g., '10.16.1' for numOctets=3)

    Example:
        >>> getNetworkPrefix('10.16.1.254')
        '10.16.1'
        >>> getNetworkPrefix('192.168.0.1', 2)
        '192.168'
    """
    octets = ip.split('.')
    return '.'.join(octets[:numOctets])


def splitIpOctets(ip: str) -> List[str]:
    """
    Split IP address into list of octets.

    Args:
        ip: IP address string

    Returns:
        List of octet strings

    Example:
        >>> splitIpOctets('10.16.1.1')
        ['10', '16', '1', '1']
    """
    return ip.split('.')


def replaceTemplateVars(content: str, variables: Dict[str, str]) -> str:
    """
    Replace all template variables in content.

    Args:
        content: Template content with @@variable@@ placeholders
        variables: Dictionary mapping placeholders to values

    Returns:
        Content with variables replaced

    Example:
        >>> content = "Server: @@servername@@.@@domainname@@"
        >>> vars = {'@@servername@@': 'server', '@@domainname@@': 'linuxmuster.lan'}
        >>> replaceTemplateVars(content, vars)
        'Server: server.linuxmuster.lan'
    """
    for placeholder, value in variables.items():
        content = content.replace(placeholder, str(value))
    return content
