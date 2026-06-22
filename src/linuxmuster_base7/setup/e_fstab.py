#!/usr/bin/python3
#
# Configure ext4 filesystems for quota and ACL support
# thomas@linuxmuster.net
# 20260622
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
REQUIRED_MOUNT_OPTIONS = ['acl', 'usrquota', 'usrjquota=aquota.user', 'grpquota', 'grpjquota=aquota.group']


def is_ssd(device):
    """Check if device is an SSD by examining /sys/block/*/queue/rotational."""
    msg = 'Check if device is an SSD '
    printScript(msg, '', False, False, True, len(msg))
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
    msg = 'Read current mounts '
    printScript(msg, '', False, False, True, len(msg))
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
        printScript(f'Failed to read /proc/self/mounts: {error}', '', True, True, False)
        sys.exit(1)
    return mounts


def get_ext4_features(device):
    """Query ext4 features from filesystem using tune2fs."""
    msg = 'Query ext4 features from filesystem '
    printScript(msg, '', False, False, True, len(msg))
    result = subprocess.run(['tune2fs', '-l', device], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith('Filesystem features:'):
            return line.split(':', 1)[1].strip().split()
    return []


def enable_ext4_quota(device):
    """Enable quota feature on ext4 filesystem."""
    msg = 'Enable quota feature using premount task during next reboot '
    printScript(msg, '', False, False, True, len(msg))
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


def merge_mount_options(current_options, required_options):
    """Merge required mount options with existing options."""
    msg = 'Merge mount options '
    printScript(msg, '', False, False, True, len(msg))
    options = list(current_options)
    for required in required_options:
        # Check if option is not already present (handles both key and key=value options)
        option_key = required.split('=')[0]
        if not any(opt.startswith(option_key) for opt in options):
            options.append(required)
    return options


def update_fstab(mountpoint, required_options):
    """Update /etc/fstab with merged mount options."""
    msg = 'Update fstab '
    printScript(msg, '', False, False, True, len(msg))
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
        printScript(f'Failed to update fstab: {error}', '', True, True, False)
        return False
    return False


def remount_filesystem(mountpoint, options):
    """Remount filesystem with new options."""
    msg = 'Remount filesystem '
    printScript(msg, '', False, False, True, len(msg))
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
    msg = 'Check if device is local '
    printScript(msg, '', False, False, True, len(msg))
    return device.startswith('/') or device.startswith('UUID=') or device.startswith('LABEL=')


def main():
    mounts = get_mounts()
    ext4_mounts = []

    # Phase 1: Enable quota feature on all ext4 filesystems
    for mountpoint, mount in mounts.items():
        device = mount['device']
        fstype = mount['fstype']

        if fstype != 'ext4':
            continue

        if not is_local_device(device):
            continue

        ext4_mounts.append((mountpoint, device, mount['options']))

        msg = f'Enabling quota feature on {device} '
        printScript(msg, '', False, False, True)

        features = get_ext4_features(device)
        if features is None:
            msg = 'Failed: cannot query ext4 features'
            printScript(msg, '', True, True, False, len(msg))
            sys.exit(1)

        if 'quota' not in features:
            if not enable_ext4_quota(device):
                msg = 'Failed: tune2fs error'
                printScript(msg, '', True, True, False, len(msg))
                sys.exit(1)
            msg = 'Success!'
            printScript(msg, '', True, True, False, len(msg))
        else:
            msg = 'Already enabled'
            printScript(msg, '', True, True, False, len(msg))

    # Phase 2: Update fstab mount options for all ext4 filesystems
    for mountpoint, device, current_options in ext4_mounts:
        msg = f'Updating /etc/fstab for {mountpoint} '
        printScript(msg, '', False, False, True, len(msg))

        required_options = list(REQUIRED_MOUNT_OPTIONS)
        # Add discard option if SSD is detected
        if is_ssd(device):
            if 'discard' not in required_options:
                required_options.append('discard')

        merged_options = merge_mount_options(current_options, required_options)
        if set(merged_options) != set(current_options):
            if not update_fstab(mountpoint, required_options):
                printScript('Failed: fstab update error', '', True, True, False, len(msg))
                sys.exit(1)
            printScript('Success!', '', True, True, False, len(msg))
        else:
            printScript('Already correct', '', True, True, False, len(msg))

    # Phase 3: Remount all ext4 filesystems
    for mountpoint, device, _ in ext4_mounts:
        msg = f'Remounting {mountpoint} '
        printScript(msg, '', False, False, True)

        # Read current mount options from fstab
        new_options = None
        try:
            with open('/etc/fstab', 'r') as f:
                for line in f:
                    if line.startswith('#') or line.strip() == '':
                        continue
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] == mountpoint:
                        new_options = parts[3].split(',')
                        break
        except Exception as error:
            printScript(f'Failed to read fstab: {error}', '', True, True, False, len(msg))
            sys.exit(1)

        if new_options is None:
            printScript('Failed: cannot read fstab', '', True, True, False, len(msg))
            sys.exit(1)

        if not remount_filesystem(mountpoint, new_options):
            printScript('Failed: remount error', '', True, True, False, len(msg))
            sys.exit(1)
        printScript('Success!', '', True, True, False, len(msg))

    # Phase 4: Initialize and activate quota
    if ext4_mounts:
        msg = 'Initializing quota (quotacheck -a) '
        printScript(msg, '', False, False, True)
        result = subprocess.run(['quotacheck', '-a'], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            printScript('Failed: quotacheck error', '', True, True, False, len(msg))
            sys.exit(1)
        printScript('Success!', '', True, True, False, len(msg))

        msg = 'Activating quota (quotaon -a) '
        printScript(msg, '', False, False, True)
        result = subprocess.run(['quotaon', '-a'], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            printScript('Failed: quotaon error', '', True, True, False, len(msg))
            sys.exit(1)
        printScript('Success!', '', True, True, False, len(msg))


if __name__ == '__main__':
    main()

