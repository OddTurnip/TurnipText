"""
Tests for network drive detection utility and drive error overlay.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.network_drive import (
    get_drive_root,
    is_drive_accessible,
    is_network_path,
    _get_windows_drive_root,
    _get_unix_mount_point,
)


class TestGetWindowsDriveRoot:
    """Test Windows drive root extraction."""

    def test_drive_letter_path(self):
        """Drive letter paths should return the drive root."""
        root, display = _get_windows_drive_root('Z:\\Users\\test\\file.txt')
        assert root == 'Z:\\'
        assert display == 'Z:'

    def test_drive_letter_lowercase(self):
        """Lowercase drive letters should be uppercased."""
        root, display = _get_windows_drive_root('z:\\Users\\test\\file.txt')
        assert root == 'Z:\\'
        assert display == 'Z:'

    def test_unc_path(self):
        """UNC paths should return server\\share root."""
        root, display = _get_windows_drive_root('\\\\server\\share\\path\\file.txt')
        assert root == '\\\\server\\share'
        assert display == '\\\\server\\share'

    def test_unc_path_short(self):
        """Short UNC paths with only server should return None."""
        root, display = _get_windows_drive_root('\\\\server')
        assert root is None
        assert display is None

    def test_no_drive_letter(self):
        """Paths without drive letters or UNC should return None."""
        root, display = _get_windows_drive_root('relative\\path\\file.txt')
        assert root is None
        assert display is None

    def test_c_drive(self):
        """C: drive should still be detected (it's up to caller to decide if network)."""
        root, display = _get_windows_drive_root('C:\\Windows\\System32\\file.txt')
        assert root == 'C:\\'
        assert display == 'C:'


class TestGetDriveRoot:
    """Test cross-platform drive root detection."""

    @patch('utils.network_drive.sys')
    def test_windows_path_delegation(self, mock_sys):
        """On Windows, should delegate to Windows handler."""
        mock_sys.platform = 'win32'
        with patch('utils.network_drive._get_windows_drive_root') as mock_win:
            mock_win.return_value = ('Z:\\', 'Z:')
            root, display = get_drive_root('Z:\\test\\file.txt')
            mock_win.assert_called_once()

    @patch('utils.network_drive.sys')
    def test_unix_path_delegation(self, mock_sys):
        """On Linux/Mac, should delegate to Unix handler."""
        mock_sys.platform = 'linux'
        with patch('utils.network_drive._get_unix_mount_point') as mock_unix:
            mock_unix.return_value = ('/mnt/nas', '/mnt/nas')
            root, display = get_drive_root('/mnt/nas/file.txt')
            mock_unix.assert_called_once()


class TestIsDriveAccessible:
    """Test drive accessibility checking."""

    @patch('utils.network_drive.get_drive_root')
    @patch('utils.network_drive.os.path.exists')
    def test_accessible_network_drive(self, mock_exists, mock_get_root):
        """Accessible network drive should return True."""
        mock_get_root.return_value = ('Z:\\', 'Z:')
        mock_exists.return_value = True
        accessible, root, display = is_drive_accessible('Z:\\test\\file.txt')
        assert accessible is True
        assert root == 'Z:\\'
        assert display == 'Z:'

    @patch('utils.network_drive.get_drive_root')
    @patch('utils.network_drive.os.path.exists')
    def test_inaccessible_network_drive(self, mock_exists, mock_get_root):
        """Inaccessible network drive should return False."""
        mock_get_root.return_value = ('Z:\\', 'Z:')
        mock_exists.return_value = False
        accessible, root, display = is_drive_accessible('Z:\\test\\file.txt')
        assert accessible is False
        assert root == 'Z:\\'
        assert display == 'Z:'

    @patch('utils.network_drive.get_drive_root')
    def test_local_path(self, mock_get_root):
        """Local paths should return True with None root."""
        mock_get_root.return_value = (None, None)
        accessible, root, display = is_drive_accessible('C:\\local\\file.txt')
        assert accessible is True
        assert root is None
        assert display is None

    @patch('utils.network_drive.get_drive_root')
    @patch('utils.network_drive.os.path.exists')
    def test_os_error_returns_inaccessible(self, mock_exists, mock_get_root):
        """OSError during check should return inaccessible."""
        mock_get_root.return_value = ('Z:\\', 'Z:')
        mock_exists.side_effect = OSError("Network error")
        accessible, root, display = is_drive_accessible('Z:\\test\\file.txt')
        assert accessible is False


class TestDriveErrorOverlay:
    """Test the drive error overlay widget."""

    def test_overlay_creation(self, qapp):
        """Overlay should create successfully with drive name."""
        from widgets.drive_error_overlay import DriveErrorOverlay
        overlay = DriveErrorOverlay("Z:")
        assert overlay.drive_display_name == "Z:"
        assert "Z:" in overlay.drive_label.text()
        overlay.deleteLater()

    def test_overlay_update_drive_name(self, qapp):
        """Updating drive name should update the label."""
        from widgets.drive_error_overlay import DriveErrorOverlay
        overlay = DriveErrorOverlay("Z:")
        overlay.update_drive_name("\\\\server\\share")
        assert "\\\\server\\share" in overlay.drive_label.text()
        overlay.deleteLater()

    def test_retry_callback_called(self, qapp):
        """Clicking retry should call the callback."""
        from widgets.drive_error_overlay import DriveErrorOverlay
        overlay = DriveErrorOverlay("Z:")
        callback = MagicMock(return_value=False)
        overlay.set_retry_callback(callback)
        overlay._on_retry_clicked()
        callback.assert_called_once()
        overlay.deleteLater()

    def test_retry_success_message(self, qapp):
        """Successful retry should show reconnected message."""
        from widgets.drive_error_overlay import DriveErrorOverlay
        overlay = DriveErrorOverlay("Z:")
        callback = MagicMock(return_value=True)
        overlay.set_retry_callback(callback)
        overlay._on_retry_clicked()
        assert "reconnected" in overlay.status_label.text().lower()
        overlay.deleteLater()

    def test_retry_cooldown(self, qapp):
        """After failed retry, button should be disabled during cooldown."""
        from widgets.drive_error_overlay import DriveErrorOverlay
        overlay = DriveErrorOverlay("Z:")
        callback = MagicMock(return_value=False)
        overlay.set_retry_callback(callback)
        overlay._on_retry_clicked()
        assert not overlay.retry_button.isEnabled()
        assert overlay._cooldown_active is True
        overlay.deleteLater()


class TestTabDriveError:
    """Test TextEditorTab drive error overlay integration."""

    def test_show_drive_error(self, qapp):
        """Showing drive error should display overlay and set readonly."""
        from models.tab_list_item_model import TextEditorTab
        tab = TextEditorTab()
        tab.show_drive_error("Z:", lambda: False)
        assert tab.has_drive_error
        assert tab.text_edit.isReadOnly()
        tab.deleteLater()

    def test_hide_drive_error(self, qapp):
        """Hiding drive error should restore editing."""
        from models.tab_list_item_model import TextEditorTab
        tab = TextEditorTab()
        tab.show_drive_error("Z:", lambda: False)
        tab.hide_drive_error()
        assert not tab.has_drive_error
        assert not tab.text_edit.isReadOnly()
        tab.deleteLater()

    def test_has_drive_error_initially_false(self, qapp):
        """New tab should not have drive error."""
        from models.tab_list_item_model import TextEditorTab
        tab = TextEditorTab()
        assert not tab.has_drive_error
        tab.deleteLater()
