r"""
Cross-platform network drive detection utility.

Detects whether a file path resides on a network drive and whether
that drive/mount is currently accessible. Supports:
- Windows mapped drives (Z:\, etc.)
- Windows UNC paths (\\server\share\...)
- Linux/macOS network mounts (/mnt/..., /media/..., /Volumes/..., NFS, CIFS, SMB)
"""

import os
import sys
import platform


def get_drive_root(file_path):
    """Extract the drive root or mount point from a file path.

    Returns a tuple of (root_path, display_name) where:
    - root_path: The drive root or mount point path to check accessibility
    - display_name: A human-readable name for the drive/mount

    Returns (None, None) if the path is not on a recognizable drive/mount.
    """
    file_path = os.path.abspath(file_path)

    if sys.platform == 'win32':
        return _get_windows_drive_root(file_path)
    else:
        return _get_unix_mount_point(file_path)


def _get_windows_drive_root(file_path):
    r"""Get drive root for Windows paths.

    Handles:
    - Drive letters: Z:\path\to\file -> Z:\
    - UNC paths: \\server\share\path -> \\server\share
    """
    # UNC paths: \\server\share\...
    if file_path.startswith('\\\\'):
        parts = file_path.split('\\')
        # parts = ['', '', 'server', 'share', ...]
        if len(parts) >= 4:
            unc_root = '\\\\' + parts[2] + '\\' + parts[3]
            display_name = '\\\\' + parts[2] + '\\' + parts[3]
            return unc_root, display_name

    # Drive letter paths: Z:\...
    if len(file_path) >= 2 and file_path[1] == ':':
        drive_letter = file_path[0].upper()
        drive_root = drive_letter + ':\\'
        display_name = drive_letter + ':'
        return drive_root, display_name

    return None, None


def _get_unix_mount_point(file_path):
    """Get mount point for Linux/macOS paths.

    Checks /proc/mounts (Linux) or /etc/mtab, or uses os.path.ismount()
    to find the mount point containing this file.
    """
    file_path = os.path.abspath(file_path)

    # Walk up from the file path to find the mount point
    current = file_path
    while current != '/':
        if os.path.ismount(current):
            # Found a mount point - check if it's a network mount
            if _is_network_mount(current):
                display_name = current
                return current, display_name
            # It's a local mount point (/, /home, etc.) - not a network drive
            return None, None
        current = os.path.dirname(current)

    # Reached root - it's local
    return None, None


def _is_network_mount(mount_point):
    """Check if a mount point is a network filesystem (Linux/macOS)."""
    # Common network mount path prefixes
    network_prefixes = ['/mnt/', '/media/', '/net/', '/Volumes/']
    if sys.platform == 'darwin':
        network_prefixes.append('/Volumes/')

    # Check by reading /proc/mounts on Linux for filesystem type
    if sys.platform == 'linux':
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        mounted_on = parts[1]
                        fs_type = parts[2]
                        if mounted_on == mount_point:
                            network_fs_types = {
                                'nfs', 'nfs4', 'cifs', 'smbfs', 'smb',
                                'fuse.sshfs', 'davfs', 'davfs2', '9p',
                                'fuse.rclone', 'fuse.gvfsd-fuse'
                            }
                            return fs_type in network_fs_types
        except (IOError, OSError):
            pass

    # macOS: check with mount command output or by prefix
    if sys.platform == 'darwin':
        # /Volumes/ typically contains network mounts (other than the boot volume)
        if mount_point.startswith('/Volumes/') and mount_point != '/Volumes/Macintosh HD':
            return True
        try:
            import subprocess
            result = subprocess.run(
                ['mount'], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f' on {mount_point} ' in line:
                    for fs_type in ['smbfs', 'nfs', 'afpfs', 'webdav', 'cifs']:
                        if fs_type in line:
                            return True
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Fallback: check common network mount prefixes
    for prefix in network_prefixes:
        if mount_point.startswith(prefix):
            return True

    return False


def is_drive_accessible(file_path):
    """Check if the drive/mount containing a file path is accessible.

    Returns a tuple of (accessible, drive_root, display_name) where:
    - accessible: True if the drive root exists and is reachable
    - drive_root: The drive root path (or None if not on a recognizable drive)
    - display_name: Human-readable drive name for error messages

    If drive_root is None, the file is on a local filesystem and
    standard os.path.exists() logic should be used instead.
    """
    drive_root, display_name = get_drive_root(file_path)

    if drive_root is None:
        # Not on a recognizable network drive - treat as local
        return True, None, None

    # Check if the drive root is accessible
    try:
        accessible = os.path.exists(drive_root)
    except OSError:
        accessible = False

    return accessible, drive_root, display_name


def is_network_path(file_path):
    """Quick check if a path looks like it's on a network drive.

    This is a lightweight check that doesn't verify accessibility.
    """
    if not file_path:
        return False

    file_path = os.path.abspath(file_path)

    if sys.platform == 'win32':
        # UNC paths
        if file_path.startswith('\\\\'):
            return True
        # Mapped drive letters - we can't know without checking, but
        # for Windows we check all non-C: drives as potentially network
        if len(file_path) >= 2 and file_path[1] == ':':
            drive_letter = file_path[0].upper()
            # C: is almost always local, but other letters could be network
            if drive_letter != 'C':
                return _is_windows_network_drive(drive_letter)
    else:
        drive_root, _ = get_drive_root(file_path)
        return drive_root is not None

    return False


def _is_windows_network_drive(drive_letter):
    """Check if a Windows drive letter is a network drive."""
    try:
        import ctypes
        drive_path = drive_letter + ':\\'
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
        # DRIVE_REMOTE = 4
        return drive_type == 4
    except (OSError, AttributeError):
        # ctypes not available or not on Windows - assume potentially network
        # if drive letter is not C:
        return True
