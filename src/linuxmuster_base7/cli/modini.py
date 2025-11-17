#!/usr/bin/python3
#
# linuxmuster-modini
# thomas@linuxmuster.net
# 20251117
#

import getopt
import os
import subprocess
import sys

from linuxmuster_base7.functions import modIni, printLf


def usage():
    """Print usage information and command-line options.

    Displays help text showing all available command-line options for modifying
    INI files. Includes example usage with Samba configuration file.
    """
    print('Modify ini files on command line. Usage: linuxmuster-modini [options]')
    print(' [options] may be:')
    print(' -i <path/to/inifile>, --inifile=<path/to/inifile> : Path to inifile (mandatory).')
    print(' -s <sectionname>,     --section=<sectionname>     : Name of section to work on (mandatory).')
    print(' -o <optionname>,      --option=<optionname>       : Name of option (mandatory).')
    print(' -v <value>,           --value=<value>             : value of option (mandatory).')
    print(' -r <servicename>,     --service=<servicename>     : Name of service to restart (optional).')
    print(' -h,                   --help                      : print this help')
    print("Example: linuxmuster-modini -i /etc/samba/smb.conf -s global -o 'time server' -v Yes -r samba-ad-dc")


def main():
    """Main entry point for CLI tool.

    Command-line utility to modify INI-style configuration files.
    This tool provides a convenient way to programmatically update configuration
    files (like smb.conf, php.ini, etc.) and optionally restart related services.

    Workflow:
    1. Parse command-line arguments
    2. Validate that the INI file exists
    3. Validate that all required parameters are provided
    4. Modify the INI file (section/option/value)
    5. Optionally restart a service if -r/--service is specified

    Exit codes:
        0: Success
        1: Modification or service restart failed
        2: Invalid command-line arguments
    """
    # Step 1: Parse command-line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hi:o:r:s:v:",
                                   ["help", "inifile=", "section=", "option=", "value=", "service="])
    except getopt.GetoptError as err:
        # Print error message (e.g., "option -a not recognized")
        print(err)
        usage()
        sys.exit(2)

    # Step 2: Extract option values from parsed arguments
    inifile = None   # Path to the INI file to modify
    section = None   # Section name in the INI file (e.g., [global])
    option = None    # Option name to modify (e.g., 'time server')
    value = None     # New value for the option
    service = None   # Optional: service to restart after modification

    for o, a in opts:
        if o in ("-i", "--inifile"):
            inifile = a
        elif o in ("-s", "--section"):
            section = a
        elif o in ("-o", "--option"):
            option = a
        elif o in ("-v", "--value"):
            value = a
        elif o in ("-r", "--service"):
            service = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"

    # Step 3: Validate that INI file exists
    if inifile is not None and not os.path.isfile(inifile):
        print('File not found!')
        usage()
        sys.exit()

    # Step 4: Validate that all required parameters are provided
    # Note: inifile can be None (modIni will create it if needed)
    if section is None or option is None or value is None:
        print('Parameter error!')
        usage()
        sys.exit()

    # Step 5: Modify the INI file using modIni() function
    # This function handles INI parsing, section/option creation, and writing
    printLf('Modifying ' + inifile + ' ... ', False)
    rc = modIni(inifile, section, option, value)
    if rc is True:
        rc = 0  # Success
        print('OK!')
    else:
        rc = 1  # Failure
        print('Failed!')

    # Step 6: Restart service if requested (and modification was successful)
    if service is not None and rc == 0:
        printLf('Restarting ' + service + ' ... ', False)
        result = subprocess.run(['service', service, 'restart'], check=False)
        rc = result.returncode
        if rc == 0:
            print('OK!')
        else:
            print('Failed!')

    sys.exit(rc)


if __name__ == '__main__':
    main()
