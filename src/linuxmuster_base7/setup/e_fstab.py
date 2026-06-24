#!/usr/bin/python3
#
# Configure ext4 filesystems for quota and ACL support
# thomas@linuxmuster.net
# 20260623
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
        printScript(' Failed!', '', True, True, False, len(msg))
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


def enable_ext4_quota():
    """Enable quota feature on ext4 filesystem."""
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
    options = list(current_options)
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


def main():
    mounts = get_mounts()
    ext4_mounts = []
    enable_quota = False

    # Phase 1: Enable quota feature on all ext4 filesystems
    for mountpoint, mount in mounts.items():
        device = mount['device']
        fstype = mount['fstype']

        if fstype != 'ext4':
            continue

        if not is_local_device(device):
            continue

        ext4_mounts.append((mountpoint, device, mount['options']))

        msg = f'Checking quota feature on {device} '
        printScript(msg, '', False, False, True)

        features = get_ext4_features(device)
        if features is None:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

        if 'quota' in features:
            printScript(' Enabled!', '', True, True, False, len(msg))
        else:
            enable_quota = True
            printScript(' Not enabled!', '', True, True, False, len(msg))
    
    if enable_quota:
        msg = 'Enabling ext4 quota '
        printScript(msg, '', False, False, True, len(msg))
        if enable_ext4_quota():
            printScript(' Success!', '', True, True, False, len(msg))
        else:
            printScript(' Failed!', '', True, True, False, len(msg))
            sys.exit(1)

    # Phase 2: Update fstab mount options for all ext4 filesystems
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

    # Phase 3: Remount all ext4 filesystems
    for mountpoint, device, _ in ext4_mounts:
        msg = ' * Remounting '
        printScript(msg, '', False, False, True)

        if subprocess.run(['mount', '-o', 'remount', f'{mountpoint}'], 
                          capture_output=True, text=True, check=False):
            printScript('Success!', '', True, True, False, len(msg))
        else:
            printScript('Failed: remount error', '', True, True, False, len(msg))
            sys.exit(1)

    # Phase 4: Initialize and activate quota
    if ext4_mounts and not enable_quota:
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
    
    if enable_quota:
        printScript('Quota feature enabled on ext4 filesystems. Please reboot to apply changes.')
        printScript('Don\'t forget to invoke \'quotacheck -a\' and \'quotaon -a\' manually after reboot.')


main()

