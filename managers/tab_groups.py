"""
Tab group management - handles saving/loading .tabs files and history.
Extracted from app.py to reduce file size and improve testability.
"""

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime


class TabGroupManager:
    """Manages tab group operations: save/load .tabs files, history tracking."""

    def __init__(self):
        self.current_tabs_file = None
        self.tab_group_name = None
        self.recent_groups = []  # List of recently loaded .tabs files (max 10)
        self._baseline_tab_state = None  # Baseline state for comparison

    def save_tabs_to_file(self, tabs_file_path, tabs_data, current_index=0):
        """Save tabs data to an XML file.

        Args:
            tabs_file_path: Path to save the .tabs file
            tabs_data: List of dicts with keys: path, pinned, icon, emoji, display_name
            current_index: Index of the currently selected tab

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            # Create XML structure
            root = ET.Element('tabs')
            root.set('version', '1.0')

            # Save tab group name if set
            if self.tab_group_name:
                root.set('name', self.tab_group_name)

            root.set('current', str(current_index))

            # Save each tab
            for tab_data in tabs_data:
                if not tab_data.get('path'):
                    continue  # Skip tabs without file paths

                tab_elem = ET.SubElement(root, 'tab')
                tab_elem.set('path', tab_data['path'])
                tab_elem.set('pinned', str(tab_data.get('pinned', False)))

                if tab_data.get('icon'):
                    tab_elem.set('icon', tab_data['icon'])
                if tab_data.get('emoji'):
                    tab_elem.set('emoji', tab_data['emoji'])
                if tab_data.get('display_name'):
                    tab_elem.set('display_name', tab_data['display_name'])

            # Write XML to file with pretty formatting
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
            with open(tabs_file_path, 'w', encoding='utf-8') as f:
                f.write(xml_str)

            # Update current tabs file
            self.current_tabs_file = tabs_file_path

            # Add to recent groups history
            self.add_to_recent_groups(tabs_file_path)

            return True
        except Exception as e:
            print(f"Failed to save tabs: {e}")
            return False

    def load_tabs_from_file(self, tabs_file_path):
        """Load tabs data from an XML file.

        Args:
            tabs_file_path: Path to the .tabs file

        Returns:
            Tuple of (tabs_data, current_index, group_name) or (None, 0, None) on error
            tabs_data is a list of dicts with keys: path, pinned, icon, emoji, display_name
        """
        try:
            # Parse XML file
            tree = ET.parse(tabs_file_path)
            root = tree.getroot()

            # Load tab group name if present
            group_name = root.get('name')  # May be None

            # Get current tab index
            current_index = int(root.get('current', '0'))

            tabs_data = []

            # Load each tab
            for tab_elem in root.findall('tab'):
                file_path = tab_elem.get('path')

                tab_data = {
                    'path': file_path,
                    'pinned': tab_elem.get('pinned', 'False') == 'True',
                    'icon': tab_elem.get('icon'),  # May be None
                    'emoji': tab_elem.get('emoji'),  # May be None
                    'display_name': tab_elem.get('display_name'),  # May be None
                    'exists': os.path.exists(file_path) if file_path else False
                }
                tabs_data.append(tab_data)

            # Update state
            self.current_tabs_file = tabs_file_path
            self.tab_group_name = group_name

            # Add to recent groups history
            self.add_to_recent_groups(tabs_file_path)

            return tabs_data, current_index, group_name

        except Exception as e:
            print(f"Failed to load tabs: {e}")
            return None, 0, None

    def add_to_recent_groups(self, tabs_file_path):
        """Add a tabs file to the recent groups history."""
        # Convert to absolute path
        tabs_file_path = os.path.abspath(tabs_file_path)

        # Remove if already in list (to move it to the top)
        if tabs_file_path in self.recent_groups:
            self.recent_groups.remove(tabs_file_path)

        # Add to the beginning
        self.recent_groups.insert(0, tabs_file_path)

        # Keep only the 10 most recent
        self.recent_groups = self.recent_groups[:10]

    def get_recent_groups_display(self):
        """Get recent groups formatted for display.

        Returns:
            List of tuples: (display_name, full_path)
        """
        result = []
        for path in self.recent_groups:
            filename = os.path.basename(path)
            if filename.endswith('.tabs'):
                display_name = filename[:-5]
            else:
                display_name = filename
            result.append((display_name, path))
        return result

    def filter_nonexistent_groups(self):
        """Remove groups that no longer exist from the recent list."""
        self.recent_groups = [p for p in self.recent_groups if os.path.exists(p)]

    def get_window_title(self):
        """Get the appropriate window title based on current state."""
        if self.tab_group_name:
            return self.tab_group_name
        elif self.current_tabs_file:
            filename = os.path.basename(self.current_tabs_file)
            # Remove .tabs extension for display
            if filename.endswith('.tabs'):
                return filename[:-5]
            return filename
        else:
            return "TurnipText"

    def set_baseline_state(self, state):
        """Set the baseline state to compare against."""
        self._baseline_tab_state = state

    def has_state_changed(self, current_state):
        """Check if the current state differs from the baseline."""
        if self._baseline_tab_state is None:
            return False
        return current_state != self._baseline_tab_state

    def clear(self):
        """Clear the current group state (for new group)."""
        self.current_tabs_file = None
        self.tab_group_name = None
        self._baseline_tab_state = None

    def get_last_saved_timestamp(self):
        """Get a formatted timestamp for 'last saved' display."""
        return datetime.now().strftime("%H:%M")


def get_tabs_data_from_widgets(content_stack, tab_list, TextEditorTabClass):
    """Extract tabs data from the editor widgets.

    Args:
        content_stack: QStackedWidget containing TextEditorTab widgets
        tab_list: TabListWidget with tab items
        TextEditorTabClass: The TextEditorTab class for isinstance checks

    Returns:
        List of dicts with tab data
    """
    tabs_data = []

    for i in range(content_stack.count()):
        widget = content_stack.widget(i)
        if isinstance(widget, TextEditorTabClass) and widget.file_path:
            tab_data = {
                'path': widget.file_path,
                'pinned': widget.is_pinned
            }

            # Find matching tab item for icon/emoji/display name
            for tab_item in tab_list.tab_items:
                if tab_item.editor_tab == widget:
                    tab_data['icon'] = tab_item.custom_icon
                    tab_data['emoji'] = tab_item.custom_emoji
                    tab_data['display_name'] = tab_item.custom_display_name
                    break

            tabs_data.append(tab_data)

    return tabs_data
