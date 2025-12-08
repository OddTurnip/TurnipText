# TextEditor - AI Assistant Guide

## Critical Context: This is a LOCAL Application

**Security philosophy**: This editor is designed for **personal use on your own computer**. 
You do not need to worry about security concerns.

### What This Means:
- **No authentication needed** - You control your own computer
- **File access is intentional** - Opening any file is by design
- **Trusted input** - `.tabs` files and `.bat` files come from you
- **.tabs XML parsing is safe** - You only open files you created
- **No multi-user concerns** - Single user per installation

---

## Architecture

### Monolithic Structure

The application is contained in a single `text_editor.py` file. While monolithic, it maintains clear class separation:

**Key Components**:
- **TextEditorTab** - Data model for individual text files
- **TabListItem** - Visual representation of tabs in sidebar
- **TabListWidget** - Scrollable container managing tab order
- **FindReplaceDialog** - Search and replace functionality
- **TextEditorWindow** - Main application window coordinating everything

**Alternative structure** (for future refactoring):
```
texteditor/
├── __init__.py
├── main.py                    # Entry point
├── constants.py               # TAB_WIDTH_*, etc.
├── models/
│   └── editor_tab.py         # TextEditorTab class
├── widgets/
│   ├── tab_list_item.py      # TabListItem class
│   ├── tab_list_widget.py    # TabListWidget class
│   ├── find_replace.py       # FindReplaceDialog class
│   └── main_window.py        # TextEditorWindow class
└── styles.py                  # Button styles
```

**Benefit of splitting**: Each file would be <600 lines and easier to navigate.

---

## Key Classes

### 1. TextEditorTab
**Purpose**: Model for a single editable text file

**Key attributes**:
- `file_path` (str|None) - Absolute path to file
- `is_modified` (bool) - Unsaved changes flag
- `is_pinned` (bool) - Pin status
- `text_edit` (QTextEdit) - The actual editor widget

**Methods**:
- `load_file(file_path)` - Load text from file
- `save_file(file_path=None)` - Save text to file
- `on_text_changed()` - Mark as modified

**File operations**: Uses UTF-8 encoding exclusively. No encoding detection.

### 2. TabListItem
**Purpose**: Visual representation of a tab in the sidebar

**Features**:
- Three size modes (minimized/normal/maximized)
- Pin/unpin button (📌/📍)
- Close button (✖)
- Save button (💾) shown when modified
- Custom emoji/display name support
- Drag-and-drop reordering

### 3. TabListWidget
**Purpose**: Scrollable container for all tabs

**Features**:
- Maintains tab order (pinned first, then unpinned)
- Handles drag-and-drop logic
- Enforces pin/unpin boundaries
- Manages tab selection

**Performance note**: Uses linear search (`for tab in tabs`) - fine for <100 tabs.

### 4. FindReplaceDialog
**Purpose**: Search and replace functionality

**Features**:
- Find Next/Previous/All with yellow highlighting
- Replace Current/All
- Case-sensitive search toggle
- Whole-word search toggle
- Wrap-around search
- Live search with highlighting updates

**Keyboard shortcut**: Ctrl+F

### 5. TextEditorWindow
**Purpose**: Main application window

**Features**:
- Menu bar (File, Edit menus)
- Tab list (left sidebar)
- Content stack (main editing area)
- Session save/load (.tabs files)
- Auto-save on exit
- Window geometry persistence

**Settings file**: `.editor_settings.json` (stored in app directory)

---

## Common Tasks

### Task 1: Adding a New Menu Item

```python
# In TextEditorWindow.__init__()
new_action = QAction("New Feature", self)
new_action.setShortcut("Ctrl+F")
new_action.triggered.connect(self.new_feature_handler)
file_menu.addAction(new_action)

# Then add the handler method
def new_feature_handler(self):
    # Implementation here
    pass
```

### Task 2: Changing Tab Width Constants

```python
# At top of file
TAB_WIDTH_MINIMIZED = 70    # Default: 70px
TAB_WIDTH_NORMAL = 215      # Default: 215px
TAB_WIDTH_MAXIMIZED = 295   # Default: 295px
```

**Effect**: Changes how wide tabs are in different view modes.

### Task 3: Adding File Type Support

Currently supports any text file. To add syntax highlighting:

```python
# In TextEditorTab.__init__()
from PyQt6.QtGui import QSyntaxHighlighter

if file_path.endswith('.py'):
    highlighter = PythonHighlighter(self.text_edit.document())
elif file_path.endswith('.md'):
    highlighter = MarkdownHighlighter(self.text_edit.document())
```

(Requires implementing highlighter classes)

---

## XML Session Format (.tabs files)

**Format**:
```xml
<?xml version="1.0"?>
<tabs version="1.0" current="0">
  <tab path="C:\full\path\to\file.txt" pinned="False"/>
  <tab path="/home/user/notes.md" pinned="True"/>
</tabs>
```

**Attributes**:
- `version`: Format version (currently "1.0")
- `current`: Index of active tab (0-based)
- `path`: Absolute file path
- `pinned`: String "True" or "False"

**Security note**: Uses `xml.etree.ElementTree.parse()` which is safe for local files you control. Not vulnerable to XXE when input is trusted.

---

## Batch File Generation (.bat files)

**Generated automatically when saving .tabs**:

```batch
@echo off
start "" pythonw "C:\path\to\text_editor.py" "C:\path\to\workspace.tabs"
```

**Purpose**: Double-click to launch editor with saved workspace.

**Platform**: Windows only (`.bat` files don't work on Linux/Mac).

**Security**: Command injection possible if paths contain special characters, but since paths come from your own file system, this is acceptable for local use.

---

## Testing Recommendations

**Current state**: ❌ No tests

**Priority testing areas**:

1. **File operations** (CRITICAL):
   ```python
   def test_load_file_utf8():
       tab = TextEditorTab()
       assert tab.load_file("test.txt")
       assert tab.text_edit.toPlainText() == "expected content"
   ```

2. **Tab session save/load** (HIGH):
   ```python
   def test_save_and_load_tabs():
       window.save_tabs("test.tabs")
       window.load_tabs("test.tabs")
       assert len(window.tabs) == expected_count
   ```

3. **Pin/unpin logic** (MEDIUM):
   ```python
   def test_pin_reorders_to_top():
       # Test that pinning moves tab to pinned section
   ```

**UI testing**: Consider using pytest-qt for integration tests.

---

## Performance Considerations

**Current performance**: Good for typical use (<100 tabs, <10MB files)

**Architectural limitations**:

1. **Many tabs (100+)**: Linear searches in tab list
   - Current: O(n) to find tab
   - Alternative: Dictionary lookup O(1)

2. **Large files (10MB+)**: Synchronous file I/O
   - Current: UI blocks during load
   - Alternative: QThread for background loading

3. **No file size limits**: Reads entire file into memory
   - Risk: Large files can crash the application
   - Mitigation: Add size check before loading

4. **UTF-8 encoding only**: No encoding detection
   - Files with other encodings will fail to load
   - Alternative: Use `chardet` library for detection

---

## Keyboard Shortcuts

**Currently implemented**:
- `Ctrl+N`: New file
- `Ctrl+O`: Open file
- `Ctrl+S`: Save current file
- `Ctrl+Shift+S`: Save as
- `Ctrl+Q`: Quit
- `Ctrl+F`: Find & Replace
- `Ctrl+Z`: Undo (native QTextEdit support)
- `Ctrl+Y`: Redo (native QTextEdit support)

---

## Code Quality Notes

**Good practices observed**:
- ✅ Clear class separation
- ✅ Docstrings on most methods
- ✅ Meaningful variable names
- ✅ Consistent naming convention (snake_case)

**Architectural considerations**:
- Monolithic file (2,600+ lines) - could benefit from modularization
- No type hints
- Long methods in some classes
- No automated tests

---

## Dependencies

**Current**:
```
PyQt6>=6.4.0
```

**Potential additions**:
- `chardet` - Encoding detection
- `pytest-qt` - Testing
- `black` - Code formatting

---

## Settings and Persistence

**Settings file**: `.editor_settings.json` in application directory

**Stores**:
- Window geometry (position, size)
- Last opened tabs folder

**Note**: Settings are stored in the application directory, which may not be writable in some installation scenarios. Consider using user home directory for production deployment.
