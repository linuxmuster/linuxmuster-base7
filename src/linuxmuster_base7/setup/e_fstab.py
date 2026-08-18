#!/usr/bin/python3
#
# Filename     : e_fstab.py
# Description  : Enable quota, ACL and extended attributes on ext4 filesystems
# Signed-off by: thomas@linuxmuster.net
# Assisted by  : Claude
# Date         : 20260818
#

"""
Setup module e_fstab: Enable quota, ACL and extended attributes on ext4 filesystems.

This module:
- Enables quota feature on ext4 filesystems via tune2fs -O quota
- Updates /etc/fstab with required mount options (acl, usrquota, grpquota, etc.)
- Remounts all affected ext4 filesystems
- Initializes and activates quota on all filesystems
"""

import sys
import subprocess
import datetime

sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
from linuxmuster_base7.functions import mySetupLogfile, printScript

logfile = mySetupLogfile(__file__)
REQUIRED_EXT4_FEATURES = ['quota']
# usrjquota=/grpjquota= (and jqfmt=) are the legacy journaled-quota mount
# options; they conflict with the modern ext4 on-disk quota feature this
# module enables above ("EXT4-fs: Journaled quota options ignored when
# QUOTA feature is enabled"). usrquota/grpquota (no "j") must stay: they
# still gate DQUOT_LIMITS_ENABLED under the on-disk feature.
REQUIRED_MOUNT_OPTIONS = ['acl', 'usrquota', 'grpquota']


def is_ssd(device):
    """Check if device is an SSD by examining /sys/block/*/queue/rotational."""
    # Extract base device name from /dev/xxx
    if device.startswith('/dev/'):
        dev_name = device.split('/')[-1]
        # Remove partition number (e.g., vda1 -> vda)
        dev_name = ''.join([c for c in dev_name if not c.isdigit()])
    else:
        return False

    rotational_path = f'/sys/block/{dev_name}/queue/rotational'
    try:
        with open(rotational_path, 'r') as f:
            rotational = f.read().strip()
        return rotational == '0'
    except Exception:
        return False


def get_mounts():
    """Read current mounts from /proc/self/mounts."""
    mounts = {}
    try:
        with open('/proc/self/mounts', 'r') as mountfile:
            for line in mountfile:
                parts = line.split()
                device = parts[0]
                mountpoint = parts[1]
                fstype = parts[2]
                options = parts[3].split(',') if len(parts) > 3 else []
                mounts[mountpoint] = {
                    'device': device,
                    'fstype': fstype,
                    'options': options,
                }
    except Exception as error:
        sys.exit(1)
    return mounts


def get_ext4_features(device):
    """Query ext4 features from filesystem using tune2fs."""
    result = subprocess.run(['tune2fs', '-l', device], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith('Filesystem features:'):
            return line.split(':', 1)[1].strip().split()
    return []


def is_quota_on(mountpoint):
    """Check whether user quota is genuinely turned on for a mountpoint.

    "quota" appearing in a mount's *active* mount options only means
    usrquota/grpquota were requested at mount time - not that quotaon has
    actually run and enforcement/tracking is live (confirmed: a fresh
    mount straight from a corrected fstab shows "quota" in its options
    immediately, with no aquota files and quotaon never having been
    called). "quotaon -p -u" queries the real, current on/off state
    instead, independent of mount options.
    """
    result = subprocess.run(['quotaon', '-p', '-u', mountpoint], capture_output=True, text=True, check=False)
    return 'is on' in result.stdout


def enable_ext4_quota():
    """Enable the ext4 on-disk quota feature on the root filesystem.

    Only usable for root. tune2fs refuses to touch the quota feature on
    any mounted filesystem ("may only be changed when unmounted and not
    in use") - root can't be unmounted live, so this rebuilds the
    initramfs instead, and linuxmuster-prepare's pre-mount dracut hook
    sets the feature via tune2fs at the next boot. Every other filesystem
    is already fully mounted (and, if it holds live data, typically busy)
    by the time this module runs, so the same approach isn't available
    for them - see the non-root branch in main() for why that's fine.
    """
    result = subprocess.run(['dracut', '--verbose', '--force', '--add', 'linuxmuster'], capture_output=True, text=True, check=False)
    if logfile:
        try:
            with open(logfile, 'a') as log:
                log.write('-' * 78 + '\n')
                log.write(f'#### {datetime.datetime.now()} ####\n')
                log.write(f'#### dracut --verbose --force --add linuxmuster ####\n')
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write('-' * 78 + '\n')
        except Exception:
            pass
    return result.returncode == 0


def mask_redundant_quotaon_units():
    """Mask systemd's quotaon-root.service/quotaon.service (root only).

    Once the ext4 on-disk quota feature is active, the kernel enables
    quota tracking automatically as soon as the filesystem is mounted
    (verified with repquota showing real usage without these units ever
    having run successfully). Calling quotaon afterwards to turn on what's
    already on fails ("quotaon: using . on <dev> [<mnt>]: File exists"),
    permanently failing the unit at every boot for no functional benefit.
    This only applies to root: it's the only filesystem that ever gets the
    on-disk feature here (see the non-root branch in main()).

    quotaon@.service (systemd's own per-mount template unit for every
    other, non-root filesystem) must NOT be masked, even though an earlier
    version of this function did exactly that. Non-root filesystems use
    the external-quota-file mechanism (aquota.user/aquota.group), which -
    unlike the modern on-disk feature - needs an explicit quotaon call
    after *every* boot to reactivate tracking; nothing else does this.
    Masking the template broke that permanently: it "fixed" a genuinely
    real but one-time problem (the very first boot before e_fstab.py has
    ever created the aquota files, where quotaon fails with "cannot find
    ... aquota.user/aquota.group") by disabling the mechanism forever,
    silently turning quota off again on every subsequent reboot even once
    the files existed - confirmed live: unmasking and starting an instance
    succeeds immediately once its aquota files are present, which they
    already are by the time this function is called this run for any
    filesystem that has quota active (quotacheck already ran) or already
    had it from before.

    Explicitly unmasks quotaon@.service in case an older linuxmuster-base7
    version already masked it on this host.

    Masking a unit name systemd hasn't generated (yet) is a harmless no-op.
    """
    subprocess.run(['systemctl', 'mask', 'quotaon-root.service', 'quotaon.service'],
                    capture_output=True, text=True, check=False)
    subprocess.run(['systemctl', 'unmask', 'quotaon@.service'],
                    capture_output=True, text=True, check=False)


# legacy journaled-quota mount options; see the note on REQUIRED_MOUNT_OPTIONS
LEGACY_QUOTA_OPTION_PREFIXES = ('usrjquota=', 'grpjquota=', 'jqfmt=')


def merge_mount_options(current_options, required_options):
    """Merge required mount options with existing options, dropping legacy
    journaled-quota options that conflict with the on-disk quota feature."""
    options = [opt for opt in current_options if not opt.startswith(LEGACY_QUOTA_OPTION_PREFIXES)]
    for required in required_options:
        # Check if option is not already present (handles both key and key=value options)
        option_key = required.split('=')[0]
        if not any(opt.startswith(option_key) for opt in options):
            options.append(required)
    return options


def update_fstab(mountpoint, required_options):
    """Update /etc/fstab with merged mount options."""
    try:
        with open('/etc/fstab', 'r') as f:
            lines = f.readlines()

        updated = False
        for i, line in enumerate(lines):
            # Skip comments and empty lines
            if line.startswith('#') or line.strip() == '':
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            if parts[1] == mountpoint:
                current_options = parts[3].split(',')
                merged_options = merge_mount_options(current_options, required_options)
                parts[3] = ','.join(merged_options)
                lines[i] = '\t'.join(parts) + '\n'
                updated = True
                break

        if updated:
            with open('/etc/fstab', 'w') as f:
                f.writelines(lines)
            return True
    except Exception as error:
        printScript(f'\nFailed to update fstab: {error}')
        return False
    return False


def remount_filesystem(mountpoint, options):
    """Remount filesystem with new options."""
    mount_opts = ','.join(options)
    result = subprocess.run(['mount', '-o', f'remount,{mount_opts}', mountpoint], 
                          capture_output=True, text=True, check=False)
    if logfile:
        try:
            with open(logfile, 'a') as log:
                log.write('-' * 78 + '\n')
                log.write(f'#### {datetime.datetime.now()} ####\n')
                log.write(f'#### mount -o remount,{mount_opts} {mountpoint} ####\n')
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write('-' * 78 + '\n')
        except Exception:
            pass
    return result.returncode == 0


def is_local_device(device):
    """Check if device is local (not a network device)."""
    return device.startswith('/') or device.startswith('UUID=') or device.startswith('LABEL=')


def check_quota_features(mounts):
    """Phase 1: check the ext4 on-disk quota feature on every local ext4
    mount, enabling it for root if needed.

    Args:
        mounts: dict as returned by get_mounts().

    Returns:
        A 3-tuple:
        - ext4_mounts: list of (mountpoint, device, options) for every
          local ext4 mount.
        - enable_quota: True if root needed the dracut+reboot path.
        - quota_needs_activation: True if at least one mount doesn't
          genuinely have quota turned on yet (see is_quota_on() - "quota"
          in the active mount options is not enough, a fresh mount from a
          corrected fstab shows that immediately even though quotaon was
          never called). This must be tracked separately from
          enable_quota: the feature may already have been turned on by
          linuxmuster-prepare's do_dracut() before linuxmuster-setup ever
          ran (the standard prepare -> reboot -> setup order), in which
          case enable_quota is False here even though enforcement hasn't
          been activated for this mount yet. Conversely, on a system
          that's already fully configured, quota is already active here
          too, so quotacheck/quotaon must not be re-run (quotaon fails
          trying to turn on what's already on).
    """
    ext4_mounts = []
    enable_quota = False
    quota_needs_activation = False

    for mountpoint, mount in mounts.items():
        device = mount['device']
        fstype = mount['fstype']

        if fstype != 'ext4':
            continue

        if not is_local_device(device):
            continue

        ext4_mounts.append((mountpoint, device, mount['options']))

        if not is_quota_on(mountpoint):
            quota_needs_activation = True

        msg = f'Checking quota feature on {device} '
        printScript(msg, '', False, False, True)

        features = get_ext4_features(device)
        if features is None:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

        if 'quota' in features:
            printScript(' Enabled!', '', True, True, False, len(msg))
        elif mountpoint == '/':
            # root can't be modified live while mounted - needs a dracut
            # rebuild and a reboot, handled once after this loop
            enable_quota = True
            printScript(' Not enabled!', '', True, True, False, len(msg))
        else:
            # Every other filesystem is already fully mounted at this
            # point (and, if it holds live data, typically busy), so
            # tune2fs can't enable the feature here either - unlike root,
            # there's no dracut+reboot path that would actually work for
            # it either: dracut only activates the LVM volumes it needs to
            # mount root, so a non-root LVM-backed filesystem (e.g.
            # /srv/samba/*) is never visible to its blkid scan, no matter
            # how many reboots happen. Not fatal though: plain
            # usrquota/grpquota mount options (later phases) already give
            # fully working quota via the older external-quota-file
            # mechanism, without needing this feature at all - confirmed
            # with a real quotacheck/quotaon/repquota run.
            printScript(' Not enabled (using external quota files)', '', True, True, False, len(msg))

    if enable_quota:
        msg = 'Enabling ext4 quota '
        printScript(msg, '', False, False, True, len(msg))
        if enable_ext4_quota():
            printScript(' Success!', '', True, True, False, len(msg))
        else:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

    return ext4_mounts, enable_quota, quota_needs_activation


def update_fstab_options(ext4_mounts):
    """Phase 2: update /etc/fstab mount options for every local ext4 mount."""
    for mountpoint, device, current_options in ext4_mounts:
        msg = f'Process mount options for {mountpoint}:'
        printScript(msg)

        required_options = list(REQUIRED_MOUNT_OPTIONS)
        # Add discard option if SSD is detected
        if is_ssd(device):
            if 'discard' not in required_options:
                printScript(' * Detected SSD, discard option added')
                required_options.append('discard')

        merged_options = merge_mount_options(current_options, required_options)
        if set(merged_options) != set(current_options):
            msg = ' * Updating fstab '
            printScript(msg, '', False, False, True, len(msg))
            if update_fstab(mountpoint, required_options):
                subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, text=True, check=False)
                printScript(' Success!', '', True, True, False, len(msg))
            else:
                printScript(' Failed!', '', True, True, False, len(msg))
                sys.exit(1)


def remount_for_activation(ext4_mounts, enable_quota, quota_needs_activation):
    """Phase 3: remount filesystems that need quota activated this run, and
    verify it actually took effect.

    Quota-related mount options can only be set at the *initial* mount -
    the kernel silently keeps a filesystem's existing quota-related
    options across a remount once any of them are already active
    (confirmed live: no combination of remount option changes affects an
    already-active jqfmt-style mount). A filesystem where that happens
    needs a real unmount+mount cycle to pick up the new fstab options,
    i.e. a reboot.

    This must NOT be gated on "not enable_quota" (root needing the
    dracut+reboot path) the way it used to be: root needing a reboot has
    nothing to do with whether some other, unrelated non-root filesystem
    can be activated live right now. Gating the whole loop on root alone
    meant that during a real release upgrade - where root essentially
    always needs enabling here, since linuxmuster-prepare's dracut hook
    only takes effect at the next boot - every non-root filesystem's
    quotacheck/quotaon got skipped for this run too, and nothing ever
    retried them afterwards (quotaon@.service is masked deliberately, see
    mask_redundant_quotaon_units()), leaving their quota silently never
    activated even after the mandatory post-upgrade reboot.

    Returns:
        A 2-tuple (mounts_ready_for_activation, reboot_required_mounts).
    """
    mounts_ready_for_activation = []
    reboot_required_mounts = []
    if not quota_needs_activation:
        return mounts_ready_for_activation, reboot_required_mounts

    for mountpoint, device, current_options in ext4_mounts:
        if is_quota_on(mountpoint):
            continue
        if mountpoint == '/' and enable_quota:
            # already being handled by check_quota_features() (dracut
            # rebuild + reboot) - attempting a remount here would be
            # redundant, and root can't pick up the feature that way
            # regardless
            continue
        msg = f' * Remounting {mountpoint} '
        printScript(msg, '', False, False, True, len(msg))
        subprocess.run(['mount', '-o', 'remount', mountpoint], capture_output=True, text=True, check=False)
        if 'quota' in get_mounts().get(mountpoint, {}).get('options', []):
            printScript('Success!', '', True, True, False, len(msg))
            mounts_ready_for_activation.append(mountpoint)
        else:
            printScript('Needs a reboot!', '', True, True, False, len(msg))
            reboot_required_mounts.append(mountpoint)

    return mounts_ready_for_activation, reboot_required_mounts


def activate_quota(mounts_ready_for_activation):
    """Phase 4: initialize and activate quota, but only for filesystems that
    were just successfully remounted this run.

    Using quotacheck/quotaon -a here would risk erroring on filesystems
    that are already fully active from before, or still stuck on the old
    format - operate on exactly the mountpoints that need it instead.
    """
    if not mounts_ready_for_activation:
        return

    # Best-effort: a filesystem upgraded from the legacy journaled-quota
    # setup (usrjquota=/jqfmt=) may already have quota turned on from
    # before this run, and quotacheck refuses to scan a filesystem with
    # quota currently enabled ("might damage the file"). Not checked for
    # errors - quotaoff itself isn't fully idempotent either (a filesystem
    # that's already off can still report one), and that's fine, it's
    # just here to guarantee a clean slate for the quotacheck/quotaon
    # call below wherever quota was left on.
    subprocess.run(['quotaoff'] + mounts_ready_for_activation, capture_output=True, text=True, check=False)

    msg = 'Initializing quota (quotacheck) '
    printScript(msg, '', False, False, True)
    # -m: don't try to remount read-only first for a paranoia-safe scan -
    # on an already-live system (e.g. during a release upgrade) that
    # remount fails because filesystems are actively being written to,
    # which quotacheck otherwise treats as a hard failure.
    # -u -g: explicit, since quotacheck without either only checks user
    # quota - confirmed live that it silently never creates aquota.group
    # otherwise, only aquota.user.
    # One mountpoint per invocation - confirmed live that quotacheck
    # silently only scans the *first* of several mountpoint arguments and
    # ignores the rest (no error, exit 0), unlike quotaon/quotaoff which
    # do handle multiple arguments correctly.
    for mountpoint in mounts_ready_for_activation:
        result = subprocess.run(['quotacheck', '-m', '-u', '-g', mountpoint], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            printScript(f'Failed: quotacheck error on {mountpoint}', '', True, True, False, len(msg))
            sys.exit(1)
    printScript('Success!', '', True, True, False, len(msg))

    msg = 'Activating quota (quotaon) '
    printScript(msg, '', False, False, True)
    result = subprocess.run(['quotaon'] + mounts_ready_for_activation, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        printScript('Failed: quotaon error', '', True, True, False, len(msg))
        sys.exit(1)
    printScript('Success!', '', True, True, False, len(msg))


def report_quota_status(enable_quota, reboot_required_mounts):
    """Print the reboot-needed summary, if any, for root and/or filesystems
    that couldn't be switched over live this run."""
    if enable_quota:
        printScript('Quota feature enabled on ext4 filesystems. Please reboot to apply changes.')
        printScript('Don\'t forget to invoke \'quotacheck -a\' and \'quotaon -a\' manually after reboot.')

    if reboot_required_mounts:
        printScript('The following filesystems already had quota active in an '
                     'older format and could not be switched over live: '
                     + ', '.join(reboot_required_mounts))
        printScript('Please reboot to apply the new quota configuration on them.')


def mask_quotaon_units(ext4_mounts):
    """Phase 5: mask now-redundant quotaon units, regardless of whether this
    run itself enabled the feature - it may already have been enabled by
    linuxmuster-prepare's do_dracut() before linuxmuster-setup even ran
    (the standard order: prepare, reboot, setup), in which case
    check_quota_features() never called enable_ext4_quota() at all.
    Masking must not depend on that branch, or the units stay enabled and
    fail at the next boot."""
    if not ext4_mounts:
        return
    msg = 'Masking redundant quotaon units '
    printScript(msg, '', False, False, True, len(msg))
    mask_redundant_quotaon_units()
    printScript(' Success!', '', True, True, False, len(msg))


def main():
    mounts = get_mounts()
    ext4_mounts, enable_quota, quota_needs_activation = check_quota_features(mounts)
    update_fstab_options(ext4_mounts)
    mounts_ready_for_activation, reboot_required_mounts = remount_for_activation(
        ext4_mounts, enable_quota, quota_needs_activation)
    activate_quota(mounts_ready_for_activation)
    report_quota_status(enable_quota, reboot_required_mounts)
    mask_quotaon_units(ext4_mounts)


main()

