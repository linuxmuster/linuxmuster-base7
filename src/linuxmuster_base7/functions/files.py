#!/usr/bin/python3
#
# Filename     : files.py
# Description  : Text file, secret file and ini file read/write helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import codecs
import configparser
import os
import shutil
from shutil import copyfile

from .core import dtStr


# return content of text file
def readTextfile(tfile):
    if not os.path.isfile(tfile):
        return False, None
    try:
        infile = codecs.open(tfile, 'r', encoding='utf-8', errors='ignore')
        content = infile.read()
        infile.close()
        return True, content
    except Exception as error:
        print(error)
        return False, None


# write textfile
def writeTextfile(tfile, content, flag):
    try:
        outfile = open(tfile, flag)
        outfile.write(content)
        outfile.close()
        return True
    except Exception as error:
        print(error)
        return False


# write a secret to a file, restricting its permissions from creation onward
# (avoids the window between a plain write and a later chmod call)
def writeSecretFile(tfile, content, mode=0o600):
    try:
        fd = os.open(tfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
        try:
            os.write(fd, content.encode('utf-8'))
        finally:
            os.close(fd)
        return True
    except Exception as error:
        print(error)
        return False


# replace string in file
def replaceInFile(tfile, search, replace):
    rc = False
    try:
        bakfile = tfile + '.bak'
        copyfile(tfile, bakfile)
        rc, content = readTextfile(tfile)
        rc = writeTextfile(tfile, content.replace(search, replace), 'w')
    except Exception as error:
        print(error)
        if os.path.isfile(bakfile):
            copyfile(bakfile, tfile)
    if os.path.isfile(bakfile):
        os.unlink(bakfile)
    return rc


# modify and write ini file
def modIni(inifile, section, option, value, mode=None):
    try:
        i = configparser.RawConfigParser(delimiters=('='))
        if not os.path.isfile(inifile):
            # create inifile; if mode is given, create it with restrictive
            # permissions from the start (e.g. for files holding secrets)
            if mode is not None:
                writeSecretFile(inifile, '[' + section + ']\n', mode)
            else:
                writeTextfile(inifile, '[' + section + ']\n', 'w')
        i.read(inifile)
        i.set(section, option, value)
        with open(inifile, 'w') as outfile:
            i.write(outfile)
        return True
    except Exception as error:
        print(error)
        return False


# concatenate files safely without shell injection risk
def catFiles(filelist, outfile):
    """
    Concatenate multiple files into a single output file.

    Uses binary mode to preserve file contents exactly (important for certificates).
    Avoids shell injection by using native Python file operations instead of subprocess.

    Args:
        filelist: List of file paths to concatenate
        outfile: Output file path where concatenated content will be written
    """
    import shutil
    with open(outfile, 'wb') as out:
        for filepath in filelist:
            with open(filepath, 'rb') as infile:
                shutil.copyfileobj(infile, out)


# backup config file
def backupCfg(configfile):
    if not os.path.isfile(configfile):
        return False
    backupfile = configfile + '.' + dtStr()
    try:
        shutil.copy(configfile, backupfile)
    except Exception as error:
        print(error)
        return False
    return True
