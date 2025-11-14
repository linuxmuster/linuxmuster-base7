#!/usr/bin/python3
#
# linuxmuster-setup CLI entry point
# thomas@linuxmuster.net
# 20251111
#

import sys
import subprocess
import datetime
import os
import getopt
import importlib
import shutil

# Add linuxmuster-common to path for environment module
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment

from linuxmuster_base7.functions import checkFwMajorVer, modIni, printScript, tee


def usage():
    print('Usage: linuxmuster-setup [options]')
    print(' [options] may be:')
    print(' -n <hostname>,   --servername=<hostname>   : Set server hostname.')
    print(' -d <domainname>, --domainname=<domainname> : Set domainname.')
    print(' -r <dhcprange>,  --dhcprange=<dhcprange>   : Set dhcp range.')
    print(' -a <adminpw>,    --adminpw=<adminpw>       : Set admin password.')
    print(' -e <schoolname>, --schoolname=<schoolname> : Set school name.')
    print(' -l <location>,   --location=<location>     : Set school location.')
    print(' -z <country>,    --country=<country>       : Set school country.')
    print(' -v <state>,      --state=<state>           : Set school state.')
    print(' -c <file>,       --config=<file>           : path to ini file with setup values')
    print(' -u,              --unattended              : unattended mode, do not ask questions')
    print(' -s,              --skip-fw                 : skip firewall setup per ssh')
    print(' -h,              --help                    : print this help')


def main():
    """Main entry point for linuxmuster-setup command."""
    # get cli args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "a:c:d:e:hl:n:r:suv:z:",
                                   ["adminpw=", "config=", "domainname=", "schoolname=", "help",
                                    "location=", "servername=", "dhcprange=", "skip-fw", "unattended", "state=", "country="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    # default values
    unattended = False
    skipfw = False
    servername = ''
    domainname = ''
    dhcprange = ''
    adminpw = ''
    schoolname = ''
    location = ''
    country = ''
    state = ''
    cli_customini = ''

    # open logfile
    global logfile
    logfile = environment.SETUPLOG
    subprocess.run(['touch', logfile], check=False)
    subprocess.run(['chmod', '600', logfile], check=True)
    try:
        l = open(logfile, 'w')
        orig_out = sys.stdout
        sys.stdout = tee(sys.stdout, l)
        sys.stderr = tee(sys.stderr, l)
    except Exception as error:
        print(f'Cannot open logfile {logfile}: {error}')
        sys.exit()

    # evaluate options
    for o, a in opts:
        if o in ("-u", "--unattended"):
            unattended = True
        elif o in ("-v", "--state"):
            state = a
        elif o in ("-z", "--country"):
            country = a
        elif o in ("-l", "--location"):
            location = a
        elif o in ("-e", "--schoolname"):
            schoolname = a
        elif o in ("-a", "--adminpw"):
            adminpw = a
        elif o in ("-n", "--servername"):
            servername = a
        elif o in ("-d", "--domainname"):
            domainname = a
        elif o in ("-r", "--dhcprange"):
            dhcprange = a
        elif o in ("-s", "--skip-fw"):
            skipfw = True
        elif o in ("-c", "--config"):
            if os.path.isfile(a):
                cli_customini = a
            else:
                usage()
                sys.exit()
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    # start message
    printScript(os.path.basename(__file__), 'begin')

    # custom ini file given on cli
    if cli_customini != '':
        print('Custom inifile ' + cli_customini
              + ' given on cli, ignoring other arguments!')
        shutil.copy2(cli_customini, environment.CUSTOMINI)
        subprocess.run(['chmod', '600', environment.CUSTOMINI], check=True)
    else:
        # check params
        print('Processing commandline arguments.')
        if servername != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'servername', servername)
        if domainname != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'domainname', domainname)
        if dhcprange != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'dhcprange', dhcprange)
        if adminpw != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'adminpw', adminpw)
        if schoolname != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'schoolname', schoolname)
        if location != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'location', location)
        if country != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'country', country)
        if state != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'state', state)
        rc = modIni(environment.CUSTOMINI, 'setup', 'skipfw', str(skipfw))

    # work off setup modules from the Python package
    import pkgutil
    import linuxmuster_base7.setup as setup_package

    # Get all modules from linuxmuster_base7.setup package
    setup_modules = []
    for importer, modname, ispkg in pkgutil.iter_modules(setup_package.__path__):
        if not ispkg and modname not in ['__init__', 'helpers']:
            setup_modules.append(modname)

    setup_modules.sort()

    for module_name in setup_modules:
        # skip dialog in unattended mode
        if (unattended and 'dialog' in module_name):
            continue
        # check firewall major version
        if (not skipfw and 'templates' in module_name):
            if not checkFwMajorVer():
                sys.exit(1)
        # print module name (extract display name from module name)
        # module names are like: a_ini, c_general-dialog, etc.
        display_name = module_name.split('_', 1)[1] if '_' in module_name else module_name
        printScript('', 'begin')
        printScript(display_name)
        # execute module
        importlib.import_module(f'linuxmuster_base7.setup.{module_name}')

    printScript(os.path.basename(__file__), 'end')


if __name__ == '__main__':
    main()
