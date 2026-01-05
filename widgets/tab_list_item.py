"""
Visual representation of a tab in the sidebar.
Displays file name, emoji, buttons, and handles drag-and-drop.
"""

import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog, QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, QSize, QPoint, QDateTime
from PyQt6.QtGui import QFont, QMouseEvent, QFontMetrics, QPixmap

from constants import TAB_WIDTH_MINIMIZED, TAB_WIDTH_NORMAL, TAB_WIDTH_MAXIMIZED
from windows.icon_editor import load_icon_pixmap, IconEditorDialog


class TabListItem(QFrame):
    """A single tab item in the sidebar list"""

    def __init__(self, editor_tab, parent=None):
        super().__init__(parent)
        self.editor_tab = editor_tab
        self.view_mode = 'normal'  # 'minimized', 'normal', 'maximized'
        self.is_selected = False
        self.custom_emoji = None  # Custom emoji override
        self.custom_icon = None   # Custom icon filename (stored in icons/ folder)
        self.custom_display_name = None  # Custom display name override
        self.drag_start_position = None  # For drag and drop

        # Set frame properties
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setLineWidth(2)

        # Create layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(2)

        # Top row: emoji + filename + buttons
        self.top_row = QHBoxLayout()
        self.top_row.setSpacing(4)

        # Emoji label
        self.emoji_label = QLabel()
        emoji_font = QFont()
        emoji_font.setPointSize(18)  # Larger to stand out more
        emoji_font.setBold(True)
        self.emoji_label.setFont(emoji_font)
        self.emoji_label.setFixedWidth(35)  # Fixed width to accommodate emojis
        self.emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the emoji
        self.top_row.addWidget(self.emoji_label)

        # Filename label
        self.filename_label = QLabel()
        filename_font = QFont()
        filename_font.setPointSize(10)
        self.filename_label.setFont(filename_font)
        self.top_row.addWidget(self.filename_label, 1)  # Stretch

        # Button container
        button_container = QHBoxLayout()
        button_container.setSpacing(5)

        # Save button
        self.save_btn = QPushButton("💾")
        self.save_btn.setMaximumSize(QSize(20, 20))
        self.save_btn.setToolTip("Save file")
        self.save_btn.setStyleSheet("QPushButton { border: none; padding: 0; }")
        button_container.addWidget(self.save_btn)

        # Pin button
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setMaximumSize(QSize(20, 20))
        self.pin_btn.setToolTip("Pin tab")
        self.pin_btn.setStyleSheet("QPushButton { border: none; padding: 0; }")
        button_container.addWidget(self.pin_btn)

        # Close button
        self.close_btn = QPushButton("✖")
        self.close_btn.setMaximumSize(QSize(20, 20))
        self.close_btn.setToolTip("Close tab")
        self.close_btn.setStyleSheet("QPushButton { border: none; padding: 0; }")
        button_container.addWidget(self.close_btn)

        self.top_row.addLayout(button_container)
        self.main_layout.addLayout(self.top_row)

        # Last modified label (only shown in maximized mode)
        self.modified_label = QLabel()
        modified_font = QFont()
        modified_font.setPointSize(8)
        self.modified_label.setFont(modified_font)
        self.modified_label.setStyleSheet("color: #666666;")
        self.main_layout.addWidget(self.modified_label)

        self.setLayout(self.main_layout)

        # Set object name for styling
        self.setObjectName("TabListItem")

        # Make widget clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Update initial display
        self.update_display()

    def get_emoji(self):
        """Get emoji/character prefix for this tab"""
        # Use custom emoji if set
        if self.custom_emoji:
            return self.custom_emoji

        if self.editor_tab.file_path:
            filename = os.path.basename(self.editor_tab.file_path)
            if filename:
                return filename[0].upper()
        return "📄"

    def get_filename(self):
        """Get filename for display"""
        # Use custom display name if set
        if self.custom_display_name:
            return self.custom_display_name

        if self.editor_tab.file_path:
            filename = os.path.basename(self.editor_tab.file_path)
            # Remove file extension
            name_without_ext = os.path.splitext(filename)[0]
            # Remove leading underscores
            display_name = name_without_ext.lstrip('_')
            # If everything was removed, show at least something
            return display_name if display_name else filename
        return "Untitled"

    def get_last_modified(self):
        """Get last modified time for file"""
        if self.editor_tab.file_path and os.path.exists(self.editor_tab.file_path):
            mtime = os.path.getmtime(self.editor_tab.file_path)
            dt = QDateTime.fromSecsSinceEpoch(int(mtime))
            return dt.toString("MMM d, yyyy h:mm AP")
        return ""

    def set_view_mode(self, mode):
        """Set the view mode: 'minimized', 'normal', or 'maximized'"""
        self.view_mode = mode
        self.update_display()

    def get_elided_filename(self, filename, max_width):
        """Get filename elided to fit within max_width pixels"""
        font_metrics = QFontMetrics(self.filename_label.font())
        return font_metrics.elidedText(filename, Qt.TextElideMode.ElideRight, max_width)

    def update_display(self):
        """Update the display based on current view mode and state"""
        emoji = self.get_emoji()
        filename = self.get_filename()

        # Update emoji/icon display
        if self.custom_icon:
            # Try to load and display custom icon
            pixmap = load_icon_pixmap(self.custom_icon)
            if pixmap:
                # Scale to fit the label (32x32 icon in 35px label)
                scaled = pixmap.scaled(
                    32, 32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.emoji_label.setPixmap(scaled)
            else:
                # Icon file not found, fall back to emoji
                self.emoji_label.setText(emoji)
        else:
            # Clear any pixmap and show emoji text
            self.emoji_label.setPixmap(QPixmap())  # Clear pixmap
            self.emoji_label.setText(emoji)

        # Update filename visibility
        if self.view_mode == 'minimized':
            self.filename_label.setVisible(False)
            self.save_btn.setVisible(False)
            self.pin_btn.setVisible(False)
            self.close_btn.setVisible(False)
            self.modified_label.setVisible(False)
        elif self.view_mode == 'normal':
            self.filename_label.setVisible(True)
            # Calculate available width: total - emoji - buttons - margins - spacing
            # emoji: 35px, buttons: 3*20px + 2*5px spacing = 70px, margins: 16px, extra spacing: ~20px
            available_width = TAB_WIDTH_NORMAL - 35 - 70 - 16 - 20
            elided = self.get_elided_filename(filename, available_width)
            self.filename_label.setText(elided)
            # Show full filename in tooltip if truncated
            self.filename_label.setToolTip(filename if elided != filename else "")
            self.save_btn.setVisible(True)
            self.pin_btn.setVisible(True)
            self.close_btn.setVisible(True)
            self.modified_label.setVisible(False)
        else:  # maximized
            self.filename_label.setVisible(True)
            # More space available in maximized mode
            available_width = TAB_WIDTH_MAXIMIZED - 35 - 70 - 16 - 20
            elided = self.get_elided_filename(filename, available_width)
            self.filename_label.setText(elided)
            # Show full filename in tooltip if truncated
            self.filename_label.setToolTip(filename if elided != filename else "")
            self.save_btn.setVisible(True)
            self.pin_btn.setVisible(True)
            self.close_btn.setVisible(True)
            self.modified_label.setVisible(True)
            self.modified_label.setText(self.get_last_modified())

        # Update save button appearance
        if self.editor_tab.is_modified:
            self.save_btn.setText("💾")
            self.save_btn.setStyleSheet("QPushButton { border: none; padding: 0; color: red; }")
        else:
            self.save_btn.setText("✔")
            self.save_btn.setStyleSheet("QPushButton { border: none; padding: 0; color: green; }")

        # Update pin button appearance
        if self.editor_tab.is_pinned:
            self.pin_btn.setText("📍")
        else:
            self.pin_btn.setText("📌")

        # Update selection appearance with border and hover effect
        # Choose background color based on modified state
        if self.editor_tab.is_modified:
            bg_color = "#FFCDD2"  # Light red for modified
            hover_bg_color = "#EF9A9A"  # Slightly darker red on hover
        else:
            bg_color = "#F5F5F5"  # Light grey for unmodified
            hover_bg_color = "#E3F2FD"  # Light blue on hover

        if self.is_selected:
            # Selected tab - use blue theme but show modified state with border
            border_color = "#EF5350" if self.editor_tab.is_modified else "#2196F3"
            self.setStyleSheet(f"""
                QFrame#TabListItem {{
                    background-color: #BBDEFB;
                    border: 2px solid {border_color};
                    border-radius: 4px;
                }}
                QFrame#TabListItem:hover {{
                    border: 3px solid {border_color};
                    background-color: #BBDEFB;
                }}
                QFrame#TabListItem QLabel {{
                    background-color: transparent;
                }}
                QFrame#TabListItem QPushButton {{
                    background-color: transparent;
                }}
            """)
        else:
            # Unselected tab - show modified state with background color
            border_color = "#E57373" if self.editor_tab.is_modified else "#E0E0E0"
            self.setStyleSheet(f"""
                QFrame#TabListItem {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 4px;
                }}
                QFrame#TabListItem:hover {{
                    border: 2px solid #90CAF9;
                    background-color: {hover_bg_color};
                }}
                QFrame#TabListItem QLabel {{
                    background-color: transparent;
                }}
                QFrame#TabListItem QPushButton {{
                    background-color: transparent;
                }}
            """)

        # Adjust widget size based on view mode
        if self.view_mode == 'minimized':
            self.setFixedHeight(50)
        elif self.view_mode == 'normal':
            self.setFixedHeight(50)
        else:  # maximized
            self.setFixedHeight(70)

    def set_selected(self, selected):
        """Set whether this tab is selected"""
        self.is_selected = selected
        self.update_display()

    def mousePressEvent(self, event):
        """Handle mouse click on tab item"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            # Find parent TabListWidget and notify it
            parent = self.parent()
            while parent:
                if parent.__class__.__name__ == 'TabListWidget':
                    parent.select_tab(self)
                    break
                parent = parent.parent()

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag and drop"""
        try:
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                return
            if not self.drag_start_position:
                return

            # Check if we've moved far enough to start a drag
            if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                return

            # Start drag operation
            from PyQt6.QtCore import QMimeData
            from PyQt6.QtGui import QDrag, QPainter, QPixmap, QColor

            drag = QDrag(self)
            mime_data = QMimeData()

            # Store the index of this tab item
            parent = self.parent()
            while parent:
                if parent.__class__.__name__ == 'TabListWidget':
                    index = parent.tab_items.index(self)
                    mime_data.setText(str(index))
                    break
                parent = parent.parent()

            drag.setMimeData(mime_data)

            # Create a pixmap of this tab to show while dragging
            pixmap = self.grab()

            # Make it slightly transparent
            transparent_pixmap = QPixmap(pixmap.size())
            transparent_pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

            painter = QPainter(transparent_pixmap)
            painter.setOpacity(0.7)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            drag.setPixmap(transparent_pixmap)
            drag.setHotSpot(self.drag_start_position)

            # Change cursor to closed hand during drag
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

            # Make this tab semi-transparent during drag
            self.setStyleSheet(self.styleSheet() + " QFrame#TabListItem { opacity: 0.3; }")

            # Execute drag
            result = drag.exec(Qt.DropAction.MoveAction)

            # Restore cursor and opacity after drag
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update_display()
        except Exception as e:
            # Handle errors gracefully
            print(f"Error in mouseMoveEvent: {e}")
            # Reset cursor
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click on tab item to edit emoji and display name"""
        if event.button() == Qt.MouseButton.LeftButton:
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QCheckBox

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
            emoji_input.setText(self.get_emoji())
            emoji_input.setPlaceholderText("e.g., 📄 or P")
            emoji_input.setStyleSheet(input_style)
            emoji_layout.addWidget(emoji_input)

            # Hint label (shown when icon overrides emoji)
            emoji_hint = QLabel("(icon overrides)")
            emoji_hint.setStyleSheet("color: #666666; font-style: italic;")
            emoji_hint.setVisible(self.custom_icon is not None)
            emoji_layout.addWidget(emoji_hint)

            layout.addLayout(emoji_layout)

            # Custom icon section
            icon_layout = QHBoxLayout()
            icon_label = QLabel("Icon:")
            icon_label.setFixedWidth(100)
            icon_layout.addWidget(icon_label)

            # Track pending icon change
            pending_icon = [self.custom_icon]  # Use list to allow mutation in closure

            # Icon status label
            icon_status = QLabel()
            if self.custom_icon:
                icon_status.setText("Custom icon set")
                icon_status.setStyleSheet("color: #4CAF50;")
            else:
                icon_status.setText("No custom icon")
                icon_status.setStyleSheet("color: #666666;")
            icon_layout.addWidget(icon_status)

            icon_layout.addStretch()

            # Remove icon button (only shown when icon is set)
            remove_icon_btn = QPushButton("Remove")
            remove_icon_btn.setStyleSheet(button_style)
            remove_icon_btn.setVisible(self.custom_icon is not None)

            def remove_icon():
                pending_icon[0] = None
                icon_status.setText("Icon will be removed")
                icon_status.setStyleSheet("color: #FF9800;")
                emoji_hint.setVisible(False)
                remove_icon_btn.setVisible(False)

            remove_icon_btn.clicked.connect(remove_icon)
            icon_layout.addWidget(remove_icon_btn)

            # Upload icon button
            upload_icon_btn = QPushButton("Upload...")
            upload_icon_btn.setStyleSheet(button_style)

            def open_icon_editor():
                icon_dialog = IconEditorDialog(dialog, pending_icon[0])
                if icon_dialog.exec() == QDialog.DialogCode.Accepted:
                    result = icon_dialog.get_icon_filename()
                    if result == "":
                        # Icon removed (from icon editor dialog)
                        remove_icon()
                    elif result:
                        # New icon set
                        pending_icon[0] = result
                        icon_status.setText("New icon selected")
                        icon_status.setStyleSheet("color: #4CAF50;")
                        emoji_hint.setVisible(True)
                        remove_icon_btn.setVisible(True)

            upload_icon_btn.clicked.connect(open_icon_editor)
            icon_layout.addWidget(upload_icon_btn)
            layout.addLayout(icon_layout)

            # Display name input
            name_layout = QHBoxLayout()
            name_label = QLabel("Display Name:")
            name_label.setFixedWidth(100)
            name_layout.addWidget(name_label)
            name_input = QLineEdit()
            name_input.setText(self.custom_display_name or "")
            # Show what the default display name will be (without custom override)
            default_name = "Untitled"
            if self.editor_tab.file_path:
                filename = os.path.basename(self.editor_tab.file_path)
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
            pin_checkbox.setChecked(self.editor_tab.is_pinned)
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
                # Update custom icon if changed
                if pending_icon[0] != self.custom_icon:
                    self.custom_icon = pending_icon[0]

                # Always save emoji (preserved even when icon is set)
                new_emoji = emoji_input.text().strip()
                if new_emoji and new_emoji != self.get_emoji():
                    self.custom_emoji = new_emoji
                elif not new_emoji:
                    self.custom_emoji = None

                # Update display name if changed
                new_name = name_input.text().strip()
                if new_name:
                    self.custom_display_name = new_name
                else:
                    self.custom_display_name = None

                # Update pin status if changed
                new_pin_status = pin_checkbox.isChecked()
                if new_pin_status != self.editor_tab.is_pinned:
                    parent = self.parent()
                    while parent:
                        if parent.__class__.__name__ == 'TextEditorWindow':
                            parent.toggle_pin(self.editor_tab)
                            break
                        parent = parent.parent()

                self.update_display()

                # Notify parent window of metadata change
                parent = self.parent()
                while parent:
                    if parent.__class__.__name__ == 'TextEditorWindow':
                        parent.mark_tabs_metadata_modified()
                        break
                    parent = parent.parent()


