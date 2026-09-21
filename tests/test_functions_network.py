#!/usr/bin/python3
#
# Filename     : test_functions_network.py
# Description  : Regression tests for isValidHostIpv4()'s subnet-aware
#                validation.
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260921
#
"""
Regression tests for linuxmuster_base7.functions.network.isValidHostIpv4().

Background: the original implementation rejected any address whose first or
last octet was 0 or > 254, guessing at network/broadcast addresses without
knowing the subnet's actual prefix length - correct only by coincidence for
/24 subnets (see issue #205, reported on the 7.4 beta-test forum thread).
isValidHostIpv4() now takes an optional `subnet` argument: without it, it's
a syntax check only; with it, it computes the real network/broadcast
addresses via netaddr and also rejects addresses outside the subnet.
"""

import pytest

pytest.importorskip('environment', reason='requires linuxmuster-common (environment.py) on sys.path')

from linuxmuster_base7.functions import isValidHostIpv4  # noqa: E402


@pytest.mark.parametrize('ip, expected', [
    ('10.16.100.1', True),
    ('0.0.0.0', True),
    ('255.255.255.255', True),
    # regression cases for #205: without a subnet, whether an address ending
    # in .0/.255 is a network/broadcast address is unknowable
    ('10.0.0.0', True),
    ('10.0.0.255', True),
    ('10.0.1.255', True),
    # still-invalid syntax (note: IPy's parser accepts legacy 3-part
    # shorthand like '10.16.100' as '10.16.0.100' - pre-existing behavior,
    # unrelated to this fix, not tested here)
    ('10.16.100.1.2', False),
    ('10.16.100.256', False),
    ('10.16.100.abc', False),
    ('', False),
    (None, False),
])
def test_no_subnet_is_syntax_only(ip, expected):
    assert isValidHostIpv4(ip) == expected


@pytest.mark.parametrize('ip, subnet, expected', [
    # ordinary /24: only the two boundary addresses are invalid
    ('10.0.0.1', '10.0.0.0/24', True),
    ('10.0.0.254', '10.0.0.0/24', True),
    ('10.0.0.0', '10.0.0.0/24', False),    # network address
    ('10.0.0.255', '10.0.0.0/24', False),  # broadcast address
    # larger subnet (#205's counterexamples from the forum): .0/.255
    # mid-range are ordinary hosts, only the subnet's real boundaries aren't
    ('10.0.0.255', '10.0.0.0/23', True),
    ('10.0.1.0', '10.0.0.0/23', True),
    ('10.0.0.0', '10.0.0.0/23', False),    # network address
    ('10.0.1.255', '10.0.0.0/23', False),  # broadcast address
    # smaller subnet: invalid addresses aren't octet-aligned at all
    ('10.0.0.65', '10.0.0.64/26', True),
    ('10.0.0.126', '10.0.0.64/26', True),
    ('10.0.0.64', '10.0.0.64/26', False),  # network address
    ('10.0.0.127', '10.0.0.64/26', False),  # broadcast address
    # outside the subnet entirely
    ('10.0.5.1', '10.0.0.0/24', False),
    # /31 point-to-point: no broadcast concept, both addresses are usable
    ('10.0.0.0', '10.0.0.0/31', True),
    ('10.0.0.1', '10.0.0.0/31', True),
])
def test_subnet_aware_network_broadcast_check(ip, subnet, expected):
    assert isValidHostIpv4(ip, subnet) == expected


def test_malformed_subnet_rejects():
    assert isValidHostIpv4('10.0.0.1', 'not-a-subnet') is False
