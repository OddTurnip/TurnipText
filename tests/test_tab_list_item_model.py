"""
Tests for TextEditorTab model (models/tab_list_item_model.py).
Tests file I/O, modification tracking, content management, and pinning.
"""

import pytest
import os
from pathlib import Path

from models.tab_list_item_model import TextEditorTab


class TestTextEditorTabCreation:
    """Test tab creation and initialization"""

    def test_create_empty_tab(self, qapp):
        """Test creating a tab without a file"""
        tab = TextEditorTab()
        assert tab.file_path is None
        assert tab.is_modified is False
        assert tab.is_pinned is False
        assert tab.text_edit is not None
        assert tab.get_content() == ''

    def test_create_tab_with_file(self, qapp, temp_file):
        """Test creating a tab with an existing file"""
        tab = TextEditorTab(file_path=temp_file)
        assert tab.file_path == temp_file
        assert tab.is_modified is False
        assert 'Initial test content' in tab.get_content()


class TestFileLoading:
    """Test file loading functionality"""

    def test_load_existing_file(self, qapp, temp_file, mock_messagebox):
        """Test loading an existing file"""
        tab = TextEditorTab()
        result = tab.load_file(temp_file)

        assert result is True
        assert tab.file_path == temp_file
        assert tab.is_modified is False
        assert 'Initial test content' in tab.get_content()

    def test_load_nonexistent_file(self, qapp, temp_dir, mock_messagebox):
        """Test loading a file that doesn't exist"""
        tab = TextEditorTab()
        fake_path = os.path.join(temp_dir, 'nonexistent.txt')
        result = tab.load_file(fake_path)

        assert result is False
        # File path should not be updated on failure
        assert tab.file_path is None

    def test_load_file_with_unicode(self, qapp, temp_dir, mock_messagebox):
        """Test loading file with unicode content"""
        unicode_file = os.path.join(temp_dir, 'unicode.txt')
        with open(unicode_file, 'w', encoding='utf-8') as f:
            f.write('Hello 世界 🌍 Привет мир\n')

        tab = TextEditorTab()
        result = tab.load_file(unicode_file)

        assert result is True
        content = tab.get_content()
        assert '世界' in content
        assert '🌍' in content
        assert 'Привет' in content


class TestFileSaving:
    """Test file saving functionality"""

    def test_save_new_file(self, qapp, temp_dir, mock_messagebox):
        """Test saving content to a new file"""
        tab = TextEditorTab()
        tab.set_content('New content for testing')

        new_file = os.path.join(temp_dir, 'new_file.txt')
        result = tab.save_file(new_file)

        assert result is True
        assert tab.file_path == new_file
        assert tab.is_modified is False

        # Verify file was actually written
        with open(new_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == 'New content for testing'

    def test_save_existing_file(self, qapp, temp_file, mock_messagebox):
        """Test saving to an existing file"""
        tab = TextEditorTab(file_path=temp_file)
        tab.set_content('Modified content')

        result = tab.save_file()

        assert result is True
        assert tab.is_modified is False

        # Verify file was actually updated
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == 'Modified content'

    def test_save_without_filepath(self, qapp, mock_messagebox):
        """Test that save fails when no file path is set"""
        tab = TextEditorTab()
        tab.set_content('Some content')

        result = tab.save_file()

        assert result is False

    def test_save_with_unicode(self, qapp, temp_dir, mock_messagebox):
        """Test saving unicode content"""
        tab = TextEditorTab()
        unicode_content = 'Testing unicode: 世界 🌍 Привет мир\n'
        tab.set_content(unicode_content)

        new_file = os.path.join(temp_dir, 'unicode_save.txt')
        result = tab.save_file(new_file)

        assert result is True

        # Verify unicode was preserved
        with open(new_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == unicode_content


class TestModificationTracking:
    """Test modification tracking functionality"""

    def test_initial_state_not_modified(self, qapp):
        """Test that new tabs are not marked as modified"""
        tab = TextEditorTab()
        assert tab.is_modified is False

    def test_loaded_file_not_modified(self, qapp, temp_file):
        """Test that loaded files are not marked as modified"""
        tab = TextEditorTab(file_path=temp_file)
        assert tab.is_modified is False

    def test_text_change_marks_modified(self, qapp, qtbot):
        """Test that text changes mark tab as modified"""
        tab = TextEditorTab()
        assert tab.is_modified is False

        # Simulate text change
        tab.text_edit.setPlainText('New text')

        # Wait for signal to propagate
        qtbot.wait(10)

        assert tab.is_modified is True

    def test_set_content_clears_modified(self, qapp):
        """Test that set_content clears the modified flag"""
        tab = TextEditorTab()
        tab.is_modified = True

        tab.set_content('New content')

        assert tab.is_modified is False

    def test_save_clears_modified(self, qapp, temp_dir, mock_messagebox):
        """Test that saving clears the modified flag"""
        tab = TextEditorTab()
        tab.set_content('Content')
        tab.is_modified = True

        new_file = os.path.join(temp_dir, 'test.txt')
        tab.save_file(new_file)

        assert tab.is_modified is False


class TestContentManagement:
    """Test content get/set operations"""

    def test_get_empty_content(self, qapp):
        """Test getting content from empty tab"""
        tab = TextEditorTab()
        assert tab.get_content() == ''

    def test_set_and_get_content(self, qapp):
        """Test setting and getting content"""
        tab = TextEditorTab()
        test_content = 'Test content\nWith multiple lines\n'

        tab.set_content(test_content)

        assert tab.get_content() == test_content

    def test_set_content_preserves_newlines(self, qapp):
        """Test that newlines are preserved"""
        tab = TextEditorTab()
        content = 'Line 1\nLine 2\nLine 3\n'

        tab.set_content(content)

        assert tab.get_content() == content

    def test_set_content_with_special_chars(self, qapp):
        """Test content with special characters"""
        tab = TextEditorTab()
        content = 'Tabs:\t\t\tSpaces:   \nQuotes: " \' `\nSymbols: @#$%^&*()\n'

        tab.set_content(content)

        assert tab.get_content() == content


class TestMarkdownHighlighting:
    """Test that markdown highlighting doesn't affect modification state"""

    def test_markdown_toggle_no_spurious_modification(self, qapp, qtbot):
        """Test that toggling markdown highlighting doesn't mark tab as modified"""
        tab = TextEditorTab()
        tab.set_content('# Header\n\nSome **bold** and *italic* text.')
        assert tab.is_modified is False

        # Enable markdown highlighting
        tab.text_edit.set_markdown_highlighting(True)
        qtbot.wait(50)  # Wait for any deferred highlighting

        assert tab.is_modified is False, "Enabling highlighting shouldn't mark as modified"

        # Disable markdown highlighting
        tab.text_edit.set_markdown_highlighting(False)
        qtbot.wait(50)  # Wait for any deferred operations

        assert tab.is_modified is False, "Disabling highlighting shouldn't mark as modified"

        # Toggle on and off again (the bug scenario)
        tab.text_edit.set_markdown_highlighting(True)
        qtbot.wait(50)
        tab.text_edit.set_markdown_highlighting(False)
        qtbot.wait(50)
        tab.text_edit.set_markdown_highlighting(True)
        qtbot.wait(50)

        assert tab.is_modified is False, "Multiple toggles shouldn't mark as modified"

    def test_markdown_toggle_preserves_real_modifications(self, qapp, qtbot):
        """Test that real modifications are preserved when toggling markdown"""
        tab = TextEditorTab()
        tab.set_content('Original content')
        assert tab.is_modified is False

        # Make a real modification
        tab.text_edit.setPlainText('Modified content')
        qtbot.wait(10)
        assert tab.is_modified is True

        # Toggle markdown highlighting
        tab.text_edit.set_markdown_highlighting(True)
        qtbot.wait(50)

        assert tab.is_modified is True, "Real modification should be preserved"

        tab.text_edit.set_markdown_highlighting(False)
        qtbot.wait(50)

        assert tab.is_modified is True, "Real modification should still be preserved"

    def test_undo_restores_unmodified_state(self, qapp, qtbot):
        """Test that undoing changes correctly updates modified state"""
        tab = TextEditorTab()
        original = 'Original content'
        tab.set_content(original)
        assert tab.is_modified is False

        # Make a modification
        tab.text_edit.setPlainText('Modified content')
        qtbot.wait(10)
        assert tab.is_modified is True

        # Undo to restore original content
        tab.text_edit.setPlainText(original)
        qtbot.wait(10)

        # Content matches saved baseline, so should be unmodified
        assert tab.is_modified is False, "Matching original content should be unmodified"


class TestPinningState:
    """Test tab pinning functionality"""

    def test_initial_unpinned(self, qapp):
        """Test that tabs start unpinned"""
        tab = TextEditorTab()
        assert tab.is_pinned is False

    def test_toggle_pinning(self, qapp):
        """Test toggling pin state"""
        tab = TextEditorTab()

        tab.is_pinned = True
        assert tab.is_pinned is True

        tab.is_pinned = False
        assert tab.is_pinned is False

    def test_pinning_persists_across_save(self, qapp, temp_dir, mock_messagebox):
        """Test that pinning state doesn't affect file operations"""
        tab = TextEditorTab()
        tab.is_pinned = True
        tab.set_content('Content')

        new_file = os.path.join(temp_dir, 'pinned.txt')
        result = tab.save_file(new_file)

        assert result is True
        assert tab.is_pinned is True  # Should remain pinned
