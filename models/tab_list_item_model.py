"""
Data model for a single text editor tab.
Handles file I/O and content management.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QStackedLayout
from widgets.text_editor import TextEditorWidget
from widgets.drive_error_overlay import DriveErrorOverlay


class TextEditorTab(QWidget):
    """Widget representing a single text editor tab"""

    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_modified = False
        self.is_pinned = False
        self._saved_content = ""  # Baseline content for change detection
        self._drive_error_overlay = None  # Overlay for network drive errors
        self._drive_error_shown = False  # Track overlay visibility state

        # Use stacked layout so overlay can be shown on top of editor
        self._stacked_layout = QStackedLayout()
        self._stacked_layout.setContentsMargins(0, 0, 0, 0)
        self._stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # Create editor container
        editor_container = QWidget()
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # Create text edit widget
        self.text_edit = TextEditorWidget()
        self.text_edit.textChanged.connect(self.on_text_changed)

        editor_layout.addWidget(self.text_edit)
        editor_container.setLayout(editor_layout)

        self._stacked_layout.addWidget(editor_container)
        self.setLayout(self._stacked_layout)

        # Load file if provided
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        """Load content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._saved_content = content  # Set baseline before loading
            self.text_edit.setPlainText(content)
            self.file_path = file_path
            self.is_modified = False
            return True
        except (IOError, OSError, UnicodeDecodeError, PermissionError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")
            return False

    def save_file(self, file_path=None):
        """Save content to file"""
        if file_path:
            self.file_path = file_path

        if not self.file_path:
            return False

        try:
            content = self.text_edit.toPlainText()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self._saved_content = content  # Update baseline after saving
            self.is_modified = False
            return True
        except (IOError, OSError, UnicodeEncodeError, PermissionError) as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")
            return False

    def on_text_changed(self):
        """Mark tab as modified when text actually changes.

        Compares current content against saved baseline to determine
        if there are real changes. This prevents false positives from
        syntax highlighting or other formatting operations that trigger
        textChanged without modifying actual text content.
        """
        current_content = self.text_edit.toPlainText()
        should_be_modified = current_content != self._saved_content

        if self.is_modified != should_be_modified:
            self.is_modified = should_be_modified
            # Notify parent window to update tab title
            # Avoids circular import by checking type name as string
            parent_widget = self.parent()
            while parent_widget:
                if parent_widget.__class__.__name__ == 'TextEditorWindow':
                    parent_widget.update_tab_title(self)
                    break
                parent_widget = parent_widget.parent()

    def show_drive_error(self, drive_display_name, retry_callback):
        """Show an overlay indicating the file's network drive is unavailable."""
        if self._drive_error_overlay is None:
            self._drive_error_overlay = DriveErrorOverlay(drive_display_name)
            self._stacked_layout.addWidget(self._drive_error_overlay)
        else:
            self._drive_error_overlay.update_drive_name(drive_display_name)
        self._drive_error_overlay.set_retry_callback(retry_callback)
        self._drive_error_overlay.show()
        self._drive_error_overlay.raise_()
        self._drive_error_shown = True
        self.text_edit.setReadOnly(True)

    def hide_drive_error(self):
        """Hide the drive error overlay and restore editing."""
        if self._drive_error_overlay is not None:
            self._drive_error_overlay.hide()
        self._drive_error_shown = False
        self.text_edit.setReadOnly(False)

    @property
    def has_drive_error(self):
        """Whether the drive error overlay is currently shown."""
        return self._drive_error_shown

    def get_content(self):
        """Get current text content"""
        return self.text_edit.toPlainText()

    def set_content(self, content):
        """Set text content"""
        self._saved_content = content  # Set baseline before setting content
        self.text_edit.setPlainText(content)
        self.is_modified = False
