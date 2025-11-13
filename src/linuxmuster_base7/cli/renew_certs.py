#!/usr/bin/python3
#
# renew self-signed server certs
# thomas@linuxmuster.net
# 20251113
#

import datetime
import environment
import getopt
import os
import shutil
import sys

from linuxmuster_base7.functions import catFiles, checkFwMajorVer, getFwConfig, getSetupValue, printScript, putFwConfig, \
    readTextfile, replaceInFile, sshExec, subProc, tee


# print usage info
def usage():
    print('Usage: linuxmuster-renew-certs [options]')
    print(' [options] may be:')
    print(' -c <list>, --certs=<list> : Comma separated list of certificates to be renewed')
    print('                             ("ca", "server" and/or "firewall" or "all"). Mandatory.')
    print(' -d <#>,    --days=<#>     : Set number of days (default: 7305).')
    print(' -f,        --force        : Skip security prompt.')
    print(' -n,        --dry-run      : Test only if the firewall certs can be renewed.')
    print(' -r,        --reboot       : Reboot server and firewall finally.')
    print(' -h,        --help         : Print this help.')




def main():
    """Renew self-signed server certificates."""
    # get cli args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:d:fhnr", ["certs=", "days=", "dry-run", "force", "help", "reboot"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)


    # default values
    dry = False
    force = False
    reboot = False
    days = '7305'
    all_list = ['ca', 'server', 'firewall']
    cert_list = []


    # open logfile
    logfile = environment.LOGDIR + '/renew-certs.log'
    try:
        l = open(logfile, 'a')
        orig_out = sys.stdout
        sys.stdout = tee(sys.stdout, l)
        sys.stderr = tee(sys.stderr, l)
    except Exception as err:
        printScript('Cannot open logfile ' + logfile + ' !')
        printScript(err)
        sys.exit()


    # start message
    printScript(os.path.basename(__file__), 'begin')


    # evaluate options
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
            dry = True
        elif o in ("-r", "--reboot"):
            reboot = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"
            usage()
            sys.exit(1)
    if len(cert_list) == 0:
        printScript('No certs to renew given (-c)!')
        usage()
        sys.exit(1)


    # get setup values
    msg = 'Reading setup data.'
    printScript(msg)
    try:
        schoolname = getSetupValue('schoolname')
        servername = getSetupValue('servername')
        domainname = getSetupValue('domainname')
        sambadomain = getSetupValue('sambadomain')
        skipfw = getSetupValue('skipfw')
        realm = getSetupValue('realm')
        firewallip = getSetupValue('firewallip')
        serverip = getSetupValue('serverip')
    except Exception as err:
        printScript(msg + ' errors detected!')
        print(err)
        sys.exit(1)


    # check options
    if skipfw and dry:
        printScript('Dry mode runs only with standard OPNsense firewall.')
        usage
        sys.exit(1)
    if skipfw and 'firewall' in cert_list:
        printScript('Renewing the firewall certificate works only with standard OPNsense firewall.')
        usage
        sys.exit(1)
    if dry:
        force = True
        cert_list = ['ca', 'firewall']


    # security prompt
    if not force:
        msg = 'Attention! Please confirm the renewing of the server certificates.'
        printScript(msg)
        answer = input("Answer \"YES\" to proceed: ")
        if answer != "YES":
            sys.exit(1)


    # certificate environment
    ssldir = environment.SSLDIR
    cacert = environment.CACERT
    cacert_crt = environment.CACERTCRT
    cacert_subject = '-subj /O="' + schoolname + '"/OU=' + sambadomain + '/CN=' + realm + '/subjectAltName=' + realm + '/'
    cakey = environment.CAKEY
    rc, cakeypw = readTextfile(environment.CAKEYSECRET)
    cakey_passin = '-passin pass:' + cakeypw
    fwconftmp = environment.FWCONFLOCAL
    now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    fwconfbak = fwconftmp.replace('.xml', '-' + now + '.xml')


    # functions

    # test firewall if cert is renewable
    def testFw(item, b64):
        if skipfw:
            return
        msg = 'Test if ' + item + ' cert can be renewed:'
        printScript(msg)
        try:
            rc, b64_test = readTextfile(b64)
            with open(fwconftmp) as fwconf:
                if b64_test in fwconf.read():
                    printScript('* Success!')
                else:
                    printScript('* Failed, certificate is unknown!')
                    sys.exit(1)
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)


    # patch firewall config with new cert
    def patchFwCert(new, old):
        msg = 'Patching firewall config with ' + os.path.basename(new) + '.'
        printScript(msg)
        try:
            rc, cert_old = readTextfile(old)
            rc, cert_new = readTextfile(new)
            replaceInFile(fwconftmp, cert_old, cert_new)
        except Exception as err:
            printScript('* Failed!')
            print(err)
            return False


    # check firewall version and download config
    def checkFw():
        if skipfw:
            return
        try:
            checkFwMajorVer()
            getFwConfig(firewallip)
            shutil.copyfile(fwconftmp, fwconfbak)
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)


    # apply firewall changes
    def applyFw():
        if skipfw:
            return
        try:
            putFwConfig(firewallip)
            if reboot:
                sshExec(firewallip, '/sbin/reboot')
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)


    # create the cnf from template
    def createCnf(cnf_tpl):
        # read template file
        rc, filedata = readTextfile(cnf_tpl)
        # replace placeholders with values
        filedata = filedata.replace('@@domainname@@', domainname)
        filedata = filedata.replace('@@firewallip@@', firewallip)
        filedata = filedata.replace('@@realm@@', realm)
        filedata = filedata.replace('@@sambadomain@@', sambadomain)
        filedata = filedata.replace('@@schoolname@@', schoolname)
        filedata = filedata.replace('@@servername@@', servername)
        filedata = filedata.replace('@@serverip@@', serverip)
        # get cnf path
        firstline = filedata.split('\n')[0]
        cnf = firstline.partition(' ')[2]
        # write cnf
        with open(cnf, 'w') as outfile:
            outfile.write(filedata)
        return cnf


    # renew certificate
    def renewCert(item):
        if item == servername and servername != 'server':
            name = 'server'
        else: 
            name = item
        if item == 'ca':
            pem = cacert
        else:
            key = ssldir + '/' + name + '.key.pem'
            pem = ssldir + '/' + name + '.cert.pem'
            csr = ssldir + '/' + name + '.csr'
            chn = ssldir + '/' + name + '.fullchain.pem'
            bdl = ssldir + '/' + name + '.cert.bundle.pem'
            cnf_tpl = environment.TPLDIR + '/' + name + '_cert_ext.cnf'
        b64 = pem + '.b64'
        b64_old = b64 + '_old'
        if name == 'firewall' or name == 'ca':
            testFw(item, b64)
            if dry: return
        msg = 'Renewing ' + name + ' certificate.'
        printScript(msg)
        try:
            if name == 'ca':
                printScript('Note that you have to renew and deploy also all certs which depend on cacert.')
                subProc('openssl req -batch -x509 ' + cacert_subject + ' -new -nodes ' + cakey_passin
                    + ' -key ' + cakey + ' -sha256 -days ' + days + ' -out ' + cacert, logfile)
                subProc('openssl x509 -in ' + cacert + ' -inform PEM -out ' + cacert_crt, logfile)
            else:
                cnf = createCnf(cnf_tpl)
                subProc('openssl x509 -req -in ' + csr + ' -CA ' + cacert + ' ' + cakey_passin + ' -CAkey '
                    + cakey + ' -CAcreateserial -out ' + pem + ' -days ' + days + ' -sha256 -extfile ' + cnf, logfile)
                catFiles([pem, cacert], chn)
                catFiles([key, pem], bdl)
            if name == 'firewall' or name == 'ca':
                shutil.copyfile(b64, b64_old)
                subProc('base64 -w0 ' + pem + ' > ' + b64, logfile)
                patchFwCert(b64, b64_old)
        except Exception as err:
            printScript('Failed!')
            print(err)
            sys.exit(1)


    # reorder certlist to ensure ca is the first item
    def reorderCertlist(cert_list):
        cert_list.remove('ca')
        ordered_list = ['ca']
        for item in cert_list:
            ordered_list.append(item)
        return ordered_list


    # main

    # reorder certlist to ensure ca is the first item
    if 'ca' in cert_list and len(cert_list) > 1 and cert_list[0] != 'ca':
        cert_list = reorderCertlist(cert_list)


    # check firewall version and download config
    if 'firewall' in cert_list or 'ca' in cert_list:
        checkFw()


    # iterate certificate items
    for item in cert_list:
        # process only valid items
        if item not in all_list:
            continue
        # renew cert
        renewCert(item)


    # dry mode
    if dry:
        printScript("Dry run finished successfully.")

    else:
        # apply firewall changes
        if 'firewall' in cert_list or 'ca' in cert_list:
            applyFw()

        # reboot server if requested
        if reboot:
            printScript("Rebooting server.")
            subProc('/sbin/reboot', logfile)


    # end message
    printScript(os.path.basename(__file__), 'end')


if __name__ == '__main__':
    main()
