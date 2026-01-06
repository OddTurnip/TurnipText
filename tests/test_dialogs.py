"""
Tests for the extracted dialog classes in windows/dialogs.py
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt

from windows.dialogs import (
    EditTabDialog, EditGroupDialog, AboutDialog,
    UnsavedChangesDialog, UnsavedGroupDialog, GroupChangeWarningDialog
)


class TestEditTabDialog:
    """Tests for EditTabDialog"""

    def test_initialization(self, qapp):
        """Test dialog initializes with correct values from tab_item"""
        # Create mock tab_item
        mock_tab_item = MagicMock()
        mock_tab_item.custom_icon = None
        mock_tab_item.custom_emoji = None
        mock_tab_item.custom_display_name = None
        mock_tab_item.get_emoji.return_value = "📄"
        mock_tab_item.editor_tab.file_path = "/path/to/test.txt"
        mock_tab_item.editor_tab.is_pinned = False

        dialog = EditTabDialog(mock_tab_item)

        assert dialog.tab_item == mock_tab_item
        assert dialog.pending_icon is None
        assert dialog.windowTitle() == "Edit Tab Appearance"

        dialog.close()

    def test_initialization_with_custom_values(self, qapp):
        """Test dialog initializes with existing custom values"""
        mock_tab_item = MagicMock()
        mock_tab_item.custom_icon = "custom_icon.png"
        mock_tab_item.custom_emoji = "🚀"
        mock_tab_item.custom_display_name = "My Custom Tab"
        mock_tab_item.get_emoji.return_value = "🚀"
        mock_tab_item.editor_tab.file_path = "/path/to/file.md"
        mock_tab_item.editor_tab.is_pinned = True

        dialog = EditTabDialog(mock_tab_item)

        assert dialog.pending_icon == "custom_icon.png"
        assert dialog.emoji_input.text() == "🚀"
        assert dialog.name_input.text() == "My Custom Tab"
        assert dialog.pin_checkbox.isChecked() is True

        dialog.close()

    def test_get_results_after_accept(self, qapp):
        """Test results are correctly returned after dialog acceptance"""
        mock_tab_item = MagicMock()
        mock_tab_item.custom_icon = None
        mock_tab_item.custom_emoji = None
        mock_tab_item.custom_display_name = None
        mock_tab_item.get_emoji.return_value = "📄"
        mock_tab_item.editor_tab.file_path = "/test/file.txt"
        mock_tab_item.editor_tab.is_pinned = False

        dialog = EditTabDialog(mock_tab_item)

        # Simulate user input
        dialog.emoji_input.setText("🎉")
        dialog.name_input.setText("Party Time")
        dialog.pin_checkbox.setChecked(True)
        dialog.pending_icon = "new_icon.png"

        # Trigger accept
        dialog._on_accept()

        icon, emoji, display_name, pinned = dialog.get_results()

        assert icon == "new_icon.png"
        assert emoji == "🎉"
        assert display_name == "Party Time"
        assert pinned is True

        dialog.close()


class TestEditGroupDialog:
    """Tests for EditGroupDialog"""

    def test_initialization_empty(self, qapp):
        """Test dialog initializes with no current name"""
        dialog = EditGroupDialog(None, None)

        assert dialog.windowTitle() == "Edit Tab Group"
        assert dialog.name_input.text() == ""
        assert "TurnipText" in dialog.name_input.placeholderText()

        dialog.close()

    def test_initialization_with_name(self, qapp):
        """Test dialog initializes with existing name"""
        dialog = EditGroupDialog("My Project", "/path/to/project.tabs")

        assert dialog.name_input.text() == "My Project"

        dialog.close()

    def test_placeholder_from_tabs_file(self, qapp):
        """Test placeholder shows filename from tabs file"""
        dialog = EditGroupDialog(None, "/path/to/MyProject.tabs")

        assert "MyProject" in dialog.name_input.placeholderText()

        dialog.close()

    def test_get_result(self, qapp):
        """Test result is correctly returned"""
        dialog = EditGroupDialog(None, None)

        dialog.name_input.setText("New Project Name")
        dialog._on_accept()

        assert dialog.get_result() == "New Project Name"

        dialog.close()

    def test_get_result_empty_returns_none(self, qapp):
        """Test empty input returns None"""
        dialog = EditGroupDialog("Old Name", None)

        dialog.name_input.setText("")
        dialog._on_accept()

        assert dialog.get_result() is None

        dialog.close()


class TestAboutDialog:
    """Tests for AboutDialog"""

    def test_initialization(self, qapp):
        """Test dialog initializes correctly"""
        dialog = AboutDialog()

        assert dialog.windowTitle() == "About TurnipText"
        assert dialog.minimumWidth() >= 450

        dialog.close()


class TestUnsavedChangesDialog:
    """Tests for UnsavedChangesDialog"""

    def test_result_codes(self):
        """Test result code constants are defined correctly"""
        assert UnsavedChangesDialog.CANCEL == 0
        assert UnsavedChangesDialog.EXIT_WITHOUT_SAVING == 1
        assert UnsavedChangesDialog.SAVE_AND_EXIT == 2

    def test_initialization(self, qapp):
        """Test dialog initializes with file list"""
        files = ["file1.txt", "file2.md", "Untitled"]

        dialog = UnsavedChangesDialog(files)

        assert dialog.windowTitle() == "Unsaved Changes"
        # Check files are mentioned somewhere in the dialog
        # (We can't easily access the label text, but initialization should work)

        dialog.close()


class TestUnsavedGroupDialog:
    """Tests for UnsavedGroupDialog"""

    def test_result_codes(self):
        """Test result code constants are defined correctly"""
        assert UnsavedGroupDialog.CANCEL == 0
        assert UnsavedGroupDialog.EXIT_WITHOUT_SAVING == 1
        assert UnsavedGroupDialog.SAVE_GROUP == 2

    def test_initialization(self, qapp):
        """Test dialog initializes with group name"""
        dialog = UnsavedGroupDialog("My Project")

        assert dialog.windowTitle() == "Unsaved Tab Group"

        dialog.close()


class TestGroupChangeWarningDialog:
    """Tests for GroupChangeWarningDialog"""

    def test_result_codes(self):
        """Test result code constants are defined correctly"""
        assert GroupChangeWarningDialog.CANCEL == 0
        assert GroupChangeWarningDialog.DONT_SAVE == 1
        assert GroupChangeWarningDialog.SAVE_ALL == 2

    def test_initialization_with_files_only(self, qapp):
        """Test dialog with unsaved files only"""
        files = ["file1.txt", "file2.txt"]

        dialog = GroupChangeWarningDialog(files, False, "Project")

        assert dialog.windowTitle() == "Unsaved Changes"

        dialog.close()

    def test_initialization_with_group_changes_only(self, qapp):
        """Test dialog with group changes only"""
        dialog = GroupChangeWarningDialog([], True, "Project")

        assert dialog.windowTitle() == "Unsaved Changes"

        dialog.close()

    def test_initialization_with_both(self, qapp):
        """Test dialog with both unsaved files and group changes"""
        files = ["modified.txt"]

        dialog = GroupChangeWarningDialog(files, True, "Project")

        assert dialog.windowTitle() == "Unsaved Changes"

        dialog.close()
