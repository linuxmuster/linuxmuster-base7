#!/usr/bin/python3
#
# Filename     : security.py
# Description  : Password generation, validation and interactive prompt helpers
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

import getpass
import random
import re
import string

from .core import printScript


def hasNumbers(password):
    return any(char.isdigit() for char in password)


def randomPassword(size):
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    while True:
        password = ''.join(random.choice(chars) for x in range(size))
        if hasNumbers(password) is True:
            break
    return password


def isValidPassword(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        7 characters length or more
        1 digit or 1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """
    # calculating the length
    length_error = len(password) < 7
    # searching for digits
    digit_error = re.search(r"\d", password) is None
    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None
    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None
    # no $ in pw
    unwanted_error = re.search(r"\$", password) is not None
    # searching for symbols
    if digit_error is True:
        digit_error = False
        symbol_error = re.search(r"[@!#%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None
    else:
        symbol_error = False
    # overall result
    password_ok = not (
        length_error or digit_error or uppercase_error or lowercase_error
        or symbol_error or unwanted_error
        )
    return password_ok


# enter password
def enterPassword(pwtype='the', validate=True, repeat=True):
    msg = '#### Enter ' + pwtype + ' password: '
    re_msg = '#### Please re-enter ' + pwtype + ' password: '
    while True:
        password = getpass.getpass(msg)
        if validate and not isValidPassword(password):
            printScript(
                'Weak password! A password is considered strong if it contains:')
            printScript(' * 7 characters length or more')
            printScript(' * 1 digit or 1 symbol or more')
            printScript(' * 1 uppercase letter or more')
            printScript(' * 1 lowercase letter or more')
            continue
        elif password == '' or password is None:
            continue
        if repeat:
            password_repeated = getpass.getpass(re_msg)
            if password != password_repeated:
                printScript('Passwords do not match!')
                continue
            else:
                break
        else:
            break
    return password
