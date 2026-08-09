#!/usr/bin/python3
#
# regression tests for linuxmuster-setup's --skip-fw handling
# thomas@linuxmuster.net
# 20260809
#
"""
Regression tests for skipfw handling in linuxmuster_base7.cli.setup.

Background: skipfw supplied via -s/--skip-fw sets a local variable in
main() that correctly gates the firewall major-version check
(checkFwMajorVer()) before the d_templates setup module runs. skipfw
supplied via -c/--config used to bypass that local variable entirely - the
config file is copied straight to custom.ini, skipping the individual
modIni() calls that would otherwise persist skipfw - so the version check
ran anyway despite the config file saying skipfw = True.

Fixed by re-reading skipfw fresh via getSetupValue() at the point of the
check, since a_ini (which merges defaults.ini < prep.ini < setup.ini <
custom.ini into setup.ini) has always already run by then - it sorts
before d_templates alphabetically.

These tests fake out the setup module loop entirely (no real setup module
is imported or executed) and redirect every ini/log path into a scratch
directory, so nothing here touches a real system.
"""

import configparser
import importlib
import os
import sys
from unittest import mock

import pytest

pytest.importorskip('environment', reason='requires linuxmuster-common (environment.py) on sys.path')

import environment  # noqa: E402  (import must follow importorskip)


@pytest.fixture
def isolated_setup_paths(tmp_path, monkeypatch):
    """Redirect every ini/log path setup.py touches into a scratch dir."""
    monkeypatch.setattr(environment, 'DEFAULTSINI', str(tmp_path / 'defaults.ini'))
    monkeypatch.setattr(environment, 'PREPINI', str(tmp_path / 'prepare.ini'))
    monkeypatch.setattr(environment, 'SETUPINI', str(tmp_path / 'setup.ini'))
    monkeypatch.setattr(environment, 'CUSTOMINI', str(tmp_path / 'custom.ini'))
    monkeypatch.setattr(environment, 'SETUPLOG', str(tmp_path / 'setup.log'))
    # defaults.ini always ships skipfw = False, mirror that here
    (tmp_path / 'defaults.ini').write_text('[setup]\nskipfw = False\n')
    return tmp_path


@pytest.fixture(autouse=True)
def preserve_stdio():
    """main() replaces sys.stdout/stderr with a tee and never restores them."""
    orig_out, orig_err = sys.stdout, sys.stderr
    try:
        yield
    finally:
        sys.stdout, sys.stderr = orig_out, orig_err


def _fake_a_ini_merge():
    """Stand in for a_ini.py's job: merge the ini cascade into setup.ini."""
    cascade = configparser.RawConfigParser(delimiters=('='))
    for f in (environment.DEFAULTSINI, environment.PREPINI,
              environment.SETUPINI, environment.CUSTOMINI):
        if os.path.isfile(f):
            cascade.read(f)
    with open(environment.SETUPINI, 'w') as fh:
        cascade.write(fh)


def _run_main_with_fake_modules(monkeypatch, argv, checkFwMajorVer_mock):
    """Run setup.main() with a_ini/d_templates faked, no other module runs."""
    from linuxmuster_base7.cli import setup as setup_cli

    fake_modules = [(None, 'a_ini', False), (None, 'd_templates', False)]
    monkeypatch.setattr('pkgutil.iter_modules', lambda path: fake_modules)

    imported = []

    def fake_import_module(name):
        imported.append(name)
        if name.endswith('a_ini'):
            _fake_a_ini_merge()

    monkeypatch.setattr(importlib, 'import_module', fake_import_module)
    monkeypatch.setattr(setup_cli, 'checkFwMajorVer', checkFwMajorVer_mock)
    monkeypatch.setattr(sys, 'argv', argv)

    setup_cli.main()
    return imported


def test_skipfw_from_config_file_skips_version_check(isolated_setup_paths, monkeypatch):
    """skipfw=True in a -c/--config file must gate checkFwMajorVer, same as -s."""
    config_file = isolated_setup_paths / 'myconfig.ini'
    config_file.write_text(
        '[setup]\n'
        'servername = testserver\n'
        'domainname = test.local\n'
        'skipfw = True\n'
    )

    version_check = mock.Mock(return_value=True)
    imported = _run_main_with_fake_modules(
        monkeypatch,
        ['linuxmuster-setup', '-c', str(config_file), '-u'],
        version_check,
    )

    version_check.assert_not_called()
    assert imported == [
        'linuxmuster_base7.setup.a_ini',
        'linuxmuster_base7.setup.d_templates',
    ]


def test_skipfw_via_flag_still_skips_version_check(isolated_setup_paths, monkeypatch):
    """Guard against regressing the already-working -s/--skip-fw path."""
    version_check = mock.Mock(return_value=True)
    _run_main_with_fake_modules(
        monkeypatch,
        ['linuxmuster-setup', '-n', 'testserver', '-d', 'test.local', '-s', '-u'],
        version_check,
    )

    version_check.assert_not_called()


def test_version_check_runs_when_skipfw_not_set(isolated_setup_paths, monkeypatch):
    """Sanity check: without skipfw anywhere, the version check still runs."""
    version_check = mock.Mock(return_value=True)
    _run_main_with_fake_modules(
        monkeypatch,
        ['linuxmuster-setup', '-n', 'testserver', '-d', 'test.local', '-u'],
        version_check,
    )

    version_check.assert_called_once()
