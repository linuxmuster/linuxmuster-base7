#!/usr/bin/python3
#
# linuxmuster-setup.py
# thomas@linuxmuster.net
# 20170324
#

import constants
import getopt
import importlib
import os
import sys
from functions import printScript
from functions import subProc
from functions import tee

def usage():
    print('Usage: linuxmuster-setup.py [options]')
    print(' [options] may be:')
    print(' -c <file>, --config=<file> : path to ini file with setup values')
    print(' -u,        --unattended    : unattended mode, do not ask questions')
    print(' -s,        --skip-fw-setup : skip firewall SSH setup')
    print(' -h,        --help          : print this help')

# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "c:hsu", ["config=", "help", "unattended", "skip-fw-setup"])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
unattended = False
skip_firewall = False

# evaluate options
for o, a in opts:
    if o == "-u":
        unattended = True
    if o == "-s":
        skip_firewall = True
    elif o in ("-c", "--config"):
        if os.path.isfile(a):
            subProc('cp ' + a + ' ' + constants.CUSTOMINI)
            subProc('chmod 600 ' + constants.CUSTOMINI)
        else:
            usage()
            sys.exit()
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    else:
        assert False, "unhandled option"

# open logfile
global logfile
logfile = constants.SETUPLOG
subProc('touch ' + logfile)
subProc('chmod 600 ' + logfile)
try:
    l = open(logfile, 'w')
    orig_out = sys.stdout
    sys.stdout = tee(sys.stdout, l)
    sys.stderr = tee(sys.stderr, l)
except:
    fail('Cannot open logfile ' + logfile + ' !')
    sys.exit()

# start message
printScript(os.path.basename(__file__), 'begin')

# work off setup modules
setup_modules = os.listdir(constants.SETUPDIR)
setup_modules.remove('__pycache__')
setup_modules.sort()
for f in setup_modules:
    if (unattended == True and f == 'b_dialog.py'):
        continue
    if (skip_firewall == True and f == 'f_ssh.py'):
        continue
    m = os.path.splitext(f)[0]
    importlib.import_module(m)

printScript(os.path.basename(__file__), 'end')
