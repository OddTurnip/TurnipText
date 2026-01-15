"""
Settings Manager for TurnipText.
Handles loading/saving application settings and auto-session data.
"""

import os
import json


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, settings_file):
        self.settings_file = settings_file
        self._settings = {}

    def load(self):
        """Load settings from file.

        Returns:
            dict: Settings dictionary, or empty dict if file doesn't exist
        """
        if not os.path.exists(self.settings_file):
            self._settings = {}
            return {}

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self._settings = json.load(f)
            return self._settings
        except Exception as e:
            print(f"Failed to load settings: {e}")
            self._settings = {}
            return {}

    def save(self, settings):
        """Save settings to file.

        Args:
            settings: dict of settings to save
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            self._settings = settings
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def get(self, key, default=None):
        """Get a setting value.

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            The setting value or default
        """
        return self._settings.get(key, default)

    def validate_geometry(self, geometry, screen_geometry):
        """Validate and adjust window geometry to fit screen.

        Args:
            geometry: dict with x, y, width, height
            screen_geometry: QRect of available screen space

        Returns:
            dict with validated x, y, width, height
        """
        if not geometry:
            return None

        # Ensure window is not too large for screen
        width = min(geometry.get('width', 1000), screen_geometry.width())
        height = min(geometry.get('height', 700), screen_geometry.height())

        # Ensure window is within screen bounds with padding for title bar
        # Add 50px minimum from top to ensure title bar is always visible
        min_top_margin = 50
        x = max(
            screen_geometry.x(),
            min(geometry.get('x', 100), screen_geometry.right() - width)
        )
        y = max(
            screen_geometry.y() + min_top_margin,
            min(geometry.get('y', 100), screen_geometry.bottom() - height)
        )

        return {'x': x, 'y': y, 'width': width, 'height': height}

    def build_auto_session(self, tabs_data, current_index, tab_group_name):
        """Build auto-session data structure.

        Args:
            tabs_data: List of tab data dicts with path, pinned, icon, emoji, display_name
            current_index: Index of current tab
            tab_group_name: Name of tab group (may be None)

        Returns:
            dict: Auto-session structure
        """
        return {
            'tabs': tabs_data,
            'current_index': current_index,
            'tab_group_name': tab_group_name
        }

    def get_auto_session(self):
        """Get auto-session data from loaded settings.

        Returns:
            tuple: (tabs_list, current_index, tab_group_name) or ([], 0, None) if not found
        """
        auto_session = self._settings.get('auto_session', {})
        if not auto_session or not auto_session.get('tabs'):
            return [], 0, None

        return (
            auto_session.get('tabs', []),
            auto_session.get('current_index', 0),
            auto_session.get('tab_group_name')
        )


def get_tabs_data_for_session(content_stack, tab_list, tab_class):
    """Extract tabs data for saving to session.

    Args:
        content_stack: QStackedWidget containing tab widgets
        tab_list: TabListWidget containing tab items
        tab_class: Class to check widgets against (e.g., TextEditorTab)

    Returns:
        list: List of tab data dicts
    """
    tabs_data = []

    for i in range(content_stack.count()):
        widget = content_stack.widget(i)
        if isinstance(widget, tab_class) and widget.file_path:
            tab_data = {
                'path': widget.file_path,
                'pinned': widget.is_pinned
            }

            # Find matching tab item for custom attributes
            for tab_item in tab_list.tab_items:
                if tab_item.editor_tab == widget:
                    if tab_item.custom_icon:
                        tab_data['icon'] = tab_item.custom_icon
                    if tab_item.custom_emoji:
                        tab_data['emoji'] = tab_item.custom_emoji
                    if tab_item.custom_display_name:
                        tab_data['display_name'] = tab_item.custom_display_name
                    break

            tabs_data.append(tab_data)

    return tabs_data
