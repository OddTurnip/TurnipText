#!/usr/bin/env python3
"""
Minimal Tabbed Text Editor with PyQt6
Features: Multiple tabs, save/load files, save/load tab sessions
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QSplitter, QStackedWidget,
    QLabel, QFrame, QLineEdit, QCheckBox, QComboBox, QDialog
)
from PyQt6.QtCore import Qt, QSize, QDateTime, QFileSystemWatcher
from PyQt6.QtGui import QAction, QShortcut, QKeySequence, QIcon, QGuiApplication

from constants import TAB_WIDTH_MINIMIZED, TAB_WIDTH_NORMAL, TAB_WIDTH_MAXIMIZED, MIN_SPLITTER_WIDTH
from models.tab_list_item_model import TextEditorTab
from widgets.tab_list import TabListWidget
from windows.find_replace import FindReplaceDialog
from windows.icon_editor import IconEditorDialog
from windows.dialogs import (
    EditTabDialog, EditGroupDialog, AboutDialog,
    UnsavedChangesDialog, UnsavedGroupDialog, GroupChangeWarningDialog
)
from styles import BUTTON_STYLE, MODIFIED_BUTTON_STYLE
from managers.tab_groups import TabGroupManager, get_tabs_data_from_widgets
from managers.settings import SettingsManager, get_tabs_data_for_session


def get_app_dir():
    """Get the application directory for settings - stored next to exe or script"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(__file__)


def get_resource_dir():
    """Get the directory for bundled resources (icons, etc.) - works for PyInstaller onefile"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe (PyInstaller) - resources are in temp folder
        return sys._MEIPASS
    else:
        # Running as script - resources are in same directory
        return os.path.dirname(__file__)


class TextEditorWindow(QMainWindow):
    """Main text editor window"""

    def __init__(self, tabs_file=None):
        super().__init__()
        self.last_file_folder = None
        self.last_tabs_folder = None
        self._initial_splitter_set = False  # Track if initial splitter position has been applied
        self.find_replace_dialog = None  # Will be created when first needed

        # Settings manager handles preferences and session persistence
        settings_file = os.path.join(get_app_dir(), '.editor_settings.json')
        self.settings_manager = SettingsManager(settings_file)

        # Tab group manager handles save/load operations and state tracking
        self.tab_group_manager = TabGroupManager()

        # File system watcher for detecting external changes
        self.file_watcher = QFileSystemWatcher(self)
        self.file_watcher.fileChanged.connect(self._on_file_changed)
        self._pending_reload_files = set()  # Track files pending reload prompt
        self._saving_files = set()  # Track files being saved internally (to ignore watcher)

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
        self.setWindowTitle("TurnipText")
        self.setGeometry(100, 100, 1000, 700)

        # Set window icon
        icon_path = os.path.join(get_resource_dir(), 'favicon.ico')
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

        # Ctrl+I - Document Info/Statistics
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self.show_document_stats)

    def create_button_toolbar(self, layout):
        """Create button toolbar with file operations"""
        toolbar = QWidget()
        toolbar.setStyleSheet("QWidget { background-color: #E8E8E8; }")
        toolbar_main_layout = QVBoxLayout()
        toolbar_main_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_main_layout.setSpacing(5)

        # Use centralized button style
        button_style = BUTTON_STYLE

        # Store the default button style for later use
        self.default_button_style = button_style

        # Label style
        label_style = "font-weight: bold; margin-right: 5px;"

        # First row: Tabs (file operations)
        toolbar_row1 = QHBoxLayout()
        toolbar_row1.setSpacing(8)

        # Tabs label
        tabs_label = QLabel("Tabs:")
        tabs_label.setStyleSheet(label_style)
        toolbar_row1.addWidget(tabs_label)

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
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setToolTip("Save current tab (Ctrl+S)")
        self.save_btn.clicked.connect(self.save_current_tab)
        self.save_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(self.save_btn)

        # Save All Changes button (saves files AND group)
        self.save_all_btn = QPushButton("💾 Save All Changes")
        self.save_all_btn.setToolTip("Save all modified files and group (Ctrl+Shift+S)")
        self.save_all_btn.clicked.connect(self.save_all)
        self.save_all_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(self.save_all_btn)

        # Last saved all label
        self.last_saved_all_label = QLabel("")
        self.last_saved_all_label.setStyleSheet("color: #666666; font-style: italic; margin-left: 10px;")
        self.last_saved_all_label.setVisible(False)  # Hidden until first save
        toolbar_row1.addWidget(self.last_saved_all_label)

        # Add stretch to push buttons to the left
        toolbar_row1.addStretch()

        # About button on the right
        about_btn = QPushButton("ℹ️ About")
        about_btn.setToolTip("About TurnipText")
        about_btn.clicked.connect(self.show_about_dialog)
        about_btn.setStyleSheet(button_style)
        toolbar_row1.addWidget(about_btn)

        toolbar_main_layout.addLayout(toolbar_row1)

        # Add divider between rows
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet("background-color: #888888; min-height: 1px; max-height: 1px;")
        toolbar_main_layout.addWidget(divider1)

        # Second row: Groups (tab session operations)
        toolbar_row2 = QHBoxLayout()
        toolbar_row2.setSpacing(8)

        # Groups label
        groups_label = QLabel("Groups:")
        groups_label.setStyleSheet(label_style)
        toolbar_row2.addWidget(groups_label)

        # New Group button
        new_group_btn = QPushButton("📄 New Group")
        new_group_btn.setToolTip("Create a new tab group")
        new_group_btn.clicked.connect(self.new_group_dialog)
        new_group_btn.setStyleSheet(button_style)
        toolbar_row2.addWidget(new_group_btn)

        # Load Group button
        load_group_btn = QPushButton("📂 Load Group")
        load_group_btn.setToolTip("Load tab group")
        load_group_btn.clicked.connect(self.load_tabs_dialog)
        load_group_btn.setStyleSheet(button_style)
        toolbar_row2.addWidget(load_group_btn)

        # Save Group button
        self.save_group_btn = QPushButton("💾 Save Group")
        self.save_group_btn.setToolTip("Save tab group")
        self.save_group_btn.clicked.connect(self.save_group)
        self.save_group_btn.setStyleSheet(button_style)
        toolbar_row2.addWidget(self.save_group_btn)

        # Edit Group button
        edit_group_btn = QPushButton("✏️ Edit Group")
        edit_group_btn.setToolTip("Edit tab group name")
        edit_group_btn.clicked.connect(self.edit_tabs_dialog)
        edit_group_btn.setStyleSheet(button_style)
        toolbar_row2.addWidget(edit_group_btn)

        # Separator before History
        toolbar_row2.addSpacing(20)

        # History label
        history_label = QLabel("History:")
        history_label.setStyleSheet(label_style)
        toolbar_row2.addWidget(history_label)

        # History dropdown
        self.history_combo = QComboBox()
        self.history_combo.setToolTip("Recently loaded tab groups")
        self.history_combo.setMinimumWidth(150)
        self.history_combo.setMaximumWidth(250)
        self.history_combo.addItem("(no recent groups)")
        self.history_combo.setEnabled(False)
        self.history_combo.currentIndexChanged.connect(self._on_history_selected)
        # Style the combo box with custom arrow image (required when styling ::drop-down)
        arrow_path = os.path.join(get_app_dir(), 'icons', 'dropdown_arrow.png').replace('\\', '/')
        combo_style = f"""
            QComboBox {{
                background-color: white;
                border: 1px solid #B0B0B0;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 20px;
            }}
            QComboBox:hover {{
                border: 1px solid #909090;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: 1px solid black;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_path});
                width: 10px;
                height: 6px;
            }}
        """
        self.history_combo.setStyleSheet(combo_style)
        toolbar_row2.addWidget(self.history_combo)

        # Last saved label for groups
        self.last_saved_label = QLabel("")
        self.last_saved_label.setStyleSheet("color: #666666; font-style: italic; margin-left: 10px;")
        self.last_saved_label.setVisible(False)  # Hidden until first save
        toolbar_row2.addWidget(self.last_saved_label)

        # Add stretch to push buttons to the left
        toolbar_row2.addStretch()

        toolbar_main_layout.addLayout(toolbar_row2)

        # Add divider between rows
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.Shape.HLine)
        divider2.setStyleSheet("background-color: #888888; min-height: 1px; max-height: 1px;")
        toolbar_main_layout.addWidget(divider2)

        # Third row: view mode controls
        toolbar_row3 = QHBoxLayout()
        toolbar_row3.setSpacing(5)

        # View mode label
        view_label = QLabel("Tab View:")
        toolbar_row3.addWidget(view_label)

        # View mode buttons
        self.minimize_btn = QPushButton("📋")
        self.minimize_btn.setToolTip("Minimize tabs (emoji only)")
        self.minimize_btn.setMaximumWidth(30)
        self.minimize_btn.setCheckable(True)
        self.minimize_btn.clicked.connect(lambda: self.set_tab_view_mode('minimized'))
        toolbar_row3.addWidget(self.minimize_btn)

        self.normal_btn = QPushButton("📑")
        self.normal_btn.setToolTip("Normal view (emoji + filename)")
        self.normal_btn.setMaximumWidth(30)
        self.normal_btn.setCheckable(True)
        self.normal_btn.setChecked(True)  # Default mode
        self.normal_btn.clicked.connect(lambda: self.set_tab_view_mode('normal'))
        toolbar_row3.addWidget(self.normal_btn)

        self.maximize_btn = QPushButton("📊")
        self.maximize_btn.setToolTip("Maximize tabs (emoji + filename + modified time)")
        self.maximize_btn.setMaximumWidth(30)
        self.maximize_btn.setCheckable(True)
        self.maximize_btn.clicked.connect(lambda: self.set_tab_view_mode('maximized'))
        toolbar_row3.addWidget(self.maximize_btn)

        # Separator
        toolbar_row3.addSpacing(20)

        # Edit tab button
        self.edit_emoji_btn = QPushButton("✏️ Edit Tab")
        self.edit_emoji_btn.setToolTip("Edit emoji and display name for selected tab")
        self.edit_emoji_btn.clicked.connect(self.edit_selected_emoji)
        toolbar_row3.addWidget(self.edit_emoji_btn)

        # Find and Replace button
        self.find_replace_btn = QPushButton("🔍 Find && Replace")
        self.find_replace_btn.setToolTip("Find and replace text (Ctrl+F)")
        self.find_replace_btn.clicked.connect(self.show_find_replace)
        toolbar_row3.addWidget(self.find_replace_btn)

        # Separator
        toolbar_row3.addSpacing(20)

        # Render Markdown checkbox
        self.render_markdown_checkbox = QCheckBox("Render Markdown")
        self.render_markdown_checkbox.setToolTip("Enable markdown syntax highlighting")
        self.render_markdown_checkbox.setChecked(True)  # Default to checked
        self.render_markdown_checkbox.stateChanged.connect(self.toggle_markdown_rendering)
        toolbar_row3.addWidget(self.render_markdown_checkbox)

        # Line Numbers checkbox
        self.line_numbers_checkbox = QCheckBox("Line Numbers")
        self.line_numbers_checkbox.setToolTip("Show line numbers and highlight current line")
        self.line_numbers_checkbox.setChecked(True)  # Default to checked
        self.line_numbers_checkbox.stateChanged.connect(self.toggle_line_numbers)
        toolbar_row3.addWidget(self.line_numbers_checkbox)

        # Monospace checkbox
        self.monospace_checkbox = QCheckBox("Monospace")
        self.monospace_checkbox.setToolTip("Use monospace font (Consolas) for editing")
        self.monospace_checkbox.setChecked(False)  # Default to unchecked (use system default)
        self.monospace_checkbox.stateChanged.connect(self.toggle_monospace_font)
        toolbar_row3.addWidget(self.monospace_checkbox)

        # Add stretch to push buttons to the left
        toolbar_row3.addStretch()

        toolbar_main_layout.addLayout(toolbar_row3)

        # Add divider after third row
        divider3 = QFrame()
        divider3.setFrameShape(QFrame.Shape.HLine)
        divider3.setStyleSheet("background-color: #888888; min-height: 1px; max-height: 1px;")
        toolbar_main_layout.addWidget(divider3)

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
        if self.tab_group_manager.current_tabs_file:
            folder = os.path.dirname(self.tab_group_manager.current_tabs_file)
            if os.path.exists(folder):
                return folder

        # Default to first tab's folder
        return self.get_default_file_folder()

    def new_file(self):
        """Create a new file tab - prompts for save location"""
        default_folder = self.get_default_file_folder()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New File",
            os.path.join(default_folder, "untitled.md"),
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            # Convert to absolute path
            file_path = os.path.abspath(file_path)

            # Update last folder
            self.last_file_folder = os.path.dirname(file_path)

            # Check if file already exists and is open
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

            # Create new tab with the file path
            tab = TextEditorTab()
            tab.file_path = file_path
            tab.save_file()  # Create the empty file
            self.content_stack.addWidget(tab)
            self.tab_list.add_tab(tab)
            self.apply_markdown_to_tab(tab)
            self.apply_line_numbers_to_tab(tab)
            self.apply_monospace_to_tab(tab)
            self._watch_file(file_path)
            self.switch_to_tab(tab)
            # Mark tab group as modified since a new tab was added
            self.mark_tabs_metadata_modified()

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
                self.apply_markdown_to_tab(tab)
                self.apply_line_numbers_to_tab(tab)
                self.apply_monospace_to_tab(tab)
                self._watch_file(file_path)
                self.switch_to_tab(tab)
                # Mark tab group as modified since a new tab was added
                self.mark_tabs_metadata_modified()
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
            # Update the text edit reference and refresh tab list
            self.find_replace_dialog.update_current_tab(current_tab)
            self.find_replace_dialog.refresh_tab_list()

        # Show dialog
        self.find_replace_dialog.show()
        self.find_replace_dialog.raise_()
        self.find_replace_dialog.activateWindow()

    def show_document_stats(self):
        """Show document statistics dialog (Ctrl+I)"""
        import re

        current_tab = self.get_current_tab()
        if not current_tab:
            QMessageBox.information(self, "No File", "Please open a file first.")
            return

        text = current_tab.get_content()

        # Calculate statistics
        char_count = len(text)
        char_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

        # Word count - split on whitespace
        words = text.split()
        word_count = len(words)

        # Line count
        lines = text.split('\n')
        line_count = len(lines)

        # Paragraph count - separated by blank lines
        paragraphs = re.split(r'\n\s*\n', text.strip())
        paragraph_count = len([p for p in paragraphs if p.strip()])

        # Sentence count - split on . ! ? followed by space or end
        sentences = re.split(r'[.!?]+(?:\s|$)', text)
        sentence_count = len([s for s in sentences if s.strip()])

        # Get file name
        file_name = os.path.basename(current_tab.file_path) if current_tab.file_path else "Untitled"

        # Build message
        stats_message = f"""<b>{file_name}</b><br><br>
<table>
<tr><td><b>Characters:</b></td><td align="right">{char_count:,}</td></tr>
<tr><td><b>Characters (no spaces):</b></td><td align="right">{char_no_spaces:,}</td></tr>
<tr><td><b>Words:</b></td><td align="right">{word_count:,}</td></tr>
<tr><td><b>Lines:</b></td><td align="right">{line_count:,}</td></tr>
<tr><td><b>Paragraphs:</b></td><td align="right">{paragraph_count:,}</td></tr>
<tr><td><b>Sentences:</b></td><td align="right">{sentence_count:,}</td></tr>
</table>"""

        msg = QMessageBox(self)
        msg.setWindowTitle("Document Statistics")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(stats_message)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

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
            self._saving_files.add(tab.file_path)
            tab.save_file()
            self.tab_list.update_tab_display(tab)
            # Update save buttons now that the file is saved
            self._update_save_buttons()
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

                self._saving_files.add(file_path)
                tab.save_file(file_path)
                self._watch_file(file_path)  # Start watching the new file
                self.tab_list.update_tab_display(tab)
                # Update save buttons now that the file is saved
                self._update_save_buttons()

    def save_all(self):
        """Save all modified files and the group"""
        saved_count = 0

        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified:
                if widget.file_path:
                    self._saving_files.add(widget.file_path)
                    widget.save_file()
                    self.tab_list.update_tab_display(widget)
                    saved_count += 1

        # Also save the group if there's a location
        if self.tab_group_manager.current_tabs_file:
            self.save_tabs(self.tab_group_manager.current_tabs_file)

        # Update last saved timestamp if anything was saved
        if saved_count > 0:
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M")
            self.last_saved_all_label.setText(f"Saved {current_time}")
            self.last_saved_all_label.setVisible(True)

        # Update button appearances
        self._update_save_buttons()

    def _update_save_buttons(self):
        """Update both Save and Save All button appearances after any save-related state change."""
        self.update_save_button()
        self.update_save_all_button()

    def update_save_button(self):
        """Update the Save button appearance based on whether current tab has unsaved changes"""
        current_tab = self.get_current_tab()
        has_unsaved = current_tab and current_tab.is_modified

        if has_unsaved:
            self.save_btn.setStyleSheet(MODIFIED_BUTTON_STYLE)
            self.save_btn.setText("⚠️ Save")
        else:
            self.save_btn.setStyleSheet(self.default_button_style)
            self.save_btn.setText("💾 Save")

    def update_save_all_button(self):
        """Update the Save All Changes button appearance based on whether there are unsaved changes"""
        # Check for unsaved file changes
        has_unsaved_files = False
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified and widget.file_path:
                has_unsaved_files = True
                break

        # Check for unsaved group changes
        has_unsaved_group = (self.tab_group_manager.current_tabs_file or self.tab_group_manager.tab_group_name) and self._has_tab_state_changed()

        has_unsaved = has_unsaved_files or has_unsaved_group

        if has_unsaved:
            self.save_all_btn.setStyleSheet(MODIFIED_BUTTON_STYLE)
            self.save_all_btn.setText("⚠️ Save All Changes")
        else:
            self.save_all_btn.setStyleSheet(self.default_button_style)
            self.save_all_btn.setText("💾 Save All Changes")

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

        # Remove from file watcher
        if widget.file_path:
            self._unwatch_file(widget.file_path)

        # Remove from tab list and content stack
        self.tab_list.remove_tab(widget)
        self.content_stack.removeWidget(widget)
        widget.deleteLater()
        # Mark tab group as modified since a tab was closed
        self.mark_tabs_metadata_modified()

    def _watch_file(self, file_path):
        """Add a file to the file system watcher"""
        if file_path and os.path.exists(file_path):
            if file_path not in self.file_watcher.files():
                self.file_watcher.addPath(file_path)

    def _unwatch_file(self, file_path):
        """Remove a file from the file system watcher"""
        if file_path and file_path in self.file_watcher.files():
            self.file_watcher.removePath(file_path)

    def _on_file_changed(self, file_path):
        """Handle file changed notification from file system watcher"""
        # Ignore changes from our own save operations
        if file_path in self._saving_files:
            self._saving_files.discard(file_path)
            # Re-add to watcher (file changes remove it on some systems)
            self._watch_file(file_path)
            return

        # Avoid duplicate prompts
        if file_path in self._pending_reload_files:
            return

        # Find the tab for this file
        tab = None
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.file_path == file_path:
                tab = widget
                break

        if not tab:
            return

        # Check if the file still exists
        if not os.path.exists(file_path):
            # File was deleted
            QMessageBox.warning(
                self,
                "File Deleted",
                f"'{os.path.basename(file_path)}' has been deleted externally.\n"
                "The file will be marked as unsaved."
            )
            tab.is_modified = True
            self.tab_list.update_tab_display(tab)
            self._unwatch_file(file_path)
            return

        # File was modified - prompt to reload
        self._pending_reload_files.add(file_path)
        file_name = os.path.basename(file_path)

        reply = QMessageBox.question(
            self,
            "File Changed",
            f"'{file_name}' has been modified externally.\n\n"
            "Do you want to reload it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        self._pending_reload_files.discard(file_path)

        if reply == QMessageBox.StandardButton.Yes:
            # Reload the file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tab._saved_content = content
                tab.text_edit.setPlainText(content)
                tab.is_modified = False
                self.tab_list.update_tab_display(tab)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reload file:\n{str(e)}")

        # Re-add to watcher (file changes remove it on some systems)
        self._watch_file(file_path)

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
            # Update visual selection in tab list (without calling select_tab to avoid recursion)
            for tab_item in self.tab_list.tab_items:
                tab_item.set_selected(tab_item.editor_tab == tab)
            # Notify Find & Replace dialog about the tab switch
            if self.find_replace_dialog and self.find_replace_dialog.isVisible():
                self.find_replace_dialog.update_current_tab(tab)
            # Update Save button highlighting
            self.update_save_button()

    def set_tab_view_mode(self, mode):
        """Set the view mode for the tab list"""
        # Update button states
        self.minimize_btn.setChecked(mode == 'minimized')
        self.normal_btn.setChecked(mode == 'normal')
        self.maximize_btn.setChecked(mode == 'maximized')

        # Update the tab list view mode
        self.tab_list.set_view_mode(mode)

    def toggle_markdown_rendering(self, state):
        """Toggle markdown syntax highlighting on all tabs.

        Note: No need to save/restore is_modified state because TextEditorTab
        now compares actual text content against a saved baseline. Formatting
        changes from the highlighter don't modify text content.
        """
        enabled = state == Qt.CheckState.Checked.value
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab):
                widget.text_edit.set_markdown_highlighting(enabled)

    def apply_markdown_to_tab(self, tab):
        """Apply current markdown rendering setting to a tab.

        Note: No need to save/restore is_modified state because TextEditorTab
        now compares actual text content against a saved baseline.
        """
        if hasattr(self, 'render_markdown_checkbox'):
            enabled = self.render_markdown_checkbox.isChecked()
            tab.text_edit.set_markdown_highlighting(enabled)

    def toggle_line_numbers(self, state):
        """Toggle line numbers and current line highlighting on all tabs."""
        enabled = state == Qt.CheckState.Checked.value
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab):
                widget.text_edit.set_line_numbers_visible(enabled)

    def apply_line_numbers_to_tab(self, tab):
        """Apply current line numbers setting to a tab."""
        if hasattr(self, 'line_numbers_checkbox'):
            enabled = self.line_numbers_checkbox.isChecked()
            tab.text_edit.set_line_numbers_visible(enabled)

    def toggle_monospace_font(self, state):
        """Toggle monospace font on all tabs."""
        enabled = state == Qt.CheckState.Checked.value
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab):
                widget.text_edit.set_monospace_font(enabled)

    def apply_monospace_to_tab(self, tab):
        """Apply current monospace font setting to a tab."""
        if hasattr(self, 'monospace_checkbox'):
            enabled = self.monospace_checkbox.isChecked()
            tab.text_edit.set_monospace_font(enabled)

    def edit_selected_emoji(self):
        """Edit the emoji and display name for the selected tab"""
        # Find the selected tab
        selected_tab_item = None
        for tab_item in self.tab_list.tab_items:
            if tab_item.is_selected:
                selected_tab_item = tab_item
                break

        if not selected_tab_item:
            QMessageBox.information(self, "No Tab Selected", "Please select a tab first.")
            return

        dialog = EditTabDialog(selected_tab_item, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            icon, emoji, display_name, pinned = dialog.get_results()

            # Update custom icon if changed
            if icon != selected_tab_item.custom_icon:
                selected_tab_item.custom_icon = icon

            # Update emoji
            if emoji and emoji != selected_tab_item.get_emoji():
                selected_tab_item.custom_emoji = emoji
            elif not emoji:
                selected_tab_item.custom_emoji = None

            # Update display name
            selected_tab_item.custom_display_name = display_name

            # Update pin status if changed
            if pinned != selected_tab_item.editor_tab.is_pinned:
                self.toggle_pin(selected_tab_item.editor_tab)

            selected_tab_item.update_display()
            self.mark_tabs_metadata_modified()

    def get_current_tab(self):
        """Get the currently active tab"""
        current_widget = self.content_stack.currentWidget()
        if isinstance(current_widget, TextEditorTab):
            return current_widget
        return None

    def _get_current_tab_state(self):
        """Get a snapshot of the current tab state for comparison."""
        state = {
            'tab_group_name': self.tab_group_manager.tab_group_name,
            'tabs': []
        }
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.file_path:
                tab_data = {
                    'path': widget.file_path,
                    'pinned': widget.is_pinned
                }
                # Find matching tab item for icon/emoji/display name
                for tab_item in self.tab_list.tab_items:
                    if tab_item.editor_tab == widget:
                        tab_data['icon'] = tab_item.custom_icon
                        tab_data['emoji'] = tab_item.custom_emoji
                        tab_data['display_name'] = tab_item.custom_display_name
                        break
                state['tabs'].append(tab_data)
        return state

    def _set_baseline_tab_state(self):
        """Set the baseline state to compare against."""
        self.tab_group_manager.set_baseline_state(self._get_current_tab_state())

    def _has_tab_state_changed(self):
        """Check if the current tab state differs from the baseline."""
        return self.tab_group_manager.has_state_changed(self._get_current_tab_state())

    def update_save_group_button(self):
        """Update the Save Group button appearance based on whether state has changed."""
        # Only show as modified if there's a tabs file or tab group name to save to
        has_changes = (self.tab_group_manager.current_tabs_file or self.tab_group_manager.tab_group_name) and self._has_tab_state_changed()

        if has_changes:
            self.save_group_btn.setText("⚠️ Save Group")
            self.save_group_btn.setStyleSheet(MODIFIED_BUTTON_STYLE)
        else:
            self.save_group_btn.setText("💾 Save Group")
            self.save_group_btn.setStyleSheet(self.default_button_style)

    def mark_tabs_metadata_modified(self):
        """Called when tab metadata may have changed - updates button state."""
        self.update_save_group_button()

    def update_tab_title(self, tab):
        """Update the title of a tab"""
        self.tab_list.update_tab_display(tab)
        # Update Save buttons when any tab changes
        self._update_save_buttons()

    def update_window_title(self):
        """Update the window title based on tab group name or current tabs file"""
        self.setWindowTitle(self.tab_group_manager.get_window_title())

    def edit_tabs_dialog(self):
        """Show dialog to edit tab group name"""
        dialog = EditGroupDialog(self.tab_group_manager.tab_group_name, self.tab_group_manager.current_tabs_file, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.tab_group_manager.tab_group_name = dialog.get_result()
            self.update_window_title()
            self.mark_tabs_metadata_modified()

    def show_about_dialog(self):
        """Show the About dialog with keyboard shortcuts and info"""
        dialog = AboutDialog(self)
        dialog.exec()

    def new_group_dialog(self):
        """Create a new tab group - closes all tabs and prompts for save location"""
        # Check for unsaved changes first
        if not self._check_unsaved_before_group_change():
            return

        # Prompt for save location for the new group
        default_folder = self.get_default_tabs_folder()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Create New Group",
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

            # Close all existing tabs
            while self.content_stack.count() > 0:
                widget = self.content_stack.widget(0)
                if hasattr(widget, 'file_path') and widget.file_path:
                    self._unwatch_file(widget.file_path)
                self.content_stack.removeWidget(widget)
                widget.deleteLater()
            self.tab_list.clear_all_tabs()

            # Set the new group location
            self.tab_group_manager.current_tabs_file = file_path
            self.tab_group_manager.tab_group_name = None

            # Update window title
            self.update_window_title()

            # Save the empty group
            self.save_tabs(file_path)

    def save_group(self):
        """Save tab group to current location without prompting"""
        if self.tab_group_manager.current_tabs_file:
            # We have a location, save directly
            self.save_tabs(self.tab_group_manager.current_tabs_file)
        else:
            # No location yet, prompt for one
            self.save_group_as_dialog()

    def save_group_as_dialog(self):
        """Show dialog to save tab group to a new location"""
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
            message = "The following documents will be excluded from the saved group:\n\n"
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
            "Save Group As",
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
        # Extract tabs data from widgets
        tabs_data = get_tabs_data_from_widgets(
            self.content_stack, self.tab_list, TextEditorTab
        )

        # Determine current tab index
        current_tab = self.get_current_tab()
        current_index = 0
        for i, tab_data in enumerate(tabs_data):
            # Find widget with matching path
            for j in range(self.content_stack.count()):
                widget = self.content_stack.widget(j)
                if isinstance(widget, TextEditorTab) and widget.file_path == tab_data['path']:
                    if widget == current_tab:
                        current_index = i
                    break

        # Save using the manager
        if self.tab_group_manager.save_tabs_to_file(tabs_file_path, tabs_data, current_index):
            # Update window title
            self.update_window_title()

            # Update last saved timestamp
            timestamp = self.tab_group_manager.get_last_saved_timestamp()
            self.last_saved_label.setText(f"Saved group {timestamp}")
            self.last_saved_label.setVisible(True)

            # Set baseline state and update button appearance
            self._set_baseline_tab_state()
            self.update_save_group_button()

            # Update history combo
            self.update_history_combo()

    def _check_unsaved_before_group_change(self):
        """Check for unsaved changes before switching groups. Returns True if safe to proceed."""
        # Check for unsaved file changes
        unsaved_files = []
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified:
                if widget.file_path:
                    unsaved_files.append(os.path.basename(widget.file_path))
                else:
                    unsaved_files.append("Untitled")

        # Check for unsaved group changes
        has_group_changes = (self.tab_group_manager.current_tabs_file or self.tab_group_manager.tab_group_name) and self._has_tab_state_changed()

        if not unsaved_files and not has_group_changes:
            return True  # No unsaved changes, safe to proceed

        group_name = self.tab_group_manager.tab_group_name or os.path.basename(self.tab_group_manager.current_tabs_file or "current group")
        dialog = GroupChangeWarningDialog(unsaved_files, has_group_changes, group_name, self)
        result = dialog.exec()

        if result == GroupChangeWarningDialog.CANCEL:
            return False
        elif result == GroupChangeWarningDialog.SAVE_ALL:
            self.save_all()
        # DONT_SAVE - just proceed

        return True

    def load_tabs_dialog(self):
        """Show dialog to load a tab group"""
        # Check for unsaved changes first
        if not self._check_unsaved_before_group_change():
            return

        default_folder = self.get_default_tabs_folder()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Group",
            default_folder,
            "Tabs Files (*.tabs)"
        )

        if file_path:
            # Update last tabs folder
            self.last_tabs_folder = os.path.dirname(file_path)
            self.load_tabs(file_path)

    def load_tabs(self, tabs_file_path):
        """Load tabs from an XML file"""
        # Load data using the manager
        tabs_data, current_index, group_name = self.tab_group_manager.load_tabs_from_file(tabs_file_path)

        if tabs_data is None:
            QMessageBox.critical(self, "Error", f"Failed to load tabs from:\n{tabs_file_path}")
            return

        # Close all existing tabs
        while self.content_stack.count() > 0:
            widget = self.content_stack.widget(0)
            if hasattr(widget, 'file_path') and widget.file_path:
                self._unwatch_file(widget.file_path)
            self.content_stack.removeWidget(widget)
            widget.deleteLater()
        self.tab_list.clear_all_tabs()

        loaded_tabs = []

        # Create widgets for each tab
        for tab_data in tabs_data:
            file_path = tab_data['path']

            # Only load tabs for existing files
            if not tab_data.get('exists', os.path.exists(file_path)):
                continue

            tab = TextEditorTab(file_path)
            tab.is_pinned = tab_data.get('pinned', False)

            # Add to content stack and tab list
            self.content_stack.addWidget(tab)
            tab_item = self.tab_list.add_tab(tab)
            self.apply_markdown_to_tab(tab)
            self.apply_line_numbers_to_tab(tab)
            self.apply_monospace_to_tab(tab)
            self._watch_file(file_path)

            # Set custom icon, emoji and display name if they were saved
            custom_icon = tab_data.get('icon')
            custom_emoji = tab_data.get('emoji')
            custom_display_name = tab_data.get('display_name')

            if custom_icon:
                tab_item.custom_icon = custom_icon
            if custom_emoji:
                tab_item.custom_emoji = custom_emoji
            if custom_display_name:
                tab_item.custom_display_name = custom_display_name
            if custom_icon or custom_emoji or custom_display_name:
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

        # Update window title
        self.update_window_title()

        # Set baseline state for change tracking
        self._set_baseline_tab_state()

        # Update history combo
        self.update_history_combo()

    def add_to_recent_groups(self, tabs_file_path):
        """Add a tabs file to the recent groups history"""
        self.tab_group_manager.add_to_recent_groups(tabs_file_path)
        self.update_history_combo()

    def update_history_combo(self):
        """Update the history combo box with recent groups"""
        # Block signals to prevent triggering selection handler
        self.history_combo.blockSignals(True)

        self.history_combo.clear()

        if self.tab_group_manager.recent_groups:
            self.history_combo.setEnabled(True)
            for path in self.tab_group_manager.recent_groups:
                # Show just the filename without extension
                filename = os.path.basename(path)
                if filename.endswith('.tabs'):
                    display_name = filename[:-5]
                else:
                    display_name = filename
                self.history_combo.addItem(display_name, path)
        else:
            self.history_combo.addItem("(no recent groups)")
            self.history_combo.setEnabled(False)

        # Reset to first item (or -1 for placeholder)
        self.history_combo.setCurrentIndex(0 if self.tab_group_manager.recent_groups else -1)

        self.history_combo.blockSignals(False)

    def _on_history_selected(self, index):
        """Handle selection from history dropdown"""
        if index < 0 or not self.tab_group_manager.recent_groups:
            return

        path = self.history_combo.itemData(index)
        if path and os.path.exists(path):
            # Don't reload if it's the current file
            if path != self.tab_group_manager.current_tabs_file:
                # Check for unsaved changes first
                if not self._check_unsaved_before_group_change():
                    # User cancelled - reset combo to current group
                    self.update_history_combo()
                    return
                self.load_tabs(path)
        elif path:
            # File doesn't exist anymore - remove from history
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The group file no longer exists:\n{path}\n\nIt will be removed from history."
            )
            self.tab_group_manager.recent_groups.remove(path)
            self.update_history_combo()

    def save_settings(self):
        """Save window settings and current session"""
        # Get current tab index
        current_tab = self.get_current_tab()
        tabs_data = get_tabs_data_for_session(self.content_stack, self.tab_list, TextEditorTab)
        current_index = 0
        for i, tab_data in enumerate(tabs_data):
            for j in range(self.content_stack.count()):
                widget = self.content_stack.widget(j)
                if isinstance(widget, TextEditorTab) and widget.file_path == tab_data['path']:
                    if widget == current_tab:
                        current_index = i
                    break

        settings = {
            'geometry': {
                'x': self.x(),
                'y': self.y(),
                'width': self.width(),
                'height': self.height()
            },
            'last_file_folder': self.last_file_folder,
            'last_tabs_folder': self.last_tabs_folder,
            'current_tabs_file': self.tab_group_manager.current_tabs_file,
            'view_mode': self.tab_list.view_mode,
            'render_markdown': self.render_markdown_checkbox.isChecked(),
            'line_numbers': self.line_numbers_checkbox.isChecked(),
            'monospace': self.monospace_checkbox.isChecked(),
            'recent_groups': self.tab_group_manager.recent_groups,
            'auto_session': self.settings_manager.build_auto_session(
                tabs_data, current_index, self.tab_group_manager.tab_group_name
            )
        }

        self.settings_manager.save(settings)

    def load_settings(self):
        """Load window settings"""
        settings = self.settings_manager.load()
        if not settings:
            return

        # Restore geometry with screen validation
        if 'geometry' in settings:
            screen = QGuiApplication.primaryScreen()
            geo = self.settings_manager.validate_geometry(
                settings['geometry'],
                screen.availableGeometry()
            )
            if geo:
                self.setGeometry(geo['x'], geo['y'], geo['width'], geo['height'])

        # Restore last folders
        self.last_file_folder = self.settings_manager.get('last_file_folder')
        self.last_tabs_folder = self.settings_manager.get('last_tabs_folder')
        self.tab_group_manager.current_tabs_file = self.settings_manager.get('current_tabs_file')

        # Restore view mode
        self.set_tab_view_mode(self.settings_manager.get('view_mode', 'normal'))

        # Restore preferences
        self.render_markdown_checkbox.setChecked(self.settings_manager.get('render_markdown', True))
        self.line_numbers_checkbox.setChecked(self.settings_manager.get('line_numbers', True))
        self.monospace_checkbox.setChecked(self.settings_manager.get('monospace', False))

        # Restore recent groups history
        self.tab_group_manager.recent_groups = self.settings_manager.get('recent_groups', [])
        self.tab_group_manager.filter_nonexistent_groups()
        self.update_history_combo()

        if self.tab_group_manager.current_tabs_file:
            self.update_window_title()

    def load_auto_session(self):
        """Load auto-saved session"""
        tabs_data, current_index, tab_group_name = self.settings_manager.get_auto_session()
        if not tabs_data:
            return

        loaded_tabs = []

        # Restore tab group name if present
        self.tab_group_manager.tab_group_name = tab_group_name
        if tab_group_name:
            self.update_window_title()

        # Load each tab
        for tab_data in tabs_data:
            file_path = tab_data.get('path')
            if not file_path or not os.path.exists(file_path):
                continue

            tab = TextEditorTab(file_path)
            tab.is_pinned = tab_data.get('pinned', False)

            # Add to content stack and tab list
            self.content_stack.addWidget(tab)
            tab_item = self.tab_list.add_tab(tab)
            self.apply_markdown_to_tab(tab)
            self.apply_line_numbers_to_tab(tab)
            self.apply_monospace_to_tab(tab)
            self._watch_file(file_path)

            # Set custom icon, emoji and display name if they were saved
            custom_icon = tab_data.get('icon')
            custom_emoji = tab_data.get('emoji')
            custom_display_name = tab_data.get('display_name')

            if custom_icon:
                tab_item.custom_icon = custom_icon
            if custom_emoji:
                tab_item.custom_emoji = custom_emoji
            if custom_display_name:
                tab_item.custom_display_name = custom_display_name
            if custom_icon or custom_emoji or custom_display_name:
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

        # Set baseline state if there's a tabs file to track changes against
        if self.tab_group_manager.current_tabs_file:
            self._set_baseline_tab_state()

    def closeEvent(self, event):
        """Handle window close event"""
        # Disconnect file watcher immediately to prevent callbacks during close
        try:
            self.file_watcher.fileChanged.disconnect(self._on_file_changed)
        except TypeError:
            pass  # Already disconnected
        # Remove all watched files
        watched_files = self.file_watcher.files()
        if watched_files:
            self.file_watcher.removePaths(watched_files)

        # Check for unsaved changes in all tabs
        modified_tabs = []
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if isinstance(widget, TextEditorTab) and widget.is_modified:
                file_name = os.path.basename(widget.file_path) if widget.file_path else "Untitled"
                modified_tabs.append(file_name)

        if modified_tabs:
            dialog = UnsavedChangesDialog(modified_tabs, self)
            result = dialog.exec()

            if result == UnsavedChangesDialog.CANCEL:
                event.ignore()
                return
            elif result == UnsavedChangesDialog.SAVE_AND_EXIT:
                # Save all files that can be saved
                for i in range(self.content_stack.count()):
                    widget = self.content_stack.widget(i)
                    if isinstance(widget, TextEditorTab) and widget.is_modified and widget.file_path:
                        widget.save_file()
            # EXIT_WITHOUT_SAVING - just continue

        # Check for unsaved tab group changes
        has_tab_changes = (self.tab_group_manager.current_tabs_file or self.tab_group_manager.tab_group_name) and self._has_tab_state_changed()
        if has_tab_changes:
            # Determine tab group name for display
            group_name = self.tab_group_manager.tab_group_name
            if not group_name and self.tab_group_manager.current_tabs_file:
                filename = os.path.basename(self.tab_group_manager.current_tabs_file)
                group_name = filename[:-5] if filename.endswith('.tabs') else filename
            if not group_name:
                group_name = "Current Tab Group"

            dialog = UnsavedGroupDialog(group_name, self)
            result = dialog.exec()

            if result == UnsavedGroupDialog.CANCEL:
                event.ignore()
                return
            elif result == UnsavedGroupDialog.SAVE_GROUP:
                if self.tab_group_manager.current_tabs_file:
                    self.save_tabs(self.tab_group_manager.current_tabs_file)
                else:
                    self.save_group_as_dialog()
                    # Check if save was cancelled (state still differs from baseline)
                    if self._has_tab_state_changed():
                        event.ignore()
                        return
            # EXIT_WITHOUT_SAVING - just continue

        # Save settings and session before closing
        self.save_settings()
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)

    # Set application icon (for taskbar)
    icon_path = os.path.join(get_resource_dir(), 'favicon.ico')
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

    # Install global exception handler to prevent crashes from losing unsaved work
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions with a dialog instead of crashing"""
        import traceback

        # Format the error message
        error_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        error_text = ''.join(error_lines)

        # Log to console
        print(f"Unhandled exception:\n{error_text}", file=sys.stderr)

        # Show error dialog
        msg = QMessageBox(window)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText("An unexpected error occurred.")
        msg.setInformativeText(
            "The application encountered an error but hasn't closed.\n"
            "You can try to save your work before closing."
        )
        msg.setDetailedText(error_text)
        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Close
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Ok)

        result = msg.exec()
        if result == QMessageBox.StandardButton.Close:
            # User chose to close - trigger normal close which will prompt for unsaved changes
            window.close()

    sys.excepthook = handle_exception

    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
