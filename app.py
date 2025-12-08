#!/usr/bin/env python3
"""
Minimal Tabbed Text Editor with PyQt6
Features: Multiple tabs, save/load files, save/load tab sessions
"""

import sys
import os
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QSplitter, QStackedWidget,
    QLabel, QFrame, QDialog, QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QSize, QDateTime
from PyQt6.QtGui import QAction, QShortcut, QKeySequence, QIcon, QGuiApplication

from constants import TAB_WIDTH_MINIMIZED, TAB_WIDTH_NORMAL, TAB_WIDTH_MAXIMIZED, MIN_SPLITTER_WIDTH
from models.tab_list_item_model import TextEditorTab
from widgets.tab_list import TabListWidget
from windows.find_replace import FindReplaceDialog


class TextEditorWindow(QMainWindow):
    """Main text editor window"""

    def __init__(self, tabs_file=None):
        super().__init__()
        self.current_tabs_file = None
        self.last_file_folder = None
        self.last_tabs_folder = None
        self.settings_file = os.path.join(os.path.dirname(__file__), '.editor_settings.json')
        self.tabs_metadata_modified = False  # Track if tab metadata (emoji/display name) has changed
        self._initial_splitter_set = False  # Track if initial splitter position has been applied
        self.find_replace_dialog = None  # Will be created when first needed

        self.init_ui()
        self.load_settings()

        # Load tabs file if provided
        if tabs_file:
            self.load_tabs(tabs_file)
        else:
            # Try to load auto-saved session
            self.load_auto_session()

    def showEvent(self, event):
        """Handle window show event to set initial splitter position"""
        super().showEvent(event)
        if not self._initial_splitter_set:
            self._initial_splitter_set = True
            # Apply the view mode's splitter position now that window has correct geometry
            self.tab_list.set_view_mode(self.tab_list.view_mode)

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Pin-Tab")
        self.setGeometry(100, 100, 1000, 700)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), 'favicon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create central widget with layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create button toolbar
        self.create_button_toolbar(main_layout)

        # Create horizontal splitter for sidebar and content
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create left sidebar with tab list
        self.tab_list = TabListWidget(self)
        self.tab_list.setMinimumWidth(TAB_WIDTH_MINIMIZED)  # Minimum width matches minimized mode
        self.splitter.addWidget(self.tab_list)

        # Create stacked widget for tab content
        self.content_stack = QStackedWidget()
        self.splitter.addWidget(self.content_stack)

        # Set initial sizes for normal mode (sidebar gets normal width, content gets 1000px)
        # Use a larger second value to ensure proper initial sizing
        self.splitter.setSizes([TAB_WIDTH_NORMAL, 1000])

        main_layout.addWidget(self.splitter, 1)  # Give splitter stretch factor

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Setup keyboard shortcuts
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+N - New file
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self.new_file)

        # Ctrl+O - Open file
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.load_file)

        # Ctrl+S - Save current tab
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_current_tab)

        # Ctrl+Shift+S - Save all
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.save_all)

        # Ctrl+F - Find
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.show_find_replace)

        # Ctrl+H - Find and Replace
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self.show_find_replace)

    def create_button_toolbar(self, layout):
        """Create button toolbar with file operations"""
        toolbar = QWidget()
        toolbar.setStyleSheet("QWidget { background-color: #E8E8E8; }")
        toolbar_main_layout = QVBoxLayout()
        toolbar_main_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_main_layout.setSpacing(5)

        # First row: file operations
        toolbar_row1 = QHBoxLayout()
        toolbar_row1.setSpacing(8)

        # Define button style for top row
        button_style = """
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #F8F8F8, stop:1 #E0E0E0);
                border: 1px solid #B0B0B0;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #FFFFFF, stop:1 #E8E8E8);
                border: 1px solid #909090;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #D0D0D0, stop:1 #C0C0C0);
                border: 1px solid #808080;
            }
        """

        # New button
        new_btn = QPushButton("📄 New")
        new_btn.setToolTip("Create new file (Ctrl+N)")
        new_btn.clicked.connect(self.new_file)
        new_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(new_btn)

        # Load button
        load_btn = QPushButton("📂 Load")
        load_btn.setToolTip("Open file (Ctrl+O)")
        load_btn.clicked.connect(self.load_file)
        load_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(load_btn)

        # Save button (current tab)
        save_btn = QPushButton("💾 Save")
        save_btn.setToolTip("Save current tab (Ctrl+S)")
        save_btn.clicked.connect(self.save_current_tab)
        save_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(save_btn)

        # Save All button
        self.save_all_btn = QPushButton("💾 Save All")
        self.save_all_btn.setToolTip("Save all modified files (Ctrl+Shift+S)")
        self.save_all_btn.clicked.connect(self.save_all)
        self.save_all_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(self.save_all_btn)

        # Separator
        toolbar_row1.addSpacing(20)

        # Load Tabs button
        load_tabs_btn = QPushButton("📋 Load Tabs")
        load_tabs_btn.setToolTip("Load tab session")
        load_tabs_btn.clicked.connect(self.load_tabs_dialog)
        load_tabs_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(load_tabs_btn)

        # Save Tabs button
        self.save_tabs_btn = QPushButton("💾 Save Tabs")
        self.save_tabs_btn.setToolTip("Save tab session")
        self.save_tabs_btn.clicked.connect(self.save_tabs_dialog)
        self.save_tabs_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(self.save_tabs_btn)

        # Store the default button style for later use
        self.default_button_style = button_style

        # Last saved labels
        self.last_saved_label = QLabel("")
        self.last_saved_label.setStyleSheet("color: #666666; font-style: italic; margin-left: 10px;")
        self.last_saved_label.setVisible(False)  # Hidden until first save
        toolbar_row1.addWidget(self.last_saved_label)

        self.last_saved_all_label = QLabel("")
        self.last_saved_all_label.setStyleSheet("color: #666666; font-style: italic; margin-left: 10px;")
        self.last_saved_all_label.setVisible(False)  # Hidden until first save
        toolbar_row1.addWidget(self.last_saved_all_label)

        # Add stretch to push buttons to the left
        toolbar_row1.addStretch()

        # About button on the right
        about_btn = QPushButton("ℹ️ About")
        about_btn.setToolTip("About Pin-Tab")
        about_btn.clicked.connect(self.show_about_dialog)
        about_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(about_btn)

        toolbar_main_layout.addLayout(toolbar_row1)

        # Add divider between rows
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #888888; min-height: 1px; max-height: 1px;")
        toolbar_main_layout.addWidget(divider)

        # Second row: view mode controls
        toolbar_row2 = QHBoxLayout()
        toolbar_row2.setSpacing(5)

        # View mode label
        view_label = QLabel("Tab View:")
        toolbar_row2.addWidget(view_label)

        # View mode buttons
        self.minimize_btn = QPushButton("📋")
        self.minimize_btn.setToolTip("Minimize tabs (emoji only)")
        self.minimize_btn.setMaximumWidth(30)
        self.minimize_btn.setCheckable(True)
        self.minimize_btn.clicked.connect(lambda: self.set_tab_view_mode('minimized'))
        toolbar_row2.addWidget(self.minimize_btn)

        self.normal_btn = QPushButton("📑")
        self.normal_btn.setToolTip("Normal view (emoji + filename)")
        self.normal_btn.setMaximumWidth(30)
        self.normal_btn.setCheckable(True)
        self.normal_btn.setChecked(True)  # Default mode
        self.normal_btn.clicked.connect(lambda: self.set_tab_view_mode('normal'))
        toolbar_row2.addWidget(self.normal_btn)

        self.maximize_btn = QPushButton("📊")
        self.maximize_btn.setToolTip("Maximize tabs (emoji + filename + modified time)")
        self.maximize_btn.setMaximumWidth(30)
        self.maximize_btn.setCheckable(True)
        self.maximize_btn.clicked.connect(lambda: self.set_tab_view_mode('maximized'))
        toolbar_row2.addWidget(self.maximize_btn)

        # Separator
        toolbar_row2.addSpacing(20)

        # Edit tab button
        self.edit_emoji_btn = QPushButton("✏️ Edit Tab")
        self.edit_emoji_btn.setToolTip("Edit emoji and display name for selected tab")
        self.edit_emoji_btn.clicked.connect(self.edit_selected_emoji)
        toolbar_row2.addWidget(self.edit_emoji_btn)

        # Find and Replace button
        self.find_replace_btn = QPushButton("🔍 Find & Replace")
        self.find_replace_btn.setToolTip("Find and replace text (Ctrl+F)")
        self.find_replace_btn.clicked.connect(self.show_find_replace)
        toolbar_row2.addWidget(self.find_replace_btn)

        # Add stretch to push buttons to the left
        toolbar_row2.addStretch()

        toolbar_main_layout.addLayout(toolbar_row2)

        # Add divider after second row
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet("background-color: #888888; min-height: 1px; max-height: 1px;")
        toolbar_main_layout.addWidget(divider2)

        toolbar.setLayout(toolbar_main_layout)
        layout.addWidget(toolbar)

    def get_default_file_folder(self):
        """Get the default folder for file dialogs"""
        # If user has used a folder before, use that
        if self.last_file_folder and os.path.exists(self.last_file_folder):
            return self.last_file_folder

        # Otherwise, use the folder of the first open tab
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.file_path:
                folder = os.path.dirname(widget.file_path)
                if os.path.exists(folder):
                    return folder

        # Default to home directory
        return str(Path.home())

    def get_default_tabs_folder(self):
        """Get the default folder for tabs file dialogs"""
        # If user has used a tabs folder before, use that
        if self.last_tabs_folder and os.path.exists(self.last_tabs_folder):
            return self.last_tabs_folder

        # Otherwise, use the current tabs file location
        if self.current_tabs_file:
            folder = os.path.dirname(self.current_tabs_file)
            if os.path.exists(folder):
                return folder

        # Default to first tab's folder
        return self.get_default_file_folder()

    def new_file(self):
        """Create a new empty file tab"""
        tab = TextEditorTab()
        self.content_stack.addWidget(tab)
        self.tab_list.add_tab(tab)
        self.switch_to_tab(tab)

    def load_file(self):
        """Load a file into a new tab"""
        try:
            default_folder = self.get_default_file_folder()

            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open File",
                default_folder,
                "All Files (*);;Text Files (*.txt);;Markdown Files (*.md)"
            )

            if file_path:
                # Convert to absolute path
                file_path = os.path.abspath(file_path)

                # Update last folder
                self.last_file_folder = os.path.dirname(file_path)

                # Check file size
                file_size = os.path.getsize(file_path)
                size_mb = file_size / (1024 * 1024)

                # Refuse files over 100MB
                if size_mb > 100:
                    QMessageBox.critical(
                        self,
                        "File Too Large",
                        f"'{os.path.basename(file_path)}' is {size_mb:.1f} MB.\n\n"
                        f"Files larger than 100 MB cannot be opened in this editor."
                    )
                    return

                # Warn for files over 1MB
                if size_mb > 1:
                    response = QMessageBox.warning(
                        self,
                        "Large File Warning",
                        f"'{os.path.basename(file_path)}' is {size_mb:.1f} MB.\n\n"
                        f"Large files may cause performance issues.\n"
                        f"Do you want to continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if response == QMessageBox.StandardButton.No:
                        return

                # Check if file is already open
                for i in range(self.content_stack.count()):
                    widget = self.content_stack.widget(i)
                    if isinstance(widget, TextEditorTab) and widget.file_path == file_path:
                        self.switch_to_tab(widget)
                        QMessageBox.information(
                            self,
                            "File Already Open",
                            f"'{os.path.basename(file_path)}' is already open.\nSwitched to that tab."
                        )
                        return

                # Create new tab and load file
                tab = TextEditorTab(file_path)
                self.content_stack.addWidget(tab)
                self.tab_list.add_tab(tab)
                self.switch_to_tab(tab)
        except Exception as e:
            print(f"ERROR in load_file: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{str(e)}")

    def show_find_replace(self):
        """Show the find and replace dialog"""
        # Get current tab
        current_tab = self.content_stack.currentWidget()
        if not isinstance(current_tab, TextEditorTab):
            QMessageBox.information(self, "No File", "Please open a file first.")
            return

        # Create or update dialog
        if self.find_replace_dialog is None:
            self.find_replace_dialog = FindReplaceDialog(current_tab.text_edit, self)
        else:
            # Update the text edit reference to current tab
            self.find_replace_dialog.text_edit = current_tab.text_edit

        # Show dialog
        self.find_replace_dialog.show()
        self.find_replace_dialog.raise_()
        self.find_replace_dialog.activateWindow()

    def save_current_tab(self):
        """Save the currently active tab"""
        current_tab = self.get_current_tab()
        if current_tab:
            self.save_single_tab(current_tab)

    def save_single_tab(self, tab):
        """Save a single tab"""
        if not isinstance(tab, TextEditorTab):
            return

        if tab.file_path:
            # File already has a path, just save
            tab.save_file()
            self.tab_list.update_tab_display(tab)
            # Update Save All button in case all files are now saved
            self.update_save_all_button()
        else:
            # Need to prompt for save location
            default_folder = self.get_default_file_folder()

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File As",
                default_folder,
                "All Files (*);;Text Files (*.txt);;Markdown Files (*.md)"
            )

            if file_path:
                # Convert to absolute path
                file_path = os.path.abspath(file_path)

                # Update last folder
                self.last_file_folder = os.path.dirname(file_path)

                tab.save_file(file_path)
                self.tab_list.update_tab_display(tab)
                # Update Save All button in case all files are now saved
                self.update_save_all_button()

    def save_all(self):
        """Save all modified files"""
        saved_count = 0

        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified:
                if widget.file_path:
                    widget.save_file()
                    self.tab_list.update_tab_display(widget)
                    saved_count += 1

        # Update last saved timestamp if anything was saved
        if saved_count > 0:
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M")
            self.last_saved_all_label.setText(f"Saved files {current_time}")
            self.last_saved_all_label.setVisible(True)

        # Update button appearance
        self.update_save_all_button()

    def update_save_all_button(self):
        """Update the Save All button appearance based on whether there are unsaved changes"""
        has_unsaved = False
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified and widget.file_path:
                has_unsaved = True
                break

        if has_unsaved:
            # Highlight button with yellow/warning color
            modified_style = """
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #FFFDE7, stop:1 #FFF9C4);
                    border: 1px solid #F9A825;
                    border-radius: 6px;
                    padding: 6px 12px;
                    min-height: 24px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #FFFEF0, stop:1 #FFEB3B);
                    border: 1px solid #F57F17;
                }
                QPushButton:pressed {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #FFF59D, stop:1 #FBC02D);
                    border: 1px solid #E65100;
                }
            """
            self.save_all_btn.setStyleSheet(modified_style)
            self.save_all_btn.setText("⚠️ Save All")
        else:
            # Reset to default style
            self.save_all_btn.setStyleSheet(self.default_button_style)
            self.save_all_btn.setText("💾 Save All")

    def close_tab(self, widget):
        """Close the given tab widget"""
        if not isinstance(widget, TextEditorTab):
            return

        # Check if pinned
        if widget.is_pinned:
            reply = QMessageBox.question(
                self,
                "Close Pinned Tab",
                "This tab is pinned. Are you sure you want to close it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Check for unsaved changes
        if widget.is_modified:
            file_name = os.path.basename(widget.file_path) if widget.file_path else "Untitled"
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"'{file_name}' has unsaved changes. Do you want to save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_single_tab(widget)
                # Check if save was successful
                if widget.is_modified:
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        # Remove from tab list and content stack
        self.tab_list.remove_tab(widget)
        self.content_stack.removeWidget(widget)
        widget.deleteLater()

    def toggle_pin(self, widget):
        """Toggle pin status of a tab"""
        if not isinstance(widget, TextEditorTab):
            return

        # Save custom emoji and display name before removing
        custom_emoji = None
        custom_display_name = None
        for tab_item in self.tab_list.tab_items:
            if tab_item.editor_tab == widget:
                custom_emoji = tab_item.custom_emoji
                custom_display_name = tab_item.custom_display_name
                break

        # Toggle the pin status
        widget.is_pinned = not widget.is_pinned

        # Remove and re-add to reorder in the list
        self.tab_list.remove_tab(widget)
        new_tab_item = self.tab_list.add_tab(widget)

        # Restore custom emoji and display name
        if custom_emoji is not None:
            new_tab_item.custom_emoji = custom_emoji
        if custom_display_name is not None:
            new_tab_item.custom_display_name = custom_display_name
        new_tab_item.update_display()

        # Select it again
        self.tab_list.select_tab(new_tab_item)

    def switch_to_tab(self, tab):
        """Switch to a specific tab"""
        if isinstance(tab, TextEditorTab):
            self.content_stack.setCurrentWidget(tab)

    def set_tab_view_mode(self, mode):
        """Set the view mode for the tab list"""
        # Update button states
        self.minimize_btn.setChecked(mode == 'minimized')
        self.normal_btn.setChecked(mode == 'normal')
        self.maximize_btn.setChecked(mode == 'maximized')

        # Update the tab list view mode
        self.tab_list.set_view_mode(mode)

    def edit_selected_emoji(self):
        """Edit the emoji and display name for the selected tab"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QCheckBox

        # Find the selected tab
        selected_tab_item = None
        for tab_item in self.tab_list.tab_items:
            if tab_item.is_selected:
                selected_tab_item = tab_item
                break

        if not selected_tab_item:
            QMessageBox.information(self, "No Tab Selected", "Please select a tab first.")
            return

        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Tab Appearance")
        layout = QVBoxLayout()

        # Style for input fields
        input_style = """
            QLineEdit {
                background-color: white;
                border: 1px solid #B0B0B0;
                border-radius: 3px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
        """

        # Style for dialog buttons
        button_style = """
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #F8F8F8, stop:1 #E0E0E0);
                border: 1px solid #B0B0B0;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 60px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #FFFFFF, stop:1 #E8E8E8);
                border: 1px solid #909090;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #D0D0D0, stop:1 #C0C0C0);
                border: 1px solid #808080;
            }
        """

        # Emoji input
        emoji_layout = QHBoxLayout()
        emoji_label = QLabel("Emoji:")
        emoji_label.setFixedWidth(100)
        emoji_layout.addWidget(emoji_label)
        emoji_input = QLineEdit()
        emoji_input.setText(selected_tab_item.get_emoji())
        emoji_input.setPlaceholderText("e.g., 📄 or P")
        emoji_input.setStyleSheet(input_style)
        emoji_layout.addWidget(emoji_input)
        layout.addLayout(emoji_layout)

        # Display name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Display Name:")
        name_label.setFixedWidth(100)
        name_layout.addWidget(name_label)
        name_input = QLineEdit()
        name_input.setText(selected_tab_item.custom_display_name or "")
        # Show what the default display name will be (without custom override)
        default_name = "Untitled"
        if selected_tab_item.editor_tab.file_path:
            filename = os.path.basename(selected_tab_item.editor_tab.file_path)
            name_without_ext = os.path.splitext(filename)[0]
            default_name = name_without_ext.lstrip('_') or filename
        name_input.setPlaceholderText(f"Default: {default_name}")
        name_input.setStyleSheet(input_style)
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)

        # Pin checkbox
        pin_layout = QHBoxLayout()
        pin_label = QLabel("")
        pin_label.setFixedWidth(100)
        pin_layout.addWidget(pin_label)
        pin_checkbox = QCheckBox("📌 Pin this tab")
        pin_checkbox.setChecked(selected_tab_item.editor_tab.is_pinned)
        pin_layout.addWidget(pin_checkbox)
        pin_layout.addStretch()
        layout.addLayout(pin_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(button_style)
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(button_style)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.setMinimumWidth(400)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update emoji if changed
            new_emoji = emoji_input.text().strip()
            if new_emoji and new_emoji != selected_tab_item.get_emoji():
                selected_tab_item.custom_emoji = new_emoji
            elif not new_emoji:
                selected_tab_item.custom_emoji = None

            # Update display name if changed
            new_name = name_input.text().strip()
            if new_name:
                selected_tab_item.custom_display_name = new_name
            else:
                selected_tab_item.custom_display_name = None

            # Update pin status if changed
            new_pin_status = pin_checkbox.isChecked()
            if new_pin_status != selected_tab_item.editor_tab.is_pinned:
                self.toggle_pin(selected_tab_item.editor_tab)

            selected_tab_item.update_display()
            self.mark_tabs_metadata_modified()

    def get_current_tab(self):
        """Get the currently active tab"""
        current_widget = self.content_stack.currentWidget()
        if isinstance(current_widget, TextEditorTab):
            return current_widget
        return None

    def mark_tabs_metadata_modified(self):
        """Mark that tab metadata (emoji/display name) has been modified"""
        self.tabs_metadata_modified = True
        self.save_tabs_btn.setText("⚠️ Save Tabs")
        # Override button style with yellow background while preserving structure
        modified_style = """
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #FFFDE7, stop:1 #FFF9C4);
                border: 1px solid #F9A825;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #FFFEF0, stop:1 #FFEB3B);
                border: 1px solid #F57F17;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #FFF59D, stop:1 #FBC02D);
                border: 1px solid #E65100;
            }
        """
        self.save_tabs_btn.setStyleSheet(modified_style)

    def update_tab_title(self, tab):
        """Update the title of a tab"""
        self.tab_list.update_tab_display(tab)
        # Update Save All button when any tab changes
        self.update_save_all_button()

    def update_window_title(self):
        """Update the window title based on current tabs file"""
        if self.current_tabs_file:
            filename = os.path.basename(self.current_tabs_file)
            # Remove .tabs extension for display
            if filename.endswith('.tabs'):
                filename = filename[:-5]
            self.setWindowTitle(filename)
        else:
            self.setWindowTitle("Pin-Tab")

    def show_about_dialog(self):
        """Show the About dialog with keyboard shortcuts and info"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("About Pin-Tab")
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("<h2>Pin-Tab Text Editor</h2>")
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
</table>
        """)
        layout.addWidget(shortcuts_text)

        # About section
        about_label = QLabel("<h3>About</h3>")
        layout.addWidget(about_label)

        about_text = QLabel("""
A free text editor created by <a href="https://oddturnip.com">OddTurnip.com</a>,
using <a href="https://docs.claude.com/en/docs/claude-code">Claude Code</a>.
        """)
        about_text.setOpenExternalLinks(True)  # Enable clickable links
        about_text.setWordWrap(True)
        layout.addWidget(about_text)

        # Close button
        button_style = """
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #F8F8F8, stop:1 #E0E0E0);
                border: 1px solid #B0B0B0;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 80px;
                min-height: 22px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #FFFFFF, stop:1 #E8E8E8);
                border: 1px solid #909090;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #D0D0D0, stop:1 #C0C0C0);
                border: 1px solid #808080;
            }
        """
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(button_style)
        close_btn.clicked.connect(dialog.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.setMinimumWidth(450)
        dialog.exec()

    def save_tabs_dialog(self):
        """Show dialog to save current tabs"""
        # Check for unsaved or untitled documents
        unsaved_files = []
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab):
                if not widget.file_path:
                    unsaved_files.append("Untitled (not saved)")
                elif widget.is_modified:
                    unsaved_files.append(os.path.basename(widget.file_path) + " (modified)")

        # Warn if there are unsaved files
        if unsaved_files:
            message = "The following documents will be excluded from the saved tabs:\n\n"
            message += "\n".join(f"  • {name}" for name in unsaved_files)
            message += "\n\nDo you want to continue?"

            reply = QMessageBox.question(
                self,
                "Unsaved Documents",
                message,
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return

        default_folder = self.get_default_tabs_folder()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Tabs",
            default_folder,
            "Tabs Files (*.tabs)"
        )

        if file_path:
            # Ensure .tabs extension
            if not file_path.endswith('.tabs'):
                file_path += '.tabs'

            # Convert to absolute path
            file_path = os.path.abspath(file_path)

            # Update last tabs folder
            self.last_tabs_folder = os.path.dirname(file_path)

            self.save_tabs(file_path)

    def save_tabs(self, tabs_file_path):
        """Save all open tabs to an XML file"""
        # Create XML structure
        root = ET.Element('tabs')
        root.set('version', '1.0')

        # Determine current tab
        current_tab = self.get_current_tab()
        current_index = 0
        tab_count = 0

        # Save all tabs (pinned tabs are already at the top in tab_list)
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.file_path:
                tab_elem = ET.SubElement(root, 'tab')
                tab_elem.set('path', widget.file_path)
                tab_elem.set('pinned', str(widget.is_pinned))

                # Save custom emoji and display name if set
                for tab_item in self.tab_list.tab_items:
                    if tab_item.editor_tab == widget:
                        if tab_item.custom_emoji:
                            tab_elem.set('emoji', tab_item.custom_emoji)
                        if tab_item.custom_display_name:
                            tab_elem.set('display_name', tab_item.custom_display_name)
                        break

                if widget == current_tab:
                    current_index = tab_count
                tab_count += 1

        root.set('current', str(current_index))

        # Write XML to file with pretty formatting
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open(tabs_file_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        # Create .bat file
        self.create_bat_file(tabs_file_path)

        # Update current tabs file and window title
        self.current_tabs_file = tabs_file_path
        self.update_window_title()

        # Update last saved timestamp
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M")
        self.last_saved_label.setText(f"Saved tabs {current_time}")
        self.last_saved_label.setVisible(True)

        # Clear metadata modified flag and reset button appearance
        self.tabs_metadata_modified = False
        self.save_tabs_btn.setText("💾 Save Tabs")
        self.save_tabs_btn.setStyleSheet(self.default_button_style)  # Reset to default style

    def create_bat_file(self, tabs_file_path):
        """Create a .bat file to launch editor with tabs"""
        bat_path = tabs_file_path.replace('.tabs', '.bat')
        script_path = os.path.abspath(__file__)

        # Create batch file content that doesn't leave a window open
        bat_content = f'@echo off\n'
        bat_content += f'start "" pythonw "{script_path}" "{tabs_file_path}"\n'

        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)

    def load_tabs_dialog(self):
        """Show dialog to load tabs"""
        default_folder = self.get_default_tabs_folder()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Tabs",
            default_folder,
            "Tabs Files (*.tabs)"
        )

        if file_path:
            # Update last tabs folder
            self.last_tabs_folder = os.path.dirname(file_path)
            self.load_tabs(file_path)

    def load_tabs(self, tabs_file_path):
        """Load tabs from an XML file"""
        try:
            # Parse XML file
            tree = ET.parse(tabs_file_path)
            root = tree.getroot()

            # Close all existing tabs
            while self.content_stack.count() > 0:
                widget = self.content_stack.widget(0)
                self.content_stack.removeWidget(widget)
                widget.deleteLater()
            self.tab_list.tab_items.clear()
            # Clear the tab layout
            for i in reversed(range(self.tab_list.tab_layout.count())):
                item = self.tab_list.tab_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()

            # Get current tab index
            current_index = int(root.get('current', '0'))
            loaded_tabs = []

            # Load each tab
            for tab_elem in root.findall('tab'):
                file_path = tab_elem.get('path')
                is_pinned = tab_elem.get('pinned', 'False') == 'True'
                custom_emoji = tab_elem.get('emoji')  # May be None
                custom_display_name = tab_elem.get('display_name')  # May be None

                if os.path.exists(file_path):
                    tab = TextEditorTab(file_path)
                    tab.is_pinned = is_pinned

                    # Add to content stack and tab list
                    self.content_stack.addWidget(tab)
                    tab_item = self.tab_list.add_tab(tab)

                    # Set custom emoji and display name if they were saved
                    if custom_emoji:
                        tab_item.custom_emoji = custom_emoji
                    if custom_display_name:
                        tab_item.custom_display_name = custom_display_name
                    if custom_emoji or custom_display_name:
                        tab_item.update_display()

                    loaded_tabs.append(tab)

            # Set current tab
            if current_index < len(loaded_tabs):
                current_tab = loaded_tabs[current_index]
                self.switch_to_tab(current_tab)
                # Select in tab list
                for tab_item in self.tab_list.tab_items:
                    if tab_item.editor_tab == current_tab:
                        self.tab_list.select_tab(tab_item)
                        break

            # Update current tabs file and window title
            self.current_tabs_file = tabs_file_path
            self.update_window_title()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load tabs:\n{str(e)}")

    def save_settings(self):
        """Save window settings and current session"""
        settings = {
            'geometry': {
                'x': self.x(),
                'y': self.y(),
                'width': self.width(),
                'height': self.height()
            },
            'last_file_folder': self.last_file_folder,
            'last_tabs_folder': self.last_tabs_folder,
            'current_tabs_file': self.current_tabs_file,
            'view_mode': self.tab_list.view_mode
        }

        # Auto-save current session
        auto_session = {
            'tabs': [],
            'current_index': 0
        }

        current_tab = self.get_current_tab()
        tab_count = 0

        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.file_path:
                tab_data = {
                    'path': widget.file_path,
                    'pinned': widget.is_pinned
                }

                # Save custom emoji and display name if set
                for tab_item in self.tab_list.tab_items:
                    if tab_item.editor_tab == widget:
                        if tab_item.custom_emoji:
                            tab_data['emoji'] = tab_item.custom_emoji
                        if tab_item.custom_display_name:
                            tab_data['display_name'] = tab_item.custom_display_name
                        break

                auto_session['tabs'].append(tab_data)
                if widget == current_tab:
                    auto_session['current_index'] = tab_count
                tab_count += 1

        settings['auto_session'] = auto_session

        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def load_settings(self):
        """Load window settings"""
        if not os.path.exists(self.settings_file):
            return

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # Restore geometry
            if 'geometry' in settings:
                geo = settings['geometry']
                # Get the available screen geometry
                from PyQt6.QtGui import QGuiApplication
                screen = QGuiApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()

                # Ensure window is not too large for screen
                width = min(geo['width'], screen_geometry.width())
                height = min(geo['height'], screen_geometry.height())

                # Ensure window is within screen bounds with padding for title bar
                # Add 50px minimum from top to ensure title bar is always visible
                min_top_margin = 50
                x = max(screen_geometry.x(), min(geo['x'], screen_geometry.right() - width))
                y = max(screen_geometry.y() + min_top_margin, min(geo['y'], screen_geometry.bottom() - height))

                self.setGeometry(x, y, width, height)

            # Restore last folders
            self.last_file_folder = settings.get('last_file_folder')
            self.last_tabs_folder = settings.get('last_tabs_folder')
            self.current_tabs_file = settings.get('current_tabs_file')

            # Restore view mode (this will set the correct splitter size)
            view_mode = settings.get('view_mode', 'normal')
            self.set_tab_view_mode(view_mode)

            if self.current_tabs_file:
                self.update_window_title()

        except Exception as e:
            print(f"Failed to load settings: {e}")

    def load_auto_session(self):
        """Load auto-saved session"""
        if not os.path.exists(self.settings_file):
            # First launch - start with empty editor
            return

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            if 'auto_session' not in settings or not settings['auto_session']['tabs']:
                # No saved session - start with empty editor
                return

            auto_session = settings['auto_session']
            loaded_tabs = []

            # Load each tab
            for tab_data in auto_session['tabs']:
                file_path = tab_data['path']
                is_pinned = tab_data.get('pinned', False)
                custom_emoji = tab_data.get('emoji')  # May be None
                custom_display_name = tab_data.get('display_name')  # May be None

                if os.path.exists(file_path):
                    tab = TextEditorTab(file_path)
                    tab.is_pinned = is_pinned

                    # Add to content stack and tab list
                    self.content_stack.addWidget(tab)
                    tab_item = self.tab_list.add_tab(tab)

                    # Set custom emoji and display name if they were saved
                    if custom_emoji:
                        tab_item.custom_emoji = custom_emoji
                    if custom_display_name:
                        tab_item.custom_display_name = custom_display_name
                    if custom_emoji or custom_display_name:
                        tab_item.update_display()

                    loaded_tabs.append(tab)

            # Set current tab
            current_index = auto_session.get('current_index', 0)
            if current_index < len(loaded_tabs):
                current_tab = loaded_tabs[current_index]
                self.switch_to_tab(current_tab)
                # Select in tab list
                for tab_item in self.tab_list.tab_items:
                    if tab_item.editor_tab == current_tab:
                        self.tab_list.select_tab(tab_item)
                        break

        except Exception as e:
            print(f"Failed to load auto-session: {e}")
            # On error, start with empty editor

    def closeEvent(self, event):
        """Handle window close event"""
        # Check for unsaved changes in all tabs
        modified_tabs = []
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified:
                file_name = os.path.basename(widget.file_path) if widget.file_path else "Untitled"
                modified_tabs.append(file_name)

        if modified_tabs:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Unsaved Changes")
            layout = QVBoxLayout()

            # Message
            message = QLabel(
                "The following files have unsaved changes:\n\n" +
                "\n".join(f"  • {name}" for name in modified_tabs) +
                "\n\nWhat would you like to do?"
            )
            layout.addWidget(message)

            # Button style
            button_style = """
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #F8F8F8, stop:1 #E0E0E0);
                    border: 1px solid #B0B0B0;
                    border-radius: 4px;
                    padding: 8px 16px;
                    min-width: 100px;
                    min-height: 28px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #FFFFFF, stop:1 #E8E8E8);
                    border: 1px solid #909090;
                }
                QPushButton:pressed {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #D0D0D0, stop:1 #C0C0C0);
                    border: 1px solid #808080;
                }
            """

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            exit_btn = QPushButton("❌ Exit")
            exit_btn.setToolTip("Exit without saving changes")
            exit_btn.setStyleSheet(button_style)
            exit_btn.clicked.connect(lambda: dialog.done(1))  # Exit without saving
            button_layout.addWidget(exit_btn)

            cancel_btn = QPushButton("🔙 Cancel")
            cancel_btn.setToolTip("Cancel and return to editing")
            cancel_btn.setStyleSheet(button_style)
            cancel_btn.clicked.connect(lambda: dialog.done(0))  # Cancel
            button_layout.addWidget(cancel_btn)

            save_exit_btn = QPushButton("💾 Save and Exit")
            save_exit_btn.setToolTip("Save all changes and exit")
            save_exit_btn.setStyleSheet(button_style)
            save_exit_btn.clicked.connect(lambda: dialog.done(2))  # Save and exit
            button_layout.addWidget(save_exit_btn)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.setMinimumWidth(400)

            result = dialog.exec()

            if result == 0:  # Cancel
                event.ignore()
                return
            elif result == 2:  # Save and exit
                # Save all files that can be saved
                for i in range(self.content_stack.count()):
                    widget = self.content_stack.widget(i)
                    if isinstance(widget, TextEditorTab) and widget.is_modified and widget.file_path:
                        widget.save_file()
            # result == 1: Exit without saving, just continue

        # Save settings and session before closing
        self.save_settings()
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)

    # Set application icon (for taskbar)
    icon_path = os.path.join(os.path.dirname(__file__), 'favicon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Check if tabs file was provided as argument
    tabs_file = None
    if len(sys.argv) > 1:
        tabs_file = sys.argv[1]
        if not os.path.exists(tabs_file):
            print(f"Warning: Tabs file not found: {tabs_file}")
            tabs_file = None

    window = TextEditorWindow(tabs_file)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
