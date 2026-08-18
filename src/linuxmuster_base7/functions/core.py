#!/usr/bin/python3
#
# Filename     : core.py
# Description  : Core console-output, logging and setup.ini helpers shared
#                by all other functions submodules
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import configparser
import datetime
import os
import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment


# append stdout to logfile
class tee(object):

    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()  # If you want the output to be visible immediately

    def flush(self):
        for f in self.files:
            f.flush()


# print with or without linefeed
def printLf(msg, lf):
    if lf:
        print(msg, flush=True)
    else:
        print(msg, end='', flush=True)


# print script output
def printScript(msg='', header='', lf=True, noleft=False, noright=False,
                offset=0):
    linelen = 78
    borderlen = 4
    border = '#' * borderlen
    sep = '-' * linelen
    if header == 'begin' or header == 'end':
        printLf(sep, lf)
        if msg == '':
            return True
        if header == 'begin':
            headermsg = 'started'
        else:
            headermsg = 'finished'
        now = datetime.datetime.now()
        msg = msg + ' ' + headermsg + ' at ' + str(now).split('.')[0]
    if not noleft:
        line = border + ' ' + msg
    else:
        line = msg
    if not noright:
        padding = linelen - len(msg) - borderlen * 2 - 2 - offset
        if noleft:
            line = '.' * padding + msg + ' ' + border
        else:
            line = line + ' ' * padding + ' ' + border
    printLf(line, lf)
    if header == 'begin' or header == 'end':
        printLf(sep, lf)


# get key value from setup.ini
def getSetupValue(keyname):
    setupini = environment.SETUPINI
    try:
        setup = configparser.RawConfigParser(delimiters=('='))
        setup.read(setupini)
        rc = setup.get('setup', keyname)
        if rc == 'False':
            rc = False
        elif rc == 'True':
            rc = True
    except Exception as error:
        print(error)
        return ''
    return rc


# return my setup logfile path
def mySetupLogfile(fpath):
    myname = os.path.splitext(os.path.basename(fpath))[0].split('_')[1]
    logfile = environment.LOGDIR + '/setup.' + myname + '.log'
    return logfile


# return datetime string
def dtStr():
    return "{:%Y%m%d%H%M%S}".format(datetime.datetime.now())


# return setup comment for modified configfiles
def setupComment():
    msg = '# modified by linuxmuster-setup at ' + dtStr() + '\n'
    return msg
