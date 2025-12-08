# TextEditor

A minimal tabbed text editor built with PyQt6, featuring tab management and workspace sessions.

## Features

- **Tabbed Interface**: Open and manage multiple files in tabs
- **File Operations**: New, Load, Save, and Save As functionality
- **Tab Management**:
  - Pin tabs to prevent accidental closure
  - Close individual tabs with unsaved change warnings
  - Visual indicator for unsaved changes (● prefix)
- **Workspace Sessions**:
  - Save all open tabs to a `.tabs` file (XML format)
  - Load tab sessions to restore your workspace
  - Automatically generate `.bat` files to launch workspaces
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
python text_editor.py
```

Or load a saved tab session:
```bash
python text_editor.py workspace.tabs
```

### Menu Options

**File Menu:**
- **📄 New** (Ctrl+N): Create a new empty tab
- **📂 Load** (Ctrl+O): Open a file in a new tab
- **💾 Save** (Ctrl+S): Save the current file
- **💾 Save As** (Ctrl+Shift+S): Save current file with a new name
- **📋 Load Tabs**: Load a saved tab session
- **💾 Save Tabs**: Save current tabs to a session file
- **🚪 Exit** (Ctrl+Q): Exit the application

### Tab Controls

Each tab has:
- **Pin button (📌/📍)**: Pin/unpin the tab
- **Close button (✖)**: Close the tab
- **Unsaved indicator (●)**: Shows when file has unsaved changes

### Workspace Sessions

**Save Tabs:**
1. Open all files you want in your workspace
2. Select **File → Save Tabs**
3. Choose a location and name (e.g., `myproject.tabs`)
4. This creates:
   - `myproject.tabs`: XML file with tab configuration
   - `myproject.bat`: Windows batch file to launch the workspace

**Load Tabs:**
- Use **File → Load Tabs** and select a `.tabs` file
- Or double-click the generated `.bat` file
- All files will open in tabs, with the previously active tab selected

### Tab Session File Format

The `.tabs` files use XML format:
```xml
<?xml version="1.0"?>
<tabs version="1.0" current="0">
  <tab path="C:\full\path\to\file1.txt" pinned="False"/>
  <tab path="C:\full\path\to\file2.md" pinned="True"/>
</tabs>
```

## Quick Start Example

1. Open the editor: `python text_editor.py`
2. Load or create several files
3. Pin important tabs with the 📌 button
4. Save the workspace: **File → Save Tabs** → `myworkspace.tabs`
5. Close the editor
6. Double-click `myworkspace.bat` to restore your workspace instantly!

## Security Considerations

**This is a local desktop application** designed for personal use on your own computer. Security considerations:

- **File Access**: The editor can open/save any file you have permissions for - this is by design, as you control what files you open
- **Tab Session Files**: `.tabs` files are XML format and trusted input from your local filesystem. Only open `.tabs` files you created or trust
- **Batch Files**: Generated `.bat` files execute on your system - only run batch files you created with this editor
- **Intended Use**: Not designed for multi-user environments or handling untrusted input from external sources

## Notes

- Files use full absolute paths in `.tabs` files
- Pinned tabs require confirmation before closing
- Unsaved changes are checked when closing tabs or the application
- Plain text only (no rich text formatting)
