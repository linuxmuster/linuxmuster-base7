#!/usr/bin/python3
#
# linuxmuster-setup.py
# thomas@linuxmuster.net
# 20180502
#

import constants
import getopt
import importlib
import os
import sys
from functions import modIni
from functions import printScript
from functions import subProc
from functions import tee

def usage():
    print('Usage: linuxmuster-setup.py [options]')
    print(' [options] may be:')
    print(' -n <hostname>,   --servername=<hostname>   : Set server hostname.')
    print(' -d <domainname>, --domainname=<domainname> : Set domainname.')
    print(' -r <dhcprange>,  --dhcprange=<dhcprange>   : Set dhcp range.')
    print(' -o <opsiip>,     --opsiip=<opsiip>         : Set opsi ip.')
    print(' -k <dockerip>,   --dockerip=<dockerip>     : Set docker ip.')
    print(' -m <mailip>,     --mailip=<mailip>         : Set mailserver ip.')
    print(' -a <adminpw>,    --adminpw=<adminpw>       : Set admin password.')
    print(' -y <smtprelay>,  --smtprelay=<smtprelay>   : Set smtp relay.')
    print(' -t <smtpuser>,   --smtpuser=<smtpuser>     : Set smtp user.')
    print(' -p <smtppw>,     --smtppw=<smtppw>         : Set smtp user password.')
    print(' -e <schoolname>, --schoolname=<schoolname> : Set school name.')
    print(' -l <location>,   --location=<location>     : Set school location.')
    print(' -z <country>,    --country=<country>       : Set school country.')
    print(' -v <state>,      --country=<state>         : Set school state.')
    print(' -c <file>,       --config=<file>           : path to ini file with setup values')
    print(' -u,              --unattended              : unattended mode, do not ask questions')
    print(' -s,              --skip-fw                 : skip firewall setup per ssh')
    print(' -h,              --help                    : print this help')

# get cli args
try:
    opts, args = getopt.getopt(sys.argv[1:], "a:c:d:e:hk:l:m:n:o:p:r:st:uv:y:z:", ["adminpw=", "config=", "domainname=", "schoolname=", "help", "dockerip=", "location=", "mailip=", "servername=", "opsiip=", "smtppw=", "dhcprange=", "skip-fw", "smtpuser=", "unattended", "state=", "smtprelay=", "country="])
except getopt.GetoptError as err:
    # print help information and exit:
    print(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
unattended = False
skipfw = False
servername = ''
domainname = ''
dhcprange = ''
dockerip = ''
mailip = ''
opsiip = ''
adminpw = ''
smtprelay = ''
smtpuser = ''
smtppw = ''
schoolname = ''
location = ''
country = ''
state = ''

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
    elif o in ("-p", "--smtppw"):
        smtppw = a
    elif o in ("-t", "--smtpuser"):
        smtpuser = a
    elif o in ("-y", "--smtprelay"):
        smtprelay = a
    elif o in ("-a", "--adminpw"):
        adminpw = a
    elif o in ("-n", "--servername"):
        servername = a
    elif o in ("-d", "--domainname"):
        domainname = a
    elif o in ("-r", "--dhcprange"):
        dhcprange = a
    elif o in ("-o", "--opsiip"):
        opsiip = a
    elif o in ("-k", "--dockerip"):
        dockerip = a
    elif o in ("-m", "--mailip"):
        mailip = a
    elif o in ("-s", "--skipfw"):
        skipfw = True
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

# start message
printScript(os.path.basename(__file__), 'begin')

# check params
if servername != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'servername', servername)
if domainname != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'domainname', domainname)
if dhcprange != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'dhcprange', dhcprange)
if opsiip != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'opsiip', opsiip)
if dockerip != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'dockerip', dockerip)
if mailip != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'mailip', mailip)
if adminpw != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'adminpw', adminpw)
if smtprelay != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'smtprelay', smtprelay)
if smtpuser != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'smtpuser', smtpuser)
if smtppw != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'smtppw', smtppw)
if schoolname != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'schoolname', schoolname)
if location != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'location', location)
if country != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'country', country)
if state != '':
    rc = modIni(constants.CUSTOMINI, 'setup', 'state', state)

# save setups flags to custom.ini
rc = modIni(constants.CUSTOMINI, 'setup', 'skipfw', str(skipfw))

# work off setup modules
setup_modules = os.listdir(constants.SETUPDIR)
setup_modules.remove('__pycache__')
setup_modules.sort()
for f in setup_modules:
    # skip dialog in unattended mode
    if (unattended == True and 'dialog.py' in f):
        continue
    # skip firewall setup
    if (skipfw == True and 'firewall.py' in f):
        continue
    # execute module
    m = os.path.splitext(f)[0]
    importlib.import_module(m)

printScript(os.path.basename(__file__), 'end')
