"""
Tests for the TabGroupManager class in managers/tab_groups.py
"""

import pytest
import os
import tempfile
import shutil

from managers.tab_groups import TabGroupManager, get_tabs_data_from_widgets


class TestTabGroupManager:
    """Tests for TabGroupManager"""

    @pytest.fixture
    def manager(self):
        """Create a fresh TabGroupManager for each test"""
        return TabGroupManager()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_initialization(self, manager):
        """Test manager initializes with correct defaults"""
        assert manager.current_tabs_file is None
        assert manager.tab_group_name is None
        assert manager.recent_groups == []
        assert manager._baseline_tab_state is None

    def test_save_tabs_to_file_creates_xml(self, manager, temp_dir):
        """Test saving tabs creates a valid XML file"""
        tabs_file = os.path.join(temp_dir, 'test.tabs')
        tabs_data = [
            {'path': '/path/to/file1.txt', 'pinned': False},
            {'path': '/path/to/file2.md', 'pinned': True, 'emoji': '📝'},
        ]

        result = manager.save_tabs_to_file(tabs_file, tabs_data, current_index=1)

        assert result is True
        assert os.path.exists(tabs_file)
        assert manager.current_tabs_file == tabs_file

    def test_save_tabs_with_custom_attributes(self, manager, temp_dir):
        """Test saving tabs with custom icon, emoji, and display name"""
        tabs_file = os.path.join(temp_dir, 'custom.tabs')
        tabs_data = [
            {
                'path': '/path/to/file.txt',
                'pinned': True,
                'icon': 'custom_icon.png',
                'emoji': '🎉',
                'display_name': 'My File'
            }
        ]

        result = manager.save_tabs_to_file(tabs_file, tabs_data)

        assert result is True

        # Verify by loading
        loaded_data, current_index, group_name = manager.load_tabs_from_file(tabs_file)
        assert loaded_data[0]['icon'] == 'custom_icon.png'
        assert loaded_data[0]['emoji'] == '🎉'
        assert loaded_data[0]['display_name'] == 'My File'

    def test_save_tabs_with_group_name(self, manager, temp_dir):
        """Test saving tabs with a group name"""
        tabs_file = os.path.join(temp_dir, 'named.tabs')
        manager.tab_group_name = "My Project"
        tabs_data = [{'path': '/path/to/file.txt', 'pinned': False}]

        manager.save_tabs_to_file(tabs_file, tabs_data)

        # Verify group name is saved
        loaded_data, current_index, group_name = manager.load_tabs_from_file(tabs_file)
        assert group_name == "My Project"

    def test_save_tabs_skips_empty_paths(self, manager, temp_dir):
        """Test that tabs without paths are skipped"""
        tabs_file = os.path.join(temp_dir, 'test.tabs')
        tabs_data = [
            {'path': '/path/to/file.txt', 'pinned': False},
            {'path': None, 'pinned': False},  # Should be skipped
            {'path': '', 'pinned': False},     # Should be skipped
        ]

        manager.save_tabs_to_file(tabs_file, tabs_data)

        loaded_data, _, _ = manager.load_tabs_from_file(tabs_file)
        assert len(loaded_data) == 1

    def test_load_tabs_from_file(self, manager, temp_dir):
        """Test loading tabs from a file"""
        # First save some tabs
        tabs_file = os.path.join(temp_dir, 'test.tabs')
        tabs_data = [
            {'path': '/path/to/file1.txt', 'pinned': False},
            {'path': '/path/to/file2.md', 'pinned': True},
        ]
        manager.save_tabs_to_file(tabs_file, tabs_data, current_index=1)

        # Create new manager and load
        new_manager = TabGroupManager()
        loaded_data, current_index, group_name = new_manager.load_tabs_from_file(tabs_file)

        assert len(loaded_data) == 2
        assert loaded_data[0]['path'] == '/path/to/file1.txt'
        assert loaded_data[0]['pinned'] is False
        assert loaded_data[1]['path'] == '/path/to/file2.md'
        assert loaded_data[1]['pinned'] is True
        assert current_index == 1

    def test_load_nonexistent_file(self, manager, temp_dir):
        """Test loading from nonexistent file returns None"""
        fake_path = os.path.join(temp_dir, 'nonexistent.tabs')

        tabs_data, current_index, group_name = manager.load_tabs_from_file(fake_path)

        assert tabs_data is None
        assert current_index == 0
        assert group_name is None

    def test_add_to_recent_groups(self, manager, temp_dir):
        """Test adding to recent groups"""
        path1 = os.path.join(temp_dir, 'group1.tabs')
        path2 = os.path.join(temp_dir, 'group2.tabs')

        manager.add_to_recent_groups(path1)
        manager.add_to_recent_groups(path2)

        assert len(manager.recent_groups) == 2
        assert manager.recent_groups[0] == os.path.abspath(path2)  # Most recent first
        assert manager.recent_groups[1] == os.path.abspath(path1)

    def test_add_duplicate_moves_to_top(self, manager, temp_dir):
        """Test adding existing path moves it to top"""
        path1 = os.path.join(temp_dir, 'group1.tabs')
        path2 = os.path.join(temp_dir, 'group2.tabs')

        manager.add_to_recent_groups(path1)
        manager.add_to_recent_groups(path2)
        manager.add_to_recent_groups(path1)  # Add again

        assert len(manager.recent_groups) == 2
        assert manager.recent_groups[0] == os.path.abspath(path1)  # Now at top

    def test_recent_groups_max_10(self, manager, temp_dir):
        """Test that recent groups is limited to 10"""
        for i in range(15):
            path = os.path.join(temp_dir, f'group{i}.tabs')
            manager.add_to_recent_groups(path)

        assert len(manager.recent_groups) == 10

    def test_get_recent_groups_display(self, manager, temp_dir):
        """Test formatting recent groups for display"""
        path1 = os.path.join(temp_dir, 'MyProject.tabs')
        path2 = os.path.join(temp_dir, 'Another.tabs')

        manager.add_to_recent_groups(path1)
        manager.add_to_recent_groups(path2)

        display = manager.get_recent_groups_display()

        assert len(display) == 2
        # Most recent first
        assert display[0][0] == 'Another'
        assert display[0][1] == os.path.abspath(path2)
        assert display[1][0] == 'MyProject'

    def test_filter_nonexistent_groups(self, manager, temp_dir):
        """Test filtering out non-existent group files"""
        # Create real file
        real_file = os.path.join(temp_dir, 'real.tabs')
        with open(real_file, 'w') as f:
            f.write('dummy')

        fake_file = os.path.join(temp_dir, 'fake.tabs')

        manager.recent_groups = [real_file, fake_file]
        manager.filter_nonexistent_groups()

        assert len(manager.recent_groups) == 1
        assert manager.recent_groups[0] == real_file

    def test_get_window_title_with_group_name(self, manager):
        """Test window title when group name is set"""
        manager.tab_group_name = "My Project"
        manager.current_tabs_file = "/path/to/something.tabs"

        assert manager.get_window_title() == "My Project"

    def test_get_window_title_with_tabs_file(self, manager):
        """Test window title when only tabs file is set"""
        manager.current_tabs_file = "/path/to/MyProject.tabs"

        assert manager.get_window_title() == "MyProject"

    def test_get_window_title_default(self, manager):
        """Test window title when nothing is set"""
        assert manager.get_window_title() == "TurnipText"

    def test_set_baseline_state(self, manager):
        """Test setting baseline state"""
        state = {'tabs': [{'path': '/file.txt'}], 'tab_group_name': 'Test'}

        manager.set_baseline_state(state)

        assert manager._baseline_tab_state == state

    def test_has_state_changed_no_baseline(self, manager):
        """Test state change check with no baseline"""
        current_state = {'tabs': []}

        assert manager.has_state_changed(current_state) is False

    def test_has_state_changed_same_state(self, manager):
        """Test state change check with same state"""
        state = {'tabs': [{'path': '/file.txt'}]}
        manager.set_baseline_state(state)

        assert manager.has_state_changed(state) is False

    def test_has_state_changed_different_state(self, manager):
        """Test state change check with different state"""
        baseline = {'tabs': [{'path': '/file.txt'}]}
        current = {'tabs': [{'path': '/other.txt'}]}

        manager.set_baseline_state(baseline)

        assert manager.has_state_changed(current) is True

    def test_clear(self, manager, temp_dir):
        """Test clearing manager state"""
        # Set some state
        manager.current_tabs_file = "/path/to/file.tabs"
        manager.tab_group_name = "Test"
        manager.set_baseline_state({'tabs': []})

        manager.clear()

        assert manager.current_tabs_file is None
        assert manager.tab_group_name is None
        assert manager._baseline_tab_state is None

    def test_get_last_saved_timestamp(self, manager):
        """Test timestamp format"""
        timestamp = manager.get_last_saved_timestamp()

        # Should be in HH:MM format
        assert ':' in timestamp
        parts = timestamp.split(':')
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()


class TestGetTabsDataFromWidgets:
    """Tests for get_tabs_data_from_widgets helper function"""

    def test_empty_stack(self):
        """Test with empty content stack"""
        from unittest.mock import MagicMock

        mock_stack = MagicMock()
        mock_stack.count.return_value = 0
        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = []

        class MockClass:
            pass

        result = get_tabs_data_from_widgets(mock_stack, mock_tab_list, MockClass)

        assert result == []

    def test_extracts_tab_data(self):
        """Test extracting data from widgets"""
        from unittest.mock import MagicMock

        # Create mock editor tab
        mock_editor = MagicMock()
        mock_editor.file_path = '/path/to/file.txt'
        mock_editor.is_pinned = True

        # Create mock tab item
        mock_tab_item = MagicMock()
        mock_tab_item.editor_tab = mock_editor
        mock_tab_item.custom_icon = 'icon.png'
        mock_tab_item.custom_emoji = '📄'
        mock_tab_item.custom_display_name = 'My File'

        # Create mock content stack
        mock_stack = MagicMock()
        mock_stack.count.return_value = 1
        mock_stack.widget.return_value = mock_editor

        # Create mock tab list
        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = [mock_tab_item]

        # Use the actual editor class type
        result = get_tabs_data_from_widgets(mock_stack, mock_tab_list, type(mock_editor))

        assert len(result) == 1
        assert result[0]['path'] == '/path/to/file.txt'
        assert result[0]['pinned'] is True
        assert result[0]['icon'] == 'icon.png'
        assert result[0]['emoji'] == '📄'
        assert result[0]['display_name'] == 'My File'

    def test_skips_tabs_without_file_path(self):
        """Test that tabs without file paths are skipped"""
        from unittest.mock import MagicMock

        mock_editor = MagicMock()
        mock_editor.file_path = None  # No file path

        mock_stack = MagicMock()
        mock_stack.count.return_value = 1
        mock_stack.widget.return_value = mock_editor

        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = []

        result = get_tabs_data_from_widgets(mock_stack, mock_tab_list, type(mock_editor))

        assert result == []
