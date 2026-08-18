#!/usr/bin/python3
#
# Filename     : __init__.py
# Description  : Public re-export surface for linuxmuster_base7.functions -
#                preserves "from linuxmuster_base7.functions import X" for
#                every name that used to live in the single functions.py
#                file, now split into cohesive submodules (see issue #129):
#                core, files, network, samba, linbo, certs, remote, security.
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import datetime  # re-exported: some callers do "from ...functions import datetime"

from .core import tee, printLf, printScript, getSetupValue, mySetupLogfile, \
    dtStr, setupComment
from .files import readTextfile, writeTextfile, writeSecretFile, \
    replaceInFile, modIni, catFiles, backupCfg
from .network import ipMatchSubnet, getIpSubnet, getIpBcAddress, \
    getSubnetArray, readDevicesCsv, validateDeviceRow, filterDevices, \
    transformDeviceRow, getDevicesArray, isValidMac, isValidHostname, \
    isValidDomainname, isValidHostIpv4, getHostname, detectedInterfaces, \
    getDefaultIface, checkSocket
from .samba import getBaseDN, adSearch, isDynamicIpDevice, sambaTool
from .linbo import getGrubPart, getGrubOstype, readStartconf, \
    getStartconfOption, getStartconfPartlabel, getStartconfPartnr, \
    setGlobalStartconfOption, getStartconfOsValues, getLinboVersion
from .certs import encodeCertToBase64, renewCaCertificate, \
    signCertificateWithCa, createCertificateChain, createCnfFromTemplate, \
    createServerCert
from .remote import waitForFw, firewallApi, checkFwMajorVer, scpTransfer, \
    getSftp, getFwConfig, putSftp, putFwConfig, sshExec
from .security import hasNumbers, randomPassword, isValidPassword, \
    enterPassword

__all__ = [
    'datetime',
    # core
    'tee', 'printLf', 'printScript', 'getSetupValue', 'mySetupLogfile',
    'dtStr', 'setupComment',
    # files
    'readTextfile', 'writeTextfile', 'writeSecretFile', 'replaceInFile',
    'modIni', 'catFiles', 'backupCfg',
    # network
    'ipMatchSubnet', 'getIpSubnet', 'getIpBcAddress', 'getSubnetArray',
    'readDevicesCsv', 'validateDeviceRow', 'filterDevices',
    'transformDeviceRow', 'getDevicesArray', 'isValidMac', 'isValidHostname',
    'isValidDomainname', 'isValidHostIpv4', 'getHostname',
    'detectedInterfaces', 'getDefaultIface', 'checkSocket',
    # samba
    'getBaseDN', 'adSearch', 'isDynamicIpDevice', 'sambaTool',
    # linbo
    'getGrubPart', 'getGrubOstype', 'readStartconf', 'getStartconfOption',
    'getStartconfPartlabel', 'getStartconfPartnr', 'setGlobalStartconfOption',
    'getStartconfOsValues', 'getLinboVersion',
    # certs
    'encodeCertToBase64', 'renewCaCertificate', 'signCertificateWithCa',
    'createCertificateChain', 'createCnfFromTemplate', 'createServerCert',
    # remote
    'waitForFw', 'firewallApi', 'checkFwMajorVer', 'scpTransfer', 'getSftp',
    'getFwConfig', 'putSftp', 'putFwConfig', 'sshExec',
    # security
    'hasNumbers', 'randomPassword', 'isValidPassword', 'enterPassword',
]
