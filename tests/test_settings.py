"""
Tests for the SettingsManager class in managers/settings.py
"""

import pytest
import os
import tempfile
import shutil
import json
from unittest.mock import MagicMock

from managers.settings import SettingsManager, get_tabs_data_for_session


class TestSettingsManager:
    """Tests for SettingsManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def settings_file(self, temp_dir):
        """Create a temporary settings file path"""
        return os.path.join(temp_dir, '.editor_settings.json')

    @pytest.fixture
    def manager(self, settings_file):
        """Create a fresh SettingsManager for each test"""
        return SettingsManager(settings_file)

    def test_initialization(self, manager, settings_file):
        """Test manager initializes correctly"""
        assert manager.settings_file == settings_file
        assert manager._settings == {}

    def test_load_nonexistent_file(self, manager):
        """Test loading from non-existent file returns empty dict"""
        result = manager.load()
        assert result == {}

    def test_save_and_load(self, manager):
        """Test saving and loading settings"""
        test_settings = {
            'view_mode': 'maximized',
            'render_markdown': False,
            'last_file_folder': '/some/path'
        }

        manager.save(test_settings)
        result = manager.load()

        assert result == test_settings

    def test_get_existing_key(self, manager):
        """Test getting an existing key"""
        manager.save({'key1': 'value1', 'key2': 42})
        manager.load()

        assert manager.get('key1') == 'value1'
        assert manager.get('key2') == 42

    def test_get_nonexistent_key_default(self, manager):
        """Test getting non-existent key returns default"""
        manager.save({})
        manager.load()

        assert manager.get('nonexistent') is None
        assert manager.get('nonexistent', 'default') == 'default'

    def test_validate_geometry_none(self, manager):
        """Test validate_geometry with None returns None"""
        result = manager.validate_geometry(None, MagicMock())
        assert result is None

    def test_validate_geometry_basic(self, manager):
        """Test basic geometry validation"""
        geometry = {'x': 100, 'y': 100, 'width': 800, 'height': 600}

        # Create mock screen geometry
        screen = MagicMock()
        screen.x.return_value = 0
        screen.y.return_value = 0
        screen.width.return_value = 1920
        screen.height.return_value = 1080
        screen.right.return_value = 1920
        screen.bottom.return_value = 1080

        result = manager.validate_geometry(geometry, screen)

        assert result['width'] == 800
        assert result['height'] == 600
        assert result['x'] >= 0
        assert result['y'] >= 50  # min_top_margin

    def test_validate_geometry_too_large(self, manager):
        """Test geometry validation clamps to screen size"""
        geometry = {'x': 0, 'y': 0, 'width': 3000, 'height': 2000}

        screen = MagicMock()
        screen.x.return_value = 0
        screen.y.return_value = 0
        screen.width.return_value = 1920
        screen.height.return_value = 1080
        screen.right.return_value = 1920
        screen.bottom.return_value = 1080

        result = manager.validate_geometry(geometry, screen)

        assert result['width'] == 1920
        assert result['height'] == 1080

    def test_validate_geometry_offscreen(self, manager):
        """Test geometry validation brings window on screen"""
        geometry = {'x': -500, 'y': -500, 'width': 800, 'height': 600}

        screen = MagicMock()
        screen.x.return_value = 0
        screen.y.return_value = 0
        screen.width.return_value = 1920
        screen.height.return_value = 1080
        screen.right.return_value = 1920
        screen.bottom.return_value = 1080

        result = manager.validate_geometry(geometry, screen)

        assert result['x'] >= 0
        assert result['y'] >= 50  # min_top_margin

    def test_build_auto_session(self, manager):
        """Test building auto-session data structure"""
        tabs_data = [
            {'path': '/file1.txt', 'pinned': False},
            {'path': '/file2.txt', 'pinned': True}
        ]

        result = manager.build_auto_session(tabs_data, 1, "My Group")

        assert result['tabs'] == tabs_data
        assert result['current_index'] == 1
        assert result['tab_group_name'] == "My Group"

    def test_build_auto_session_no_group_name(self, manager):
        """Test building auto-session without group name"""
        result = manager.build_auto_session([], 0, None)

        assert result['tabs'] == []
        assert result['current_index'] == 0
        assert result['tab_group_name'] is None

    def test_get_auto_session_empty(self, manager):
        """Test getting auto-session when not set"""
        manager.save({})
        manager.load()

        tabs, index, name = manager.get_auto_session()

        assert tabs == []
        assert index == 0
        assert name is None

    def test_get_auto_session_with_data(self, manager):
        """Test getting auto-session with data"""
        tabs_data = [
            {'path': '/file1.txt', 'pinned': False},
            {'path': '/file2.txt', 'pinned': True, 'emoji': '📝'}
        ]

        manager.save({
            'auto_session': {
                'tabs': tabs_data,
                'current_index': 1,
                'tab_group_name': 'Test Group'
            }
        })
        manager.load()

        tabs, index, name = manager.get_auto_session()

        assert tabs == tabs_data
        assert index == 1
        assert name == 'Test Group'

    def test_get_auto_session_empty_tabs(self, manager):
        """Test getting auto-session with empty tabs list"""
        manager.save({
            'auto_session': {
                'tabs': [],
                'current_index': 0
            }
        })
        manager.load()

        tabs, index, name = manager.get_auto_session()

        assert tabs == []
        assert index == 0
        assert name is None

    def test_save_handles_error(self, temp_dir, capsys):
        """Test save handles write error gracefully"""
        # Create manager with invalid path
        invalid_path = os.path.join(temp_dir, 'nonexistent_dir', 'settings.json')
        manager = SettingsManager(invalid_path)

        # Should not raise, just print error
        manager.save({'key': 'value'})

        captured = capsys.readouterr()
        assert 'Failed to save settings' in captured.out

    def test_load_handles_invalid_json(self, settings_file, capsys):
        """Test load handles invalid JSON gracefully"""
        # Write invalid JSON
        with open(settings_file, 'w') as f:
            f.write('{ invalid json }')

        manager = SettingsManager(settings_file)
        result = manager.load()

        assert result == {}
        captured = capsys.readouterr()
        assert 'Failed to load settings' in captured.out


class TestGetTabsDataForSession:
    """Tests for get_tabs_data_for_session helper function"""

    def test_empty_stack(self):
        """Test with empty content stack"""
        mock_stack = MagicMock()
        mock_stack.count.return_value = 0
        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = []

        class MockClass:
            pass

        result = get_tabs_data_for_session(mock_stack, mock_tab_list, MockClass)

        assert result == []

    def test_extracts_basic_tab_data(self):
        """Test extracting basic tab data"""
        mock_editor = MagicMock()
        mock_editor.file_path = '/path/to/file.txt'
        mock_editor.is_pinned = True

        mock_tab_item = MagicMock()
        mock_tab_item.editor_tab = mock_editor
        mock_tab_item.custom_icon = None
        mock_tab_item.custom_emoji = None
        mock_tab_item.custom_display_name = None

        mock_stack = MagicMock()
        mock_stack.count.return_value = 1
        mock_stack.widget.return_value = mock_editor

        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = [mock_tab_item]

        result = get_tabs_data_for_session(mock_stack, mock_tab_list, type(mock_editor))

        assert len(result) == 1
        assert result[0]['path'] == '/path/to/file.txt'
        assert result[0]['pinned'] is True
        assert 'icon' not in result[0]
        assert 'emoji' not in result[0]
        assert 'display_name' not in result[0]

    def test_extracts_custom_attributes(self):
        """Test extracting custom icon, emoji, and display name"""
        mock_editor = MagicMock()
        mock_editor.file_path = '/path/to/file.txt'
        mock_editor.is_pinned = False

        mock_tab_item = MagicMock()
        mock_tab_item.editor_tab = mock_editor
        mock_tab_item.custom_icon = 'custom.png'
        mock_tab_item.custom_emoji = '🎉'
        mock_tab_item.custom_display_name = 'My File'

        mock_stack = MagicMock()
        mock_stack.count.return_value = 1
        mock_stack.widget.return_value = mock_editor

        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = [mock_tab_item]

        result = get_tabs_data_for_session(mock_stack, mock_tab_list, type(mock_editor))

        assert result[0]['icon'] == 'custom.png'
        assert result[0]['emoji'] == '🎉'
        assert result[0]['display_name'] == 'My File'

    def test_skips_tabs_without_file_path(self):
        """Test that tabs without file paths are skipped"""
        mock_editor = MagicMock()
        mock_editor.file_path = None

        mock_stack = MagicMock()
        mock_stack.count.return_value = 1
        mock_stack.widget.return_value = mock_editor

        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = []

        result = get_tabs_data_for_session(mock_stack, mock_tab_list, type(mock_editor))

        assert result == []

    def test_multiple_tabs(self):
        """Test extracting data from multiple tabs"""
        mock_editor1 = MagicMock()
        mock_editor1.file_path = '/file1.txt'
        mock_editor1.is_pinned = True

        mock_editor2 = MagicMock()
        mock_editor2.file_path = '/file2.txt'
        mock_editor2.is_pinned = False

        mock_tab_item1 = MagicMock()
        mock_tab_item1.editor_tab = mock_editor1
        mock_tab_item1.custom_icon = None
        mock_tab_item1.custom_emoji = '📄'
        mock_tab_item1.custom_display_name = None

        mock_tab_item2 = MagicMock()
        mock_tab_item2.editor_tab = mock_editor2
        mock_tab_item2.custom_icon = None
        mock_tab_item2.custom_emoji = None
        mock_tab_item2.custom_display_name = 'Second'

        mock_stack = MagicMock()
        mock_stack.count.return_value = 2
        mock_stack.widget.side_effect = [mock_editor1, mock_editor2]

        mock_tab_list = MagicMock()
        mock_tab_list.tab_items = [mock_tab_item1, mock_tab_item2]

        # Need to match the type for isinstance check
        result = get_tabs_data_for_session(mock_stack, mock_tab_list, type(mock_editor1))

        assert len(result) == 2
        assert result[0]['path'] == '/file1.txt'
        assert result[0]['emoji'] == '📄'
        assert result[1]['path'] == '/file2.txt'
        assert result[1]['display_name'] == 'Second'
