#!/usr/bin/python3
#
# linuxmuster-holiday
# thomas@linuxmuster.net
# 20251113
#

"""
Simple script to test if today is holiday, based on the configuration file
/etc/linuxmuster/sophomorix/SCHOOL/holidays.yml.

Structure of the configuration file (YAML):
holiday_name1:
  start: "dd.mm.yyyy"
  end: "dd.mm.yyyy"
holiday_name2:
  start: "dd.mm.yyyy"
  end: "dd.mm.yyyy"
"""

import getopt
import sys
import yaml

from datetime import date


class Holiday:
    def __init__(self, name, start, end):
        """
        Holiday object.
        :param name: Name of holiday
        :type name: string
        :param start: Start date as dd.mm.yyyy
        :type start: string
        :param end: End as dd.mm.yyyy
        :type end: string
        """

        self.name = name
        self.start = date(*map(int, start.split('.')[::-1]))
        self.end = date(*map(int, end.split('.')[::-1]))

    def __str__(self):
        return f"{self.name} ({self.start} - {self.end})"


def TestToday(config):
    """
    Method to get all holidays stored in configuration file and test if the current day is in holiday.
    """
    today = date.today()

    try:
        with open(config, 'r') as f:
            holidays_dict = yaml.load(f.read(), Loader=yaml.SafeLoader)
    except FileNotFoundError:
        print(f"The file {config} does not seem to exists, you need to configure it first with the Webui.")
        return None
    except yaml.scanner.ScannerError:
        print(f"The file {config} does not seem to respect yaml standards, you need to verify it.")
        return None

    holidays = []
    try:
        for name, dates in holidays_dict.items():
            holidays.append(Holiday(name, dates['start'], dates['end']))

        for holiday in holidays:
            if holiday.start <= today <= holiday.end:
                return holiday
    except AttributeError:
        print(f"The file {config} seems to be empty, you need to configure it first with the Webui.")

    return None


def usage():
    print("""
Usage: linuxmuster-holiday [options]
Options:
    -s, --school <file> - Specify school to process. Process 'default-school' if nothing is specified.
    -h, --help          - Show this help
    """)


def main():
    """Test if today is a holiday."""
    school = 'default-school'

    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            'hs:',
            ['help', 'school=']
        )
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s", "--school"):
            school = a

    config = f"/etc/linuxmuster/sophomorix/{school}/holidays.yml"

    isTodayInHoliday = TestToday(config)

    if isTodayInHoliday is None:
        print("Today is not holiday")
        sys.exit()
    else:
        print(f"Today is holiday in: {isTodayInHoliday}")
        sys.exit(-1)


if __name__ == '__main__':
    main()
