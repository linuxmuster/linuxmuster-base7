#!/usr/bin/python3
#
# Filename     : test_import_devices.py
# Description  : Tests for the LINBO group ids that import_devices.py writes
#                into the DHCP config, the link csv and the start.conf/grub
#                cfg file names.
# Signed-off by: tom.lehmann@netzint.de
# Assisted by  : Claude
# Date         : 20260928
#
"""
Tests for the use of getLinboGroupId() in linuxmuster_base7.cli.import_devices.

default-school output must stay byte-for-byte identical (plain group names),
every other school gets the qualified id '<school>+<group>' in the DHCP
extensions-path/nis-domain options, the start.conf/grub cfg link sources and
the start.conf.<id>/<id>.cfg files (see issue #206). getDevicesArray() is
stubbed with the rows it would return, and the LINBO directories of the
environment module are pointed to tmp_path.
"""

import io

import pytest

environment = pytest.importorskip('environment',
                                  reason='requires linuxmuster-common (environment.py) on sys.path')

from linuxmuster_base7.cli import import_devices  # noqa: E402

# rows as getDevicesArray() returns them: the hostname already carries the
# school prefix for non-default schools, the group does not
DHCP_ROWS = {
    'default-school': [['pc01', 'raum101', '00:11:22:33:44:55', '10.0.0.1', '', 'pc', '1']],
    'abc': [['abc-pc01', 'raum101', '00:11:22:33:44:56', '10.0.0.2', '', 'pc', '1']],
}
LINK_ROWS = {
    'default-school': [
        ['pc01', 'raum101', '00:11:22:33:44:55', '10.0.0.1', '1'],
        ['pc02', 'raum101', '00:11:22:33:44:57', 'DHCP', '1'],
    ],
    'abc': [
        ['abc-pc01', 'raum101', '00:11:22:33:44:56', '10.0.0.2', '1'],
        ['abc-pc02', 'win11-efi_2', 'AA:11:22:33:44:58', 'DHCP', '1'],
    ],
}


def stubDevicesArray(monkeypatch, rows):
    def getDevicesArray(fieldnrs='', subnet='', pxeflag='', school='default-school'):
        return rows[school]
    monkeypatch.setattr(import_devices, 'getDevicesArray', getDevicesArray)


@pytest.fixture
def linbodir(tmp_path, monkeypatch):
    linbo_dir = tmp_path / 'srv' / 'linbo'
    grub_dir = linbo_dir / 'boot' / 'grub'
    tpl_dir = tmp_path / 'templates'
    (grub_dir / 'hostcfg').mkdir(parents=True)
    tpl_dir.mkdir()
    # unconfigured default start.conf (no Cache) and forced netboot template
    (linbo_dir / 'start.conf').write_text('[LINBO]\nServer = 10.0.0.1\nGroup = \n')
    (tpl_dir / 'grub.cfg.forced_netboot').write_text('# forced netboot\n')
    monkeypatch.setattr(environment, 'LINBODIR', str(linbo_dir))
    monkeypatch.setattr(environment, 'LINBOGRUBDIR', str(grub_dir))
    monkeypatch.setattr(environment, 'LINBOTPLDIR', str(tpl_dir))
    return linbo_dir


def test_dhcp_default_school_unchanged(monkeypatch):
    stubDevicesArray(monkeypatch, DHCP_ROWS)
    outfile = io.StringIO()
    import_devices.processDevicesForSubnet(outfile, '10.0.0.0/24', 'default-school')
    assert outfile.getvalue() == (
        '# subnet 10.0.0.0/24\n'
        'host pc01 {\n'
        '  option host-name "pc01";\n'
        '  hardware ethernet 00:11:22:33:44:55;\n'
        '  fixed-address 10.0.0.1;\n'
        '  option extensions-path "raum101";\n'
        '  option nis-domain "raum101";\n'
        '}\n'
    )


def test_dhcp_other_school_qualified(monkeypatch):
    stubDevicesArray(monkeypatch, DHCP_ROWS)
    outfile = io.StringIO()
    import_devices.processDevicesForSubnet(outfile, '10.0.0.0/24', 'abc')
    assert outfile.getvalue() == (
        '# subnet 10.0.0.0/24\n'
        'host abc-pc01 {\n'
        '  option host-name "abc-pc01";\n'
        '  hardware ethernet 00:11:22:33:44:56;\n'
        '  fixed-address 10.0.0.2;\n'
        '  option extensions-path "abc+raum101";\n'
        '  option nis-domain "abc+raum101";\n'
        '}\n'
    )


def test_links_default_school_unchanged(monkeypatch, linbodir):
    stubDevicesArray(monkeypatch, LINK_ROWS)
    pxe_groups = import_devices.doPxeGroupsBySchool(school='default-school')
    assert pxe_groups == ['raum101']
    links = (linbodir / 'boot' / 'links' / 'default-school.csv').read_bytes().decode()
    grub_dir = environment.LINBOGRUBDIR
    assert links == (
        f'start.conf.raum101;{linbodir}/start.conf-10.0.0.1\r\n'
        f'../raum101.cfg;{grub_dir}/hostcfg/pc01.cfg\r\n'
        f'start.conf.raum101;{linbodir}/start.conf-00:11:22:33:44:57\r\n'
        f'../raum101.cfg;{grub_dir}/hostcfg/pc02.cfg\r\n'
    )


def test_links_other_school_qualified(monkeypatch, linbodir):
    stubDevicesArray(monkeypatch, LINK_ROWS)
    pxe_groups = import_devices.doPxeGroupsBySchool(school='abc')
    assert pxe_groups == ['abc+raum101', 'abc+win11-efi_2']
    links = (linbodir / 'boot' / 'links' / 'abc.csv').read_bytes().decode()
    grub_dir = environment.LINBOGRUBDIR
    assert links == (
        f'start.conf.abc+raum101;{linbodir}/start.conf-10.0.0.2\r\n'
        f'../abc+raum101.cfg;{grub_dir}/hostcfg/abc-pc01.cfg\r\n'
        f'start.conf.abc+win11-efi_2;{linbodir}/start.conf-aa:11:22:33:44:58\r\n'
        f'../abc+win11-efi_2.cfg;{grub_dir}/hostcfg/abc-pc02.cfg\r\n'
    )


@pytest.mark.parametrize('school, group_id, host', [
    ('default-school', 'raum101', 'pc01'),
    ('abc', 'abc+raum101', 'abc-pc01'),
])
def test_startconf_grubcfg_and_links(monkeypatch, linbodir, school, group_id, host):
    stubDevicesArray(monkeypatch, LINK_ROWS)
    versionfile = linbodir / 'linbo-version'
    versionfile.write_text('LINBO 4.3.12: Codename\n')
    monkeypatch.setattr(environment, 'LINBOVERFILE', str(versionfile))
    import_devices.generateGrubConfigsForGroups(school)
    grub_dir = linbodir / 'boot' / 'grub'
    # doLinboStartconf()/doGrubCfg() create the files under the group id ...
    assert (linbodir / ('start.conf.' + group_id)).is_file()
    assert (grub_dir / (group_id + '.cfg')).is_file()
    # ... and doAllGroupLinks() points the host links at them
    assert (linbodir / ('start.conf-' + LINK_ROWS[school][0][3])).resolve() == \
        (linbodir / ('start.conf.' + group_id)).resolve()
    assert (grub_dir / 'hostcfg' / (host + '.cfg')).resolve() == \
        (grub_dir / (group_id + '.cfg')).resolve()
