"""
Tests for TabListWidget - the sidebar container for tabs.
"""

import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QWidget

from widgets.tab_list import TabListWidget
from models.tab_list_item_model import TextEditorTab


class MockEditorTab:
    """Mock editor tab for testing without file I/O"""

    def __init__(self, file_path=None, is_pinned=False):
        self.file_path = file_path
        self.is_pinned = is_pinned
        self.is_modified = False
        self.text_edit = MagicMock()


class TestTabListWidget:
    """Tests for TabListWidget"""

    def test_initialization(self, qapp):
        """Test widget initializes correctly"""
        widget = TabListWidget()

        assert widget.tab_items == []
        assert widget.view_mode == 'normal'

        widget.close()

    def test_add_tab(self, qapp):
        """Test adding a tab"""
        widget = TabListWidget()
        mock_tab = MockEditorTab("/path/to/file.txt")

        tab_item = widget.add_tab(mock_tab)

        assert len(widget.tab_items) == 1
        assert tab_item in widget.tab_items
        assert tab_item.editor_tab == mock_tab

        widget.close()

    def test_add_multiple_tabs(self, qapp):
        """Test adding multiple tabs"""
        widget = TabListWidget()

        tab1 = MockEditorTab("/path/to/file1.txt")
        tab2 = MockEditorTab("/path/to/file2.txt")
        tab3 = MockEditorTab("/path/to/file3.txt")

        widget.add_tab(tab1)
        widget.add_tab(tab2)
        widget.add_tab(tab3)

        assert len(widget.tab_items) == 3

        widget.close()

    def test_add_pinned_tab_at_top(self, qapp):
        """Test pinned tabs are added at the top"""
        widget = TabListWidget()

        # Add unpinned tab first
        unpinned = MockEditorTab("/path/to/unpinned.txt", is_pinned=False)
        widget.add_tab(unpinned)

        # Add pinned tab second
        pinned = MockEditorTab("/path/to/pinned.txt", is_pinned=True)
        widget.add_tab(pinned)

        # Pinned tab should be first
        assert widget.tab_items[0].editor_tab == pinned
        assert widget.tab_items[1].editor_tab == unpinned

        widget.close()

    def test_add_multiple_pinned_tabs(self, qapp):
        """Test multiple pinned tabs are ordered correctly"""
        widget = TabListWidget()

        unpinned1 = MockEditorTab("/path/to/unpinned1.txt", is_pinned=False)
        unpinned2 = MockEditorTab("/path/to/unpinned2.txt", is_pinned=False)
        pinned1 = MockEditorTab("/path/to/pinned1.txt", is_pinned=True)
        pinned2 = MockEditorTab("/path/to/pinned2.txt", is_pinned=True)

        widget.add_tab(unpinned1)
        widget.add_tab(pinned1)
        widget.add_tab(unpinned2)
        widget.add_tab(pinned2)

        # Pinned tabs should be at top
        assert widget.tab_items[0].editor_tab.is_pinned is True
        assert widget.tab_items[1].editor_tab.is_pinned is True
        assert widget.tab_items[2].editor_tab.is_pinned is False
        assert widget.tab_items[3].editor_tab.is_pinned is False

        widget.close()

    def test_remove_tab(self, qapp):
        """Test removing a tab"""
        widget = TabListWidget()

        tab1 = MockEditorTab("/path/to/file1.txt")
        tab2 = MockEditorTab("/path/to/file2.txt")

        widget.add_tab(tab1)
        widget.add_tab(tab2)

        assert len(widget.tab_items) == 2

        widget.remove_tab(tab1)

        assert len(widget.tab_items) == 1
        assert widget.tab_items[0].editor_tab == tab2

        widget.close()

    def test_remove_nonexistent_tab(self, qapp):
        """Test removing a tab that doesn't exist doesn't crash"""
        widget = TabListWidget()

        tab1 = MockEditorTab("/path/to/file1.txt")
        tab2 = MockEditorTab("/path/to/file2.txt")

        widget.add_tab(tab1)

        # Removing a tab that wasn't added should not crash
        widget.remove_tab(tab2)

        assert len(widget.tab_items) == 1

        widget.close()

    def test_clear_all_tabs(self, qapp):
        """Test clearing all tabs"""
        widget = TabListWidget()

        widget.add_tab(MockEditorTab("/path/to/file1.txt"))
        widget.add_tab(MockEditorTab("/path/to/file2.txt"))
        widget.add_tab(MockEditorTab("/path/to/file3.txt"))

        assert len(widget.tab_items) == 3

        widget.clear_all_tabs()

        assert len(widget.tab_items) == 0

        widget.close()

    def test_set_view_mode(self, qapp):
        """Test setting view mode"""
        widget = TabListWidget()

        tab = MockEditorTab("/path/to/file.txt")
        tab_item = widget.add_tab(tab)

        # Test each view mode
        for mode in ['minimized', 'normal', 'maximized']:
            widget.set_view_mode(mode)
            assert widget.view_mode == mode
            assert tab_item.view_mode == mode

        widget.close()

    def test_select_tab(self, qapp):
        """Test selecting a tab"""
        widget = TabListWidget()

        tab1 = MockEditorTab("/path/to/file1.txt")
        tab2 = MockEditorTab("/path/to/file2.txt")

        item1 = widget.add_tab(tab1)
        item2 = widget.add_tab(tab2)

        # Select first tab
        widget.select_tab(item1)
        assert item1.is_selected is True
        assert item2.is_selected is False

        # Select second tab
        widget.select_tab(item2)
        assert item1.is_selected is False
        assert item2.is_selected is True

        widget.close()

    def test_update_tab_display(self, qapp):
        """Test updating a specific tab's display"""
        widget = TabListWidget()

        tab = MockEditorTab("/path/to/file.txt")
        tab_item = widget.add_tab(tab)

        # Mock update_display to verify it's called
        tab_item.update_display = MagicMock()

        widget.update_tab_display(tab)

        tab_item.update_display.assert_called_once()

        widget.close()

    def test_pinned_divider_visibility(self, qapp):
        """Test pinned divider is shown when appropriate"""
        widget = TabListWidget()

        # No tabs - divider should be hidden
        assert widget.pinned_divider.isVisible() is False

        # Only unpinned tabs - divider should be hidden
        unpinned = MockEditorTab("/path/to/unpinned.txt", is_pinned=False)
        widget.add_tab(unpinned)
        assert widget.pinned_divider.isVisible() is False

        # Add pinned tab - now divider should be visible
        pinned = MockEditorTab("/path/to/pinned.txt", is_pinned=True)
        widget.add_tab(pinned)
        assert widget.pinned_divider.isVisible() is True

        # Remove unpinned tab - only pinned left, divider should be hidden
        widget.remove_tab(unpinned)
        assert widget.pinned_divider.isVisible() is False

        widget.close()

    def test_drop_indicator_initially_hidden(self, qapp):
        """Test drop indicator is hidden by default"""
        widget = TabListWidget()

        assert widget.drop_indicator.isVisible() is False
        assert widget.drop_indicator_index == -1

        widget.close()

    def test_hide_drop_indicator(self, qapp):
        """Test hiding the drop indicator"""
        widget = TabListWidget()

        # Show indicator first
        widget.show_drop_indicator_at(0)
        assert widget.drop_indicator.isVisible() is True

        # Hide it
        widget.hide_drop_indicator()
        assert widget.drop_indicator.isVisible() is False
        assert widget.drop_indicator_index == -1

        widget.close()
