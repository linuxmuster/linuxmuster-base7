#!/usr/bin/python3
#
# linuxmuster-update-ntpconf
# thomas@linuxmuster.net
# 20260921
#

import datetime
import environment
import shutil
import subprocess
import sys

from linuxmuster_base7.functions import getSetupValue, getSubnetArray, \
    printScript, readTextfile, writeTextfile


def main():
    """Update ntpsec configuration with current network settings."""
    printScript('Updating ntpsec configuration:')

    # read necessary values from setup.ini and other sources
    firewallip = getSetupValue('firewallip')
    timestamp = str(datetime.datetime.now()).replace('-', '').replace(' ', '').replace(':', '').split('.')[0]

    # read template
    cfgtemplate = environment.TPLDIR + '/ntp.conf'
    rc, content = readTextfile(cfgtemplate)
    cfgfile = content.split('\n')[0].replace('# ', '')
    # create backup of current configuration
    bakfile = cfgfile + '-' + timestamp
    printScript('* Creating backup ' + bakfile + '.')
    try:
        shutil.copy2(cfgfile, bakfile)
    except Exception as e:
        printScript('* Failed to backup ' + cfgfile + ': ' + str(e))
        sys.exit(1)

    # get subnets
    printScript('* Processing subnets')
    subnets = [row[0] for row in getSubnetArray()]

    # create config lines for restricted subnets
    restricted_subnets = None
    # iterate over subnets
    for subnet in subnets:
        printScript('  -  ' + subnet)
        if restricted_subnets is None:
            restricted_subnets = 'restrict ' + subnet
        else:
            restricted_subnets = restricted_subnets + '\nrestrict ' + subnet
    # replace placeholders with values
    content = content.replace('@@firewallip@@', firewallip).replace('@@restricted_subnets@@', restricted_subnets).replace('@@ntpsockdir@@', environment.NTPSOCKDIR)
    # write content to cfgfile
    printScript('* Writing ' + cfgfile + '.')
    writeTextfile(cfgfile, content, 'w')

    # restart ntp service
    printScript('* Restarting ntpsec service.')
    subprocess.run(['systemctl', 'restart', 'ntpsec.service'], check=False)


if __name__ == '__main__':
    main()
