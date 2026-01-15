"""
Reusable dialog classes for TurnipText.
Extracted from app.py to reduce file size and improve testability.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt

from styles import DIALOG_BUTTON_STYLE, INPUT_STYLE, CLOSE_DIALOG_BUTTON_STYLE
from windows.icon_editor import IconEditorDialog


class EditTabDialog(QDialog):
    """Dialog for editing tab appearance (emoji, icon, display name, pin status)."""

    def __init__(self, tab_item, parent=None):
        super().__init__(parent)
        self.tab_item = tab_item
        self.pending_icon = tab_item.custom_icon
        self.result_emoji = None
        self.result_icon = None
        self.result_display_name = None
        self.result_pinned = None

        self.setWindowTitle("Edit Tab Appearance")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Emoji input
        emoji_layout = QHBoxLayout()
        emoji_label = QLabel("Emoji:")
        emoji_label.setFixedWidth(100)
        emoji_layout.addWidget(emoji_label)

        self.emoji_input = QLineEdit()
        self.emoji_input.setText(self.tab_item.get_emoji())
        self.emoji_input.setPlaceholderText("e.g., 📄 or P")
        self.emoji_input.setStyleSheet(INPUT_STYLE)
        emoji_layout.addWidget(self.emoji_input)

        # Hint label (shown when icon overrides emoji)
        self.emoji_hint = QLabel("(icon overrides)")
        self.emoji_hint.setStyleSheet("color: #666666; font-style: italic;")
        self.emoji_hint.setVisible(self.tab_item.custom_icon is not None)
        emoji_layout.addWidget(self.emoji_hint)

        layout.addLayout(emoji_layout)

        # Custom icon section
        icon_layout = QHBoxLayout()
        icon_label = QLabel("Icon:")
        icon_label.setFixedWidth(100)
        icon_layout.addWidget(icon_label)

        # Icon status label
        self.icon_status = QLabel()
        if self.tab_item.custom_icon:
            self.icon_status.setText("Custom icon set")
            self.icon_status.setStyleSheet("color: #4CAF50;")
        else:
            self.icon_status.setText("No custom icon")
            self.icon_status.setStyleSheet("color: #666666;")
        icon_layout.addWidget(self.icon_status)

        icon_layout.addStretch()

        # Remove icon button (only shown when icon is set)
        self.remove_icon_btn = QPushButton("Remove")
        self.remove_icon_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        self.remove_icon_btn.setVisible(self.tab_item.custom_icon is not None)
        self.remove_icon_btn.clicked.connect(self._remove_icon)
        icon_layout.addWidget(self.remove_icon_btn)

        # Upload icon button
        upload_icon_btn = QPushButton("Upload...")
        upload_icon_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        upload_icon_btn.clicked.connect(self._open_icon_editor)
        icon_layout.addWidget(upload_icon_btn)

        layout.addLayout(icon_layout)

        # Display name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Display Name:")
        name_label.setFixedWidth(100)
        name_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setText(self.tab_item.custom_display_name or "")

        # Show what the default display name will be
        default_name = "Untitled"
        if self.tab_item.editor_tab.file_path:
            filename = os.path.basename(self.tab_item.editor_tab.file_path)
            name_without_ext = os.path.splitext(filename)[0]
            default_name = name_without_ext.lstrip('_') or filename
        self.name_input.setPlaceholderText(f"Default: {default_name}")
        self.name_input.setStyleSheet(INPUT_STYLE)
        name_layout.addWidget(self.name_input)

        layout.addLayout(name_layout)

        # Pin checkbox
        pin_layout = QHBoxLayout()
        pin_label = QLabel("")
        pin_label.setFixedWidth(100)
        pin_layout.addWidget(pin_label)

        self.pin_checkbox = QCheckBox("📌 Pin this tab")
        self.pin_checkbox.setChecked(self.tab_item.editor_tab.is_pinned)
        pin_layout.addWidget(self.pin_checkbox)
        pin_layout.addStretch()

        layout.addLayout(pin_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _remove_icon(self):
        self.pending_icon = None
        self.icon_status.setText("Icon will be removed")
        self.icon_status.setStyleSheet("color: #FF9800;")
        self.emoji_hint.setVisible(False)
        self.remove_icon_btn.setVisible(False)

    def _open_icon_editor(self):
        icon_dialog = IconEditorDialog(self, self.pending_icon)
        if icon_dialog.exec() == QDialog.DialogCode.Accepted:
            result = icon_dialog.get_icon_filename()
            if result == "":
                # Icon removed
                self._remove_icon()
            elif result:
                # New icon set
                self.pending_icon = result
                self.icon_status.setText("New icon selected")
                self.icon_status.setStyleSheet("color: #4CAF50;")
                self.emoji_hint.setVisible(True)
                self.remove_icon_btn.setVisible(True)

    def _on_accept(self):
        # Store results for retrieval
        self.result_icon = self.pending_icon
        self.result_emoji = self.emoji_input.text().strip() or None
        self.result_display_name = self.name_input.text().strip() or None
        self.result_pinned = self.pin_checkbox.isChecked()
        self.accept()

    def get_results(self):
        """Get the dialog results after acceptance.

        Returns tuple: (icon, emoji, display_name, pinned)
        """
        return (self.result_icon, self.result_emoji,
                self.result_display_name, self.result_pinned)


class EditGroupDialog(QDialog):
    """Dialog for editing tab group name."""

    def __init__(self, current_name, current_tabs_file, parent=None):
        super().__init__(parent)
        self.result_name = None

        self.setWindowTitle("Edit Tab Group")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Tab group name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Tab Group Name:")
        name_label.setFixedWidth(120)
        name_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setText(current_name or "")

        # Show default name based on tabs file
        default_name = "TurnipText"
        if current_tabs_file:
            filename = os.path.basename(current_tabs_file)
            if filename.endswith('.tabs'):
                default_name = filename[:-5]
        self.name_input.setPlaceholderText(f"Default: {default_name}")
        self.name_input.setStyleSheet(INPUT_STYLE)
        name_layout.addWidget(self.name_input)

        layout.addLayout(name_layout)

        # Info label
        info_label = QLabel("This name will be used as the window title and saved in the .tabs file.")
        info_label.setStyleSheet("color: #666666; font-style: italic; margin-top: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        ok_btn.clicked.connect(self._on_accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _on_accept(self):
        self.result_name = self.name_input.text().strip() or None
        self.accept()

    def get_result(self):
        """Get the new group name after acceptance."""
        return self.result_name


class AboutDialog(QDialog):
    """Dialog showing application info and keyboard shortcuts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TurnipText")
        self.setMinimumWidth(450)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("<h2>TurnipText Editor</h2>")
        layout.addWidget(title_label)

        # Keyboard shortcuts section
        shortcuts_label = QLabel("<h3>Keyboard Shortcuts</h3>")
        layout.addWidget(shortcuts_label)

        shortcuts_text = QLabel("""
<table cellpadding="5">
  <tr><td><b>Ctrl+N</b></td><td>New file</td></tr>
  <tr><td><b>Ctrl+O</b></td><td>Open file</td></tr>
  <tr><td><b>Ctrl+S</b></td><td>Save current tab</td></tr>
  <tr><td><b>Ctrl+Shift+S</b></td><td>Save all files</td></tr>
  <tr><td><b>Ctrl+F</b></td><td>Find &amp; Replace</td></tr>
  <tr><td><b>Ctrl+H</b></td><td>Find &amp; Replace</td></tr>
  <tr><td><b>Ctrl+I</b></td><td>Document statistics</td></tr>
  <tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
  <tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
</table>
        """)
        layout.addWidget(shortcuts_text)

        # Fonts section
        fonts_label = QLabel("<h3>Fonts</h3>")
        layout.addWidget(fonts_label)

        fonts_text = QLabel("""
<b>Line numbers:</b> Calibri<br>
<b>Editor:</b> System default (or Consolas with Monospace checkbox)
        """)
        layout.addWidget(fonts_text)

        # About section
        about_label = QLabel("<h3>About</h3>")
        layout.addWidget(about_label)

        about_text = QLabel("""
A free text editor created by <a href="https://oddturnip.com">OddTurnip.com</a>,
using <a href="https://docs.claude.com/en/docs/claude-code">Claude Code</a>.
        """)
        about_text.setOpenExternalLinks(True)
        about_text.setWordWrap(True)
        layout.addWidget(about_text)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(DIALOG_BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)


class UnsavedChangesDialog(QDialog):
    """Dialog for handling unsaved file changes on close."""

    # Result codes
    CANCEL = 0
    EXIT_WITHOUT_SAVING = 1
    SAVE_AND_EXIT = 2

    def __init__(self, modified_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unsaved Changes")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Message
        message = QLabel(
            "The following files have unsaved changes:\n\n" +
            "\n".join(f"  • {name}" for name in modified_files) +
            "\n\nWhat would you like to do?"
        )
        layout.addWidget(message)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        exit_btn = QPushButton("❌ Exit")
        exit_btn.setToolTip("Exit without saving changes")
        exit_btn.setStyleSheet(CLOSE_DIALOG_BUTTON_STYLE)
        exit_btn.clicked.connect(lambda: self.done(self.EXIT_WITHOUT_SAVING))
        button_layout.addWidget(exit_btn)

        cancel_btn = QPushButton("🔙 Cancel")
        cancel_btn.setToolTip("Cancel and return to editing")
        cancel_btn.setStyleSheet(CLOSE_DIALOG_BUTTON_STYLE)
        cancel_btn.clicked.connect(lambda: self.done(self.CANCEL))
        button_layout.addWidget(cancel_btn)

        save_exit_btn = QPushButton("💾 Save and Exit")
        save_exit_btn.setToolTip("Save all changes and exit")
        save_exit_btn.setStyleSheet(CLOSE_DIALOG_BUTTON_STYLE)
        save_exit_btn.clicked.connect(lambda: self.done(self.SAVE_AND_EXIT))
        button_layout.addWidget(save_exit_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)


class UnsavedGroupDialog(QDialog):
    """Dialog for handling unsaved tab group changes on close."""

    # Result codes
    CANCEL = 0
    EXIT_WITHOUT_SAVING = 1
    SAVE_GROUP = 2

    def __init__(self, group_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unsaved Tab Group")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Message
        message = QLabel(
            f"The tab group '{group_name}' has unsaved changes.\n\n"
            "This includes changes to:\n"
            "  • Tabs added or removed\n"
            "  • Tab emojis or display names\n"
            "  • Tab group name\n\n"
            "Would you like to save the tab group before exiting?"
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        exit_btn = QPushButton("❌ Exit")
        exit_btn.setToolTip("Exit without saving tab group")
        exit_btn.setStyleSheet(CLOSE_DIALOG_BUTTON_STYLE)
        exit_btn.clicked.connect(lambda: self.done(self.EXIT_WITHOUT_SAVING))
        button_layout.addWidget(exit_btn)

        cancel_btn = QPushButton("🔙 Cancel")
        cancel_btn.setToolTip("Cancel and return to editing")
        cancel_btn.setStyleSheet(CLOSE_DIALOG_BUTTON_STYLE)
        cancel_btn.clicked.connect(lambda: self.done(self.CANCEL))
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save Group")
        save_btn.setToolTip("Save tab group and exit")
        save_btn.setStyleSheet(CLOSE_DIALOG_BUTTON_STYLE)
        save_btn.clicked.connect(lambda: self.done(self.SAVE_GROUP))
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)


class GroupChangeWarningDialog(QDialog):
    """Dialog for handling unsaved changes when switching groups."""

    # Result codes
    CANCEL = 0
    DONT_SAVE = 1
    SAVE_ALL = 2

    def __init__(self, unsaved_files, has_group_changes, group_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unsaved Changes")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Build warning message
        message_parts = []
        if unsaved_files:
            message_parts.append("Unsaved file changes:\n" +
                               "\n".join(f"  • {name}" for name in unsaved_files))
        if has_group_changes:
            message_parts.append(f"Unsaved group changes: {group_name}")

        message_text = "\n\n".join(message_parts)
        message_text += "\n\nDo you want to save before switching groups?"

        label = QLabel(message_text)
        label.setWordWrap(True)
        layout.addWidget(label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lambda: self.done(self.CANCEL))
        button_layout.addWidget(cancel_btn)

        dont_save_btn = QPushButton("Don't Save")
        dont_save_btn.clicked.connect(lambda: self.done(self.DONT_SAVE))
        button_layout.addWidget(dont_save_btn)

        save_btn = QPushButton("Save All Changes")
        save_btn.clicked.connect(lambda: self.done(self.SAVE_ALL))
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)
