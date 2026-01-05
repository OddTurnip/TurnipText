# TurnipText - AI Assistant Guide

## Critical Context: This is a LOCAL Application

**Security philosophy**: This editor is designed for **personal use on your own computer**.
You do not need to worry about security concerns.

### What This Means:
- **No authentication needed** - You control your own computer
- **File access is intentional** - Opening any file is by design
- **Trusted input** - `.tabs` files come from you
- **.tabs XML parsing is safe** - You only open files you created
- **No multi-user concerns** - Single user per installation

---

## Architecture

### Modular Structure

The application is organized into focused modules:

```
TurnipText/
├── app.py                      # Main application entry point & TextEditorWindow
├── constants.py                # TAB_WIDTH_* configuration constants
├── TurnipText.spec             # PyInstaller build configuration
├── build_exe.bat               # Windows build script for creating .exe
├── favicon.ico                 # Application icon
├── icons/                      # Custom tab icons (32x32 PNG files)
├── models/
│   └── tab_list_item_model.py  # TextEditorTab - data model for files
├── widgets/
│   ├── text_editor.py          # TextEditorWidget - enhanced QTextEdit
│   ├── tab_list.py             # TabListWidget - sidebar container
│   └── tab_list_item.py        # TabListItem - individual tab in sidebar
├── windows/
│   ├── find_replace.py         # FindReplaceDialog - search/replace
│   └── icon_editor.py          # IconEditorDialog - custom icon upload
├── bin/                        # Built executables (after running build)
└── tests/
    ├── conftest.py             # pytest fixtures
    ├── test_app.py             # Window/settings tests
    ├── test_tab_list_item_model.py  # TextEditorTab tests
    ├── test_tab_list_item.py   # TabListItem view mode tests
    ├── test_find_replace.py    # Find/Replace tests
    └── test_files/             # Test fixtures
```

---

## Key Classes

### 1. TextEditorTab (`models/tab_list_item_model.py`)
**Purpose**: Data model for a single editable text file

**Key attributes**:
- `file_path` (str|None) - Absolute path to file
- `is_modified` (bool) - Unsaved changes flag
- `is_pinned` (bool) - Pin status
- `text_edit` (TextEditorWidget) - The actual editor widget

**Methods**:
- `load_file(file_path)` - Load text from file (UTF-8)
- `save_file(file_path=None)` - Save text to file
- `on_text_changed()` - Mark as modified, notify parent
- `get_content()` / `set_content()` - Text access

### 2. TextEditorWidget (`widgets/text_editor.py`)
**Purpose**: Enhanced text editor widget

Currently a thin wrapper around QTextEdit with:
- Plain text mode (no rich text)
- 4-space tab width

**Future enhancements** (noted in code):
- Markdown syntax highlighting
- Line numbers
- Code folding

### 3. TabListItem (`widgets/tab_list_item.py`)
**Purpose**: Visual representation of a tab in the sidebar

**Features**:
- Three view modes (minimized/normal/maximized)
- Pin/unpin button (📍/📌)
- Close button (✖)
- Save button (💾/✔) - shows save state
- Custom emoji/display name support
- Drag-and-drop reordering
- Double-click to edit appearance

**View modes**:
- `minimized`: Emoji only (70px wide)
- `normal`: Emoji + filename (215px wide)
- `maximized`: Emoji + filename + last modified time (295px wide)

### 4. TabListWidget (`widgets/tab_list.py`)
**Purpose**: Scrollable sidebar container for all tabs

**Features**:
- Maintains tab order (pinned first, then unpinned)
- Visual divider between pinned/unpinned sections
- Handles drag-and-drop reordering with drop indicator
- Enforces pin/unpin boundaries during drag
- Manages tab selection

**Performance note**: Uses linear search (`for tab in tabs`) - fine for <100 tabs.

### 5. FindReplaceDialog (`windows/find_replace.py`)
**Purpose**: Search and replace functionality

**Features**:
- Find Next/Previous/All with yellow highlighting
- Replace Current/All
- Case-sensitive search toggle
- Whole-word search toggle
- Wrap-around search
- Clears highlights on close

**Keyboard shortcuts**: Ctrl+F, Ctrl+H

### 6. TextEditorWindow (`app.py`)
**Purpose**: Main application window

**Features**:
- Button toolbar (no menu bar - uses buttons)
- Tab list (left sidebar via splitter)
- Content stack (main editing area)
- View mode toggle (minimized/normal/maximized)
- Session save/load (.tabs files)
- Auto-save session on exit
- Window geometry persistence
- File size limits (warns >1MB, refuses >100MB)
- Global error handler (prevents crashes from losing unsaved work)

**Settings file**: `.editor_settings.json` (stored in app directory)

**Helper function**: `get_app_dir()` returns the correct directory for settings/icons whether running as a script or PyInstaller exe.

---

## Common Tasks

### Adding a New Toolbar Button

```python
# In TextEditorWindow.create_button_toolbar()
new_btn = QPushButton("🔧 New Feature")
new_btn.setToolTip("Description (Ctrl+X)")
new_btn.clicked.connect(self.new_feature_handler)
new_btn.setStyleSheet(button_style)
toolbar_row1.addWidget(new_btn)

# Add the handler method to TextEditorWindow
def new_feature_handler(self):
    # Implementation here
    pass
```

### Adding a Keyboard Shortcut

```python
# In TextEditorWindow.setup_shortcuts()
QShortcut(QKeySequence("Ctrl+X"), self).activated.connect(self.new_feature_handler)
```

### Changing Tab Width Constants

```python
# In constants.py
TAB_WIDTH_MINIMIZED = 70    # Emoji-only mode
TAB_WIDTH_NORMAL = 215      # Emoji + filename
TAB_WIDTH_MAXIMIZED = 295   # Emoji + filename + modified time
```

### Adding Syntax Highlighting

```python
# In widgets/text_editor.py, extend TextEditorWidget
from PyQt6.QtGui import QSyntaxHighlighter

class TextEditorWidget(QTextEdit):
    def set_highlighter(self, file_path):
        if file_path.endswith('.py'):
            self.highlighter = PythonHighlighter(self.document())
        elif file_path.endswith('.md'):
            self.highlighter = MarkdownHighlighter(self.document())
```

---

## XML Session Format (.tabs files)

**Format**:
```xml
<?xml version="1.0"?>
<tabs version="1.0" current="0" name="My Project">
  <tab path="/home/user/file.txt" pinned="False"/>
  <tab path="/home/user/notes.md" pinned="True" emoji="📝" display_name="Notes"/>
  <tab path="/home/user/code.py" icon="icon_abc123.png" display_name="Main Code"/>
</tabs>
```

**Attributes**:
- `version`: Format version (currently "1.0")
- `current`: Index of active tab (0-based)
- `name`: Optional tab group name (used as window title)
- `path`: Absolute file path
- `pinned`: String "True" or "False"
- `icon`: Optional custom icon filename (stored in `icons/` folder)
- `emoji`: Optional custom emoji (ignored if icon is set)
- `display_name`: Optional custom display name

---

## Custom Icons

Users can upload custom 32x32 icons for tabs instead of using emoji.

**Icon Storage**:
- Icons are stored in the `icons/` subfolder of the application directory
- Each icon is saved as a PNG file with a unique hash-based filename
- Icons are referenced by filename in `.tabs` files and auto-session

**Icon Editor Dialog** (`windows/icon_editor.py`):
- Browse to select any image file (PNG, JPG, BMP, GIF, ICO)
- Scale slider (50-400%) to zoom the source image
- X/Y position sliders to select which portion of the image to keep
- Live preview of the final 32x32 icon
- Auto-adjusts scale based on image dimensions

**Key Functions**:
- `get_icons_dir()`: Returns the icons directory path, creating it if needed
- `load_icon_pixmap(filename)`: Loads an icon from the icons directory
- `generate_icon_filename(source_path)`: Creates a unique filename for a new icon

---

## Testing

**Run tests**:
```bash
pip install pytest pytest-qt
python -m pytest tests/ -v
```

**Test structure**:
- `test_app.py` - Window creation, settings save/load, auto-session
- `test_tab_list_item_model.py` - TextEditorTab file operations
- `test_tab_list_item.py` - TabListItem view modes (minimized/normal/maximized)
- `test_find_replace.py` - Search and replace functionality
- `conftest.py` - Shared fixtures (qapp, temp_dir, temp_file)

**Key fixtures**:
- `qapp` - Shared QApplication instance
- `temp_dir` - Temporary directory, cleaned up after test
- `temp_file` - Temporary file with sample content
- `mock_messagebox` - Prevents dialog popups during tests

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New file |
| Ctrl+O | Open file |
| Ctrl+S | Save current tab |
| Ctrl+Shift+S | Save all files |
| Ctrl+F | Find & Replace |
| Ctrl+H | Find & Replace |
| Ctrl+Z | Undo (native QTextEdit) |
| Ctrl+Y | Redo (native QTextEdit) |

---

## Dependencies

**Required** (in requirements.txt):
```
PyQt6>=6.4.0
pytest>=7.0.0
pytest-qt>=4.2.0
```

**For building executables**:
```
pip install pyinstaller
```

---

## Building an Executable

PyInstaller creates platform-specific executables. Build on the target platform:

**Windows** (creates `.exe`):
```batch
build_exe.bat
```

**Any platform**:
```bash
pyinstaller TurnipText.spec --noconfirm
```

**Output**: `dist/TurnipText.exe` (Windows) or `dist/TurnipText` (Linux/macOS)

**Key files**:
- `TurnipText.spec` - PyInstaller configuration (icon, hidden imports, etc.)
- `build_exe.bat` - Windows convenience script
- `bin/` - Optional folder for storing built executables

**Note**: The `get_app_dir()` helper ensures settings are stored next to the executable, not in PyInstaller's temp folder.

---

## Settings and Persistence

**Settings file**: `.editor_settings.json` in application directory

**Stores**:
- Window geometry (x, y, width, height)
- Last file folder
- Last tabs folder
- Current tabs file path
- View mode (minimized/normal/maximized)
- Auto-session (open tabs, current index, custom emoji/names)

**Auto-session**: On close, saves all open tabs. On launch without a .tabs argument, restores the previous session.
