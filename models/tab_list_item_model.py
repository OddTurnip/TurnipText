"""
Data model for a single text editor tab.
Handles file I/O and content management.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from widgets.text_editor import TextEditorWidget


class TextEditorTab(QWidget):
    """Widget representing a single text editor tab"""

    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.is_modified = False
        self.is_pinned = False

        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Create text edit widget
        self.text_edit = TextEditorWidget()
        self.text_edit.textChanged.connect(self.on_text_changed)

        layout.addWidget(self.text_edit)
        self.setLayout(layout)

        # Load file if provided
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        """Load content from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
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
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            self.is_modified = False
            return True
        except (IOError, OSError, UnicodeEncodeError, PermissionError) as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")
            return False

    def on_text_changed(self):
        """Mark tab as modified when text changes"""
        if not self.is_modified:
            self.is_modified = True
            # Notify parent window to update tab title
            # Avoids circular import by checking type name as string
            parent_widget = self.parent()
            while parent_widget:
                if parent_widget.__class__.__name__ == 'TextEditorWindow':
                    parent_widget.update_tab_title(self)
                    break
                parent_widget = parent_widget.parent()

    def get_content(self):
        """Get current text content"""
        return self.text_edit.toPlainText()

    def set_content(self, content):
        """Set text content"""
        self.text_edit.setPlainText(content)
        self.is_modified = False
