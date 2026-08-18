#!/usr/bin/python3
#
# Filename     : setup.py
# Description  : linuxmuster-setup CLI entry point
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
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

from linuxmuster_base7.functions import checkFwMajorVer, getSetupValue, modIni, printScript, tee


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


def parseArguments():
    """Parse command-line arguments for linuxmuster-setup.

    Returns:
        Dict with keys: unattended, skipfw, servername, domainname, dhcprange,
        adminpw, schoolname, location, country, state, cli_customini
    """
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
    values = {
        'unattended':    False,
        'skipfw':        False,
        'servername':    '',
        'domainname':    '',
        'dhcprange':     '',
        'adminpw':       '',
        'schoolname':    '',
        'location':      '',
        'country':       '',
        'state':         '',
        'cli_customini': '',
    }

    # evaluate options
    for o, a in opts:
        if o in ("-u", "--unattended"):
            values['unattended'] = True
        elif o in ("-v", "--state"):
            values['state'] = a
        elif o in ("-z", "--country"):
            values['country'] = a
        elif o in ("-l", "--location"):
            values['location'] = a
        elif o in ("-e", "--schoolname"):
            values['schoolname'] = a
        elif o in ("-a", "--adminpw"):
            values['adminpw'] = a
        elif o in ("-n", "--servername"):
            values['servername'] = a
        elif o in ("-d", "--domainname"):
            values['domainname'] = a
        elif o in ("-r", "--dhcprange"):
            values['dhcprange'] = a
        elif o in ("-s", "--skip-fw"):
            values['skipfw'] = True
        elif o in ("-c", "--config"):
            if os.path.isfile(a):
                values['cli_customini'] = a
            else:
                usage()
                sys.exit()
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    return values


def openSetupLogfile():
    """Open the setup logfile and tee stdout/stderr into it.

    Sets the module-level `logfile` global.
    """
    global logfile
    logfile = environment.SETUPLOG
    subprocess.run(['touch', logfile], check=False)
    subprocess.run(['chmod', '600', logfile], check=True)
    try:
        l = open(logfile, 'w')
        sys.stdout = tee(sys.stdout, l)
        sys.stderr = tee(sys.stderr, l)
    except Exception as error:
        print(f'Cannot open logfile {logfile}: {error}')
        sys.exit()


def writeCustomIni(args):
    """Persist parsed CLI arguments into custom.ini for the a_ini merge step.

    If a --config file was given, it's copied verbatim to custom.ini
    (ignoring all other arguments). Otherwise, each provided CLI argument is
    written individually via modIni(), plus skipfw unconditionally.

    Args:
        args: Dict as returned by parseArguments()
    """
    if args['cli_customini'] != '':
        print('Custom inifile ' + args['cli_customini']
              + ' given on cli, ignoring other arguments!')
        shutil.copy2(args['cli_customini'], environment.CUSTOMINI)
        subprocess.run(['chmod', '600', environment.CUSTOMINI], check=True)
    else:
        # check params
        print('Processing commandline arguments.')
        if args['servername'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'servername', args['servername'])
        if args['domainname'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'domainname', args['domainname'])
        if args['dhcprange'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'dhcprange', args['dhcprange'])
        if args['adminpw'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'adminpw', args['adminpw'])
        if args['schoolname'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'schoolname', args['schoolname'])
        if args['location'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'location', args['location'])
        if args['country'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'country', args['country'])
        if args['state'] != '':
            rc = modIni(environment.CUSTOMINI, 'setup', 'state', args['state'])
        rc = modIni(environment.CUSTOMINI, 'setup', 'skipfw', str(args['skipfw']))


def runSetupModules(unattended):
    """Discover and execute all setup modules in the setup package, in order.

    Skips dialog modules in unattended mode. Enforces a firewall major-
    version check right before d_templates runs (unless skipfw is set).

    Args:
        unattended: If True, skip modules whose name contains 'dialog'
    """
    # work off setup modules from the Python package
    import pkgutil
    from linuxmuster_base7 import setup as setup_package

    # Get all modules from setup package
    setup_modules = []
    for importer, modname, ispkg in pkgutil.iter_modules(setup_package.__path__):
        if not ispkg and modname not in ['__init__', 'helpers']:
            setup_modules.append(modname)

    setup_modules.sort()

    for module_name in setup_modules:
        # skip dialog in unattended mode
        if (unattended and 'dialog' in module_name):
            continue
        # Check firewall major version.
        # Note: re-read skipfw from setup.ini rather than trusting the
        # unattended/args state above - it's only ever set by the standalone
        # -s/--skip-fw flag. A skipfw value provided via -c/--config is
        # copied straight into custom.ini (see writeCustomIni()) and would
        # otherwise be missed here. By this point in the module loop a_ini
        # (which merges defaults.ini < prep.ini < setup.ini < custom.ini
        # into setup.ini) has already run, since 'a_ini' sorts before
        # 'd_templates'.
        if (not getSetupValue('skipfw') and 'templates' in module_name):
            if not checkFwMajorVer():
                sys.exit(1)
        # print module name (extract display name from module name)
        # module names are like: a_ini, c_general-dialog, etc.
        display_name = module_name.split('_', 1)[1] if '_' in module_name else module_name
        printScript('', 'begin')
        printScript(display_name)
        # execute module
        importlib.import_module(f'linuxmuster_base7.setup.{module_name}')


def main():
    """Main entry point for linuxmuster-setup command."""
    args = parseArguments()
    openSetupLogfile()

    # start message
    printScript(os.path.basename(__file__), 'begin')

    writeCustomIni(args)
    runSetupModules(args['unattended'])

    printScript(os.path.basename(__file__), 'end')


if __name__ == '__main__':
    main()
