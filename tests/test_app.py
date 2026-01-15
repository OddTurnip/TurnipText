"""
Tests for TextEditorWindow (app.py).
Tests settings save/load, session management, and window state.
"""

import pytest
import os
import json
import tempfile
from pathlib import Path

from app import TextEditorWindow
from models.tab_list_item_model import TextEditorTab


@pytest.fixture
def temp_settings_file(temp_dir):
    """Create a temporary settings file path"""
    return os.path.join(temp_dir, '.editor_settings.json')


@pytest.fixture
def editor_window(qapp, temp_settings_file, monkeypatch):
    """Create a TextEditorWindow for testing"""
    window = TextEditorWindow()
    # Update the settings manager to use temp file
    window.settings_manager.settings_file = temp_settings_file
    yield window
    window.close()


class TestWindowCreation:
    """Test window initialization"""

    def test_window_creation(self, qapp, temp_settings_file):
        """Test creating a basic window"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        assert window is not None
        # Window title is either "TurnipText" or derived from a loaded .tabs file
        assert isinstance(window.windowTitle(), str)
        assert len(window.windowTitle()) > 0
        assert window.content_stack is not None
        assert window.tab_list is not None

        window.close()

    def test_window_has_required_components(self, qapp, temp_settings_file):
        """Test that window has all required components"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        assert hasattr(window, 'content_stack')
        assert hasattr(window, 'tab_list')
        assert hasattr(window, 'splitter')
        assert hasattr(window, 'tab_group_manager')  # current_tabs_file is now in tab_group_manager
        assert hasattr(window, 'last_file_folder')
        assert hasattr(window, 'last_tabs_folder')

        window.close()


class TestSettingsSaveLoad:
    """Test settings persistence"""

    def test_save_settings_creates_file(self, qapp, temp_settings_file):
        """Test that saving settings creates a file"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Delete file if it exists
        if os.path.exists(temp_settings_file):
            os.remove(temp_settings_file)

        window.save_settings()

        # File should now exist
        assert os.path.exists(temp_settings_file)

        window.close()

    def test_save_settings_structure(self, qapp, temp_settings_file):
        """Test that saved settings have correct structure"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        window.save_settings()

        # Read and verify structure
        with open(temp_settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        assert 'geometry' in settings
        assert 'last_file_folder' in settings
        assert 'last_tabs_folder' in settings
        assert 'current_tabs_file' in settings
        assert 'view_mode' in settings
        assert 'auto_session' in settings

        # Geometry should have x, y, width, height
        assert 'x' in settings['geometry']
        assert 'y' in settings['geometry']
        assert 'width' in settings['geometry']
        assert 'height' in settings['geometry']

        # Auto session should have tabs and current_index
        assert 'tabs' in settings['auto_session']
        assert 'current_index' in settings['auto_session']

        window.close()

    def test_load_nonexistent_settings(self, qapp, temp_settings_file):
        """Test loading when settings file doesn't exist"""
        # Ensure file doesn't exist
        if os.path.exists(temp_settings_file):
            os.remove(temp_settings_file)

        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Should not crash
        window.load_settings()

        assert window is not None

        window.close()

    def test_settings_roundtrip(self, qapp, temp_settings_file):
        """Test saving and loading settings"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Set some values
        window.last_file_folder = "/test/path"
        window.last_tabs_folder = "/tabs/path"
        window.tab_list.view_mode = "maximized"

        # Save
        window.save_settings()

        # Create new window and load
        window2 = TextEditorWindow()
        window2.settings_manager.settings_file = temp_settings_file
        window2.load_settings()

        # Verify values were restored
        assert window2.last_file_folder == "/test/path"
        assert window2.last_tabs_folder == "/tabs/path"
        assert window2.tab_list.view_mode == "maximized"

        window.close()
        window2.close()


class TestAutoSession:
    """Test automatic session save/load"""

    def test_auto_session_saves_tabs(self, qapp, temp_settings_file, temp_file):
        """Test that auto-session saves open tabs"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Clear any auto-loaded tabs first
        while window.content_stack.count() > 0:
            widget = window.content_stack.widget(0)
            window.content_stack.removeWidget(widget)
            widget.deleteLater()
        window.tab_list.tab_items.clear()

        # Open a tab
        tab = TextEditorTab(temp_file)
        window.content_stack.addWidget(tab)
        window.tab_list.add_tab(tab)

        # Save settings
        window.save_settings()

        # Read settings
        with open(temp_settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # Should have one tab in auto_session
        assert len(settings['auto_session']['tabs']) == 1
        assert settings['auto_session']['tabs'][0]['path'] == temp_file
        assert settings['auto_session']['tabs'][0]['pinned'] is False

        window.close()

    def test_auto_session_saves_pinned_state(self, qapp, temp_settings_file, temp_file):
        """Test that auto-session saves pinned state"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Clear any auto-loaded tabs first
        while window.content_stack.count() > 0:
            widget = window.content_stack.widget(0)
            window.content_stack.removeWidget(widget)
            widget.deleteLater()
        window.tab_list.tab_items.clear()

        # Open a pinned tab
        tab = TextEditorTab(temp_file)
        tab.is_pinned = True
        window.content_stack.addWidget(tab)
        window.tab_list.add_tab(tab)

        # Save settings
        window.save_settings()

        # Read settings
        with open(temp_settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # Should have pinned flag
        assert settings['auto_session']['tabs'][0]['pinned'] is True

        window.close()

    def test_auto_session_empty_when_no_tabs(self, qapp, temp_settings_file):
        """Test auto-session with no tabs open"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Clear any auto-loaded tabs first
        while window.content_stack.count() > 0:
            widget = window.content_stack.widget(0)
            window.content_stack.removeWidget(widget)
            widget.deleteLater()
        window.tab_list.tab_items.clear()

        # Save with no tabs
        window.save_settings()

        # Read settings
        with open(temp_settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # Should have empty tabs list
        assert settings['auto_session']['tabs'] == []

        window.close()


class TestViewMode:
    """Test view mode persistence"""

    def test_view_mode_saves(self, qapp, temp_settings_file):
        """Test that view mode is saved"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Set view mode
        window.tab_list.view_mode = "minimized"

        # Save
        window.save_settings()

        # Read settings
        with open(temp_settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        assert settings['view_mode'] == "minimized"

        window.close()

    def test_view_mode_loads(self, qapp, temp_settings_file):
        """Test that view mode is loaded"""
        # Create settings with specific view mode
        settings = {
            'geometry': {'x': 100, 'y': 100, 'width': 800, 'height': 600},
            'last_file_folder': None,
            'last_tabs_folder': None,
            'current_tabs_file': None,
            'view_mode': 'maximized',
            'auto_session': {'tabs': [], 'current_index': 0}
        }

        with open(temp_settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f)

        # Create window and load
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file
        window.load_settings()

        assert window.tab_list.view_mode == 'maximized'

        window.close()


class TestGeometryPersistence:
    """Test window geometry save/load"""

    def test_geometry_saves(self, qapp, temp_settings_file):
        """Test that window geometry is saved"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        # Set geometry
        window.setGeometry(100, 200, 800, 600)

        # Save
        window.save_settings()

        # Read settings
        with open(temp_settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        geo = settings['geometry']
        assert geo['x'] == window.x()
        assert geo['y'] == window.y()
        assert geo['width'] == window.width()
        assert geo['height'] == window.height()

        window.close()


class TestCurrentTabFolder:
    """Test folder path persistence"""

    def test_last_file_folder_persists(self, qapp, temp_settings_file):
        """Test that last file folder is saved and loaded"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        test_path = "/home/user/documents"
        window.last_file_folder = test_path

        window.save_settings()

        # Create new window
        window2 = TextEditorWindow()
        window2.settings_manager.settings_file = temp_settings_file
        window2.load_settings()

        assert window2.last_file_folder == test_path

        window.close()
        window2.close()

    def test_last_tabs_folder_persists(self, qapp, temp_settings_file):
        """Test that last tabs folder is saved and loaded"""
        window = TextEditorWindow()
        window.settings_manager.settings_file = temp_settings_file

        test_path = "/home/user/tab_sessions"
        window.last_tabs_folder = test_path

        window.save_settings()

        # Create new window
        window2 = TextEditorWindow()
        window2.settings_manager.settings_file = temp_settings_file
        window2.load_settings()

        assert window2.last_tabs_folder == test_path

        window.close()
        window2.close()
