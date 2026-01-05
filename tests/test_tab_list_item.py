"""
Tests for TabListItem widget (widgets/tab_list_item.py).
Tests view modes, display updates, and interactions.
"""

import pytest
import os
import tempfile

from widgets.tab_list_item import TabListItem
from models.tab_list_item_model import TextEditorTab


@pytest.fixture
def temp_file_with_content(temp_dir):
    """Create a temporary file with some content"""
    file_path = os.path.join(temp_dir, 'test_document.txt')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('Test content for view mode testing\n')
    return file_path


@pytest.fixture
def editor_tab(qapp, temp_file_with_content):
    """Create a TextEditorTab with a loaded file"""
    tab = TextEditorTab()
    tab.load_file(temp_file_with_content)
    yield tab


@pytest.fixture
def tab_list_item(qapp, editor_tab):
    """Create a TabListItem for testing"""
    item = TabListItem(editor_tab)
    yield item


class TestViewModes:
    """Test tab view mode switching"""

    def test_initial_view_mode_is_normal(self, tab_list_item):
        """Test that default view mode is normal"""
        assert tab_list_item.view_mode == 'normal'

    def test_set_minimized_view_mode(self, tab_list_item):
        """Test switching to minimized view mode"""
        tab_list_item.set_view_mode('minimized')

        assert tab_list_item.view_mode == 'minimized'
        assert not tab_list_item.filename_label.isVisible()
        assert not tab_list_item.save_btn.isVisible()
        assert not tab_list_item.pin_btn.isVisible()
        assert not tab_list_item.close_btn.isVisible()
        assert not tab_list_item.modified_label.isVisible()
        # Emoji should always be visible
        assert tab_list_item.emoji_label.isVisible()

    def test_set_normal_view_mode(self, tab_list_item):
        """Test switching to normal view mode"""
        # First set to minimized, then back to normal
        tab_list_item.set_view_mode('minimized')
        tab_list_item.set_view_mode('normal')

        assert tab_list_item.view_mode == 'normal'
        assert tab_list_item.filename_label.isVisible()
        assert tab_list_item.save_btn.isVisible()
        assert tab_list_item.pin_btn.isVisible()
        assert tab_list_item.close_btn.isVisible()
        assert not tab_list_item.modified_label.isVisible()  # Only visible in maximized

    def test_set_maximized_view_mode(self, tab_list_item):
        """Test switching to maximized view mode"""
        tab_list_item.set_view_mode('maximized')

        assert tab_list_item.view_mode == 'maximized'
        assert tab_list_item.filename_label.isVisible()
        assert tab_list_item.save_btn.isVisible()
        assert tab_list_item.pin_btn.isVisible()
        assert tab_list_item.close_btn.isVisible()
        assert tab_list_item.modified_label.isVisible()  # Only visible in maximized

    def test_maximized_shows_last_modified_time(self, tab_list_item):
        """Test that maximized view shows last modified time"""
        tab_list_item.set_view_mode('maximized')

        # Should have some date text (not empty)
        modified_text = tab_list_item.modified_label.text()
        assert modified_text != ""
        # Should contain typical date elements
        assert any(month in modified_text for month in
                   ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])

    def test_cycle_through_all_view_modes(self, tab_list_item):
        """Test cycling through all view modes doesn't crash"""
        modes = ['minimized', 'normal', 'maximized', 'normal', 'minimized', 'maximized']

        for mode in modes:
            tab_list_item.set_view_mode(mode)
            assert tab_list_item.view_mode == mode


class TestViewModeWithUnsavedFile:
    """Test view modes with unsaved (new) files"""

    @pytest.fixture
    def unsaved_tab_list_item(self, qapp):
        """Create a TabListItem with an unsaved file"""
        tab = TextEditorTab()  # No file loaded
        tab.text_edit.setPlainText("Unsaved content")
        item = TabListItem(tab)
        yield item

    def test_minimized_mode_unsaved_file(self, unsaved_tab_list_item):
        """Test minimized mode with unsaved file doesn't crash"""
        unsaved_tab_list_item.set_view_mode('minimized')
        assert unsaved_tab_list_item.view_mode == 'minimized'

    def test_normal_mode_unsaved_file(self, unsaved_tab_list_item):
        """Test normal mode with unsaved file doesn't crash"""
        unsaved_tab_list_item.set_view_mode('normal')
        assert unsaved_tab_list_item.view_mode == 'normal'

    def test_maximized_mode_unsaved_file(self, unsaved_tab_list_item):
        """Test maximized mode with unsaved file doesn't crash"""
        unsaved_tab_list_item.set_view_mode('maximized')
        assert unsaved_tab_list_item.view_mode == 'maximized'
        # Modified label should be empty for unsaved files
        assert unsaved_tab_list_item.modified_label.text() == ""


class TestGetLastModified:
    """Test the get_last_modified method"""

    def test_get_last_modified_with_file(self, tab_list_item):
        """Test getting last modified time for a real file"""
        result = tab_list_item.get_last_modified()
        assert result != ""
        assert isinstance(result, str)

    def test_get_last_modified_without_file(self, qapp):
        """Test getting last modified time for unsaved file"""
        tab = TextEditorTab()  # No file
        item = TabListItem(tab)

        result = item.get_last_modified()
        assert result == ""

    def test_get_last_modified_nonexistent_file(self, qapp):
        """Test getting last modified time for nonexistent file path"""
        tab = TextEditorTab()
        tab.file_path = "/nonexistent/path/to/file.txt"
        item = TabListItem(tab)

        result = item.get_last_modified()
        assert result == ""
