# TurnipText

A minimal tabbed text editor built with PyQt6, featuring tab management and workspace sessions.

## Features

- **Tabbed Interface**: Open and manage multiple files in tabs
- **File Operations**: New, Load, Save, and Save As functionality
- **Tab Management**:
  - Pin tabs to prevent accidental closure
  - Close individual tabs with unsaved change warnings
  - Visual indicator for unsaved changes
  - Drag-and-drop tab reordering
  - Custom emoji and display names for tabs
- **Workspace Sessions**:
  - Save all open tabs to a `.tabs` file (XML format)
  - Load tab sessions to restore your workspace
  - Automatically generate `.bat` files to launch workspaces (Windows)
- **Find & Replace**: Search and replace with case-sensitive and whole-word options
- **Format Support**: Plain text files (any extension)

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Editor

Run the editor:
```bash
python app.py
```

Or load a saved tab session:
```bash
python app.py workspace.tabs
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save current tab |
| Ctrl+Shift+S | Save all files |
| Ctrl+F | Find & Replace |
| Ctrl+H | Find & Replace |

### Tab Controls

Each tab has:
- **Pin button**: Pin/unpin the tab
- **Close button**: Close the tab
- **Save button**: Appears when file has unsaved changes

### Workspace Sessions

**Save Tabs:**
1. Open all files you want in your workspace
2. Click **Save Tabs** button
3. Choose a location and name (e.g., `myproject.tabs`)
4. This creates:
   - `myproject.tabs`: XML file with tab configuration
   - `myproject.bat`: Windows batch file to launch the workspace

**Load Tabs:**
- Click **Load Tabs** and select a `.tabs` file
- Or double-click the generated `.bat` file (Windows)
- All files will open in tabs, with the previously active tab selected

### Tab Session File Format

The `.tabs` files use XML format:
```xml
<?xml version="1.0"?>
<tabs version="1.0" current="0">
  <tab path="/path/to/file1.txt" pinned="False"/>
  <tab path="/path/to/file2.md" pinned="True" emoji="📝" display_name="Notes"/>
</tabs>
```

## Project Structure

```
TurnipText/
├── app.py                  # Main application window
├── constants.py            # Configuration constants
├── models/
│   └── tab_list_item_model.py   # TextEditorTab data model
├── widgets/
│   ├── tab_list.py              # Tab sidebar container
│   ├── tab_list_item.py         # Individual tab widget
│   └── text_editor.py           # Text editor widget
├── windows/
│   └── find_replace.py          # Find & Replace dialog
└── tests/                       # Test suite
```

## Running Tests

```bash
pip install pytest pytest-qt
python -m pytest tests/ -v
```

## Notes

- Files use full absolute paths in `.tabs` files
- Pinned tabs require confirmation before closing
- Unsaved changes are checked when closing tabs or the application
- Plain text only (no rich text formatting)
- Auto-saves session on exit, restores on next launch
