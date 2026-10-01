#!/usr/bin/python3
#
# Filename     : test_functions_linbo.py
# Description  : Tests for the LINBO group id helper pair
#                getLinboGroupId()/splitLinboGroupId().
# Signed-off by: tom.lehmann@netzint.de
# Assisted by  : Claude
# Date         : 20260928
#
"""
Tests for linuxmuster_base7.functions.linbo.getLinboGroupId() and
splitLinboGroupId().

Background: on a multi-school server every school other than default-school
gets school-qualified LINBO group ids '<school>+<group>', so two schools can
use the same group name without sharing one start.conf (see issue #206 and
linuxmuster-linbo7#178). default-school keeps the plain group, so
single-school installations see no change. The helpers must round-trip, and
group names may contain '-' and '_' (sophomorix allows [A-Za-z0-9_-]).
"""

import pytest

pytest.importorskip('environment',
                    reason='requires linuxmuster-common (environment.py) on sys.path')

from linuxmuster_base7.functions import getLinboGroupId, splitLinboGroupId  # noqa: E402


@pytest.mark.parametrize('school, group, expected', [
    # default-school keeps the plain group
    ('default-school', 'raum101', 'raum101'),
    ('default-school', 'win11-efi_2', 'win11-efi_2'),
    # every other school is qualified with '+'
    ('abc', 'raum101', 'abc+raum101'),
    ('abc', 'win11-efi_2', 'abc+win11-efi_2'),
    # school names may contain '-' as well
    ('gs-nord', 'raum101', 'gs-nord+raum101'),
    ('a', 'b-x', 'a+b-x'),
    ('a-b', 'x', 'a-b+x'),
])
def test_get_linbo_group_id(school, group, expected):
    assert getLinboGroupId(school, group) == expected


@pytest.mark.parametrize('group_id, expected', [
    # no '+' means default-school
    ('raum101', ('default-school', 'raum101')),
    ('win11-efi_2', ('default-school', 'win11-efi_2')),
    # otherwise split on the first '+'
    ('abc+raum101', ('abc', 'raum101')),
    ('gs-nord+win11-efi_2', ('gs-nord', 'win11-efi_2')),
    ('a+b+c', ('a', 'b+c')),
])
def test_split_linbo_group_id(group_id, expected):
    assert splitLinboGroupId(group_id) == expected


@pytest.mark.parametrize('school, group', [
    ('default-school', 'raum101'),
    ('default-school', 'win11-efi_2'),
    ('abc', 'raum101'),
    ('gs-nord', 'win11-efi_2'),
    # '-' in either part must not make the ids collide ('a-b-x' with '-')
    ('a', 'b-x'),
    ('a-b', 'x'),
])
def test_round_trip(school, group):
    assert splitLinboGroupId(getLinboGroupId(school, group)) == (school, group)


def test_no_collision_between_schools():
    # school 'a' + group 'b-x' and school 'a-b' + group 'x' would both be
    # 'a-b-x' with '-' as separator
    assert getLinboGroupId('a', 'b-x') != getLinboGroupId('a-b', 'x')
    # a default-school group can never look like a qualified id
    assert getLinboGroupId('default-school', 'abc-raum101') != getLinboGroupId('abc', 'raum101')
