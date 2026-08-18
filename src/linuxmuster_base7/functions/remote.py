#!/usr/bin/python3
#
# Filename     : remote.py
# Description  : OPNsense firewall API and SSH/SCP remote-execution helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import configparser
import json
import paramiko
import subprocess
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import requests
import time
import urllib3
import warnings

from .core import getSetupValue, printScript

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings(action='ignore', module='.*paramiko.*')


# wait for firewall to come up, after timeout seconds loop will be canceled
def waitForFw(timeout=300, wait=0):
    printScript('Waiting for opnsense to come up')
    firewallip = getSetupValue('firewallip')
    time.sleep(wait)
    count = 0
    while True:
        if count > timeout:
            # cancel if it lasts longer than timeout
            printScript('Timeout!')
            return False
        if sshExec(firewallip, 'exit'):
            break
        count = count + 2
        time.sleep(2)

    # SSH answers well before the OPNsense web stack (lighttpd/php-fpm/configd)
    # is fully initialized, especially right after a reboot triggered by a
    # plugin install. Wait for the API to actually respond before declaring
    # the firewall ready, using a single attempt per poll since this loop
    # already provides its own retry/backoff.
    printScript('Waiting for opnsense api to come up')
    while True:
        if count > timeout:
            printScript('Timeout waiting for api!')
            return False
        if firewallApi('get', '/core/firmware/status', retries=1) is not None:
            return True
        count = count + 2
        time.sleep(2)


# firewall api get request
def firewallApi(request, path, data='', retries=3, retry_wait=3):
    domainname = getSetupValue('domainname')
    fwapi = configparser.RawConfigParser(delimiters=('='))
    fwapi.read(environment.FWAPIKEYS)
    apikey = fwapi.get('api', 'key')
    apisecret = fwapi.get('api', 'secret')
    headers = {'content-type': 'application/json'}
    url = 'https://firewall.' + domainname + '/api' + path

    for attempt in range(1, retries + 1):
        try:
            if request == 'get':
                req = requests.get(url, auth=(apikey, apisecret), verify=False, timeout=30)
            elif request == 'post' and data == '':
                req = requests.post(url, auth=(apikey, apisecret), verify=False, timeout=30)
            elif request == 'post' and data != '':
                req = requests.post(url, data=data, auth=(
                    apikey, apisecret), headers=headers, verify=False, timeout=30)
            else:
                return None
        except requests.exceptions.RequestException as error:
            printScript(f'* Firewall API connection error (attempt {attempt}/{retries}): {error}')
            if attempt < retries:
                time.sleep(retry_wait)
                continue
            return None

        # get response
        if req.status_code == 200:
            return json.loads(req.text)
        else:
            printScript('Connection / Authentication issue, response received:')
            print(req.text)
            return None

    return None


# check firewall's major version
def checkFwMajorVer():
    try:
        firewallip = getSetupValue('firewallip')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(firewallip, port=22, username='root', password=environment.ROOTPW)
        stdin, stdout, stderr = ssh.exec_command('opnsense-version')
        output = stdout.readlines()[0]
        fver = output.split()[1]
        mver = int(fver.split('.')[0])
        if mver == environment.FWMAJORVER:
            return True
        else:
            print('Firewall version ' + fver + ' does not match ' + str(environment.FWMAJORVER) + '.*!')
            return False
    except Exception as error:
        print(error)
        return False


# file transfer per scp
def scpTransfer(ip, mode, sourcefile, targetfile, secret='', sshuser='root'):
    """
    Transfer files via SCP (Secure Copy Protocol).

    Args:
        ip: Remote host IP address
        mode: 'get' (download) or 'put' (upload)
        sourcefile: Source file path
        targetfile: Target file path
        secret: SSH password (empty string for key-based auth)
        sshuser: SSH username (default: 'root')

    Returns:
        True on success, False on failure
    """
    if mode == 'get' or mode == 'put':
        printScript(mode + ' ' + ip + ' ' + sourcefile + ' ' + targetfile)
    else:
        print('Usage: scpTransfer(ip, mode, sourcefile, targetfile, secret, sshuser)')
        return 1
    # passwordless transfer using ssh keys
    if secret == '':
        # build ssh/scp command arguments as list (no shell injection risk)
        sshopts = ['-q', '-oNumberOfPasswordPrompts=0', '-oStrictHostkeyChecking=no']
        # test ssh connection first
        try:
            subprocess.run(['ssh'] + sshopts + ['-l', sshuser, ip, 'exit'],
                          check=True, capture_output=True)
        except subprocess.CalledProcessError as error:
            print(error)
            return False
        # file transfer with scp
        try:
            if mode == 'put':
                targetfile = sshuser + '@' + ip + ':' + targetfile
            if mode == 'get':
                sourcefile = sshuser + '@' + ip + ':' + sourcefile
            subprocess.run(['scp'] + sshopts + [sourcefile, targetfile],
                          check=True, capture_output=True)
        except subprocess.CalledProcessError as error:
            print(error)
            return False
    # transfer with password
    else:
        # test ssh connection
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, port=22, username=sshuser, password=secret)
        except Exception as error:
            print(error)
            return False
        # file upload
        try:
            ftp = ssh.open_sftp()
            if mode == 'put':
                ftp.put(sourcefile, targetfile)
            if mode == 'get':
                ftp.get(sourcefile, targetfile)
        except Exception as error:
            print(error)
            return False
        ftp.close()
        ssh.close()
    # return success
    return True


# download per sftp
def getSftp(ip, remotefile, localfile, secret='', sshuser='root'):
    rc = scpTransfer(ip, 'get', remotefile, localfile, secret, sshuser)
    return rc


# download firewall config.xml
def getFwConfig(firewallip, secret=''):
    printScript('Downloading firewall configuration:')
    rc = getSftp(firewallip, environment.FWCONFREMOTE,
                 environment.FWCONFLOCAL, secret)
    if rc:
        printScript('* Download finished successfully.')
    else:
        printScript('* Download failed!')
    return rc


# upload per sftp
def putSftp(ip, localfile, remotefile, secret='', sshuser='root'):
    rc = scpTransfer(ip, 'put', localfile, remotefile, secret, sshuser)
    return rc


# upload firewall config
def putFwConfig(firewallip, fwconf=environment.FWCONFREMOTE, secret=''):
    printScript('Uploading firewall configuration:')
    rc = putSftp(firewallip, environment.FWCONFLOCAL,
                 fwconf, secret)
    if rc:
        printScript('* Upload finished successfully.')
    else:
        printScript('* Upload failed!')
    return rc


# execute ssh command
# note: paramiko key based connection is obviously broken in 18.04, so we use
#   ssh shell command
def sshExec(ip, cmd, secret=''):
    """
    Execute command on remote host via SSH.

    Args:
        ip: Remote host IP address
        cmd: Command to execute remotely
        secret: SSH password (empty string for key-based auth)

    Returns:
        True on success, False on failure
    """
    printScript('Executing ssh command on ' + ip + ':')
    printScript('* -> "' + cmd + '"')
    sshopts = ['-q', '-oNumberOfPasswordPrompts=0', '-oStrictHostkeyChecking=no']
    # first test connection
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if secret == '':
            # key-based auth: test connection with subprocess (no shell=True)
            subprocess.run(['ssh'] + sshopts + ['-l', 'root', ip, 'exit'],
                          check=True, stdout=subprocess.DEVNULL)
        else:
            # password auth: test connection with paramiko
            ssh.connect(ip, port=22, username='root', password=secret)
        printScript('* SSH connection successfully established.')
        if cmd == 'exit':
            return True
    except (subprocess.CalledProcessError, Exception) as error:
        print(error)
        return False
    # second execute command
    try:
        if secret != '':
            # password auth: use paramiko for command execution
            stdin, stdout, stderr = ssh.exec_command(cmd)
        else:
            # key-based auth: use subprocess with command as separate argument
            subprocess.run(['ssh'] + sshopts + ['-l', 'root', ip, cmd],
                          check=True, capture_output=True)
        printScript('* SSH command execution finished successfully.')
    except (subprocess.CalledProcessError, Exception) as error:
        print(error)
        return False
    if secret != '':
        ssh.close()
    return True
