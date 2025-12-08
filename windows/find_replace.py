"""
Find and Replace dialog window.
Provides search and replace functionality with highlighting.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument, QTextCursor, QColor, QBrush, QTextCharFormat


class FindReplaceDialog(QDialog):
    """Dialog for find and replace functionality"""

    def __init__(self, text_edit, parent=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self.last_search_text = ""
        self.all_matches = []  # Store all match positions for Find All

        self.setWindowTitle("Find and Replace")
        self.setModal(False)
        self.resize(450, 220)

        # Create layout
        layout = QVBoxLayout()

        # Find row
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.textChanged.connect(self.on_find_text_changed)
        self.find_input.returnPressed.connect(self.find_next)
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        # Replace row
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.returnPressed.connect(self.replace_current)
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        # Options row
        options_layout = QHBoxLayout()
        self.case_sensitive_cb = QCheckBox("Case Sensitive")
        self.whole_words_cb = QCheckBox("Whole Words")
        options_layout.addWidget(self.case_sensitive_cb)
        options_layout.addWidget(self.whole_words_cb)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # First buttons row - Find operations
        buttons_row1 = QHBoxLayout()

        self.find_next_btn = QPushButton("Find Next")
        self.find_next_btn.clicked.connect(self.find_next)
        buttons_row1.addWidget(self.find_next_btn)

        self.find_prev_btn = QPushButton("Find Previous")
        self.find_prev_btn.clicked.connect(self.find_previous)
        buttons_row1.addWidget(self.find_prev_btn)

        self.find_all_btn = QPushButton("Find All")
        self.find_all_btn.clicked.connect(self.find_all)
        buttons_row1.addWidget(self.find_all_btn)

        buttons_row1.addStretch()

        layout.addLayout(buttons_row1)

        # Second buttons row - Replace operations
        buttons_row2 = QHBoxLayout()

        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_current)
        buttons_row2.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all)
        buttons_row2.addWidget(self.replace_all_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        buttons_row2.addWidget(self.close_btn)

        buttons_row2.addStretch()

        layout.addLayout(buttons_row2)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def on_find_text_changed(self):
        """Reset search when find text changes"""
        self.status_label.setText("")
        self.clear_all_highlights()

    def clear_all_highlights(self):
        """Clear all yellow highlights"""
        self.text_edit.setExtraSelections([])
        self.all_matches = []

    def highlight_all_matches(self, search_text):
        """Highlight all matches in vivid yellow"""
        if not search_text:
            return

        # Clear previous highlights
        self.all_matches = []

        # Create yellow highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(QColor(255, 255, 0)))  # Vivid yellow

        flags = self.get_find_flags()

        # Find all matches
        cursor = self.text_edit.document().find(search_text, 0, flags)
        extra_selections = []

        while not cursor.isNull():
            selection = self.text_edit.ExtraSelection()
            selection.format = highlight_format
            selection.cursor = cursor
            extra_selections.append(selection)
            self.all_matches.append(cursor.position())
            cursor = self.text_edit.document().find(search_text, cursor, flags)

        # Apply all highlights
        self.text_edit.setExtraSelections(extra_selections)

        return len(extra_selections)

    def get_find_flags(self):
        """Get QTextDocument find flags based on options"""
        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.whole_words_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def find_next(self):
        """Find next occurrence"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        # Highlight all matches first
        count = self.highlight_all_matches(search_text)

        if count == 0:
            self.status_label.setText("Not found")
            return

        # Get current cursor position to search from
        current_cursor = self.text_edit.textCursor()
        current_pos = current_cursor.position()

        # Find next occurrence using document.find (doesn't select)
        flags = self.get_find_flags()
        found_cursor = self.text_edit.document().find(search_text, current_pos, flags)

        if found_cursor.isNull():
            # Try wrapping from beginning
            found_cursor = self.text_edit.document().find(search_text, 0, flags)

            if not found_cursor.isNull():
                self.status_label.setText("Wrapped to beginning")
            else:
                self.status_label.setText("Not found")
                return
        else:
            self.status_label.setText("")

        # Move cursor to the found position WITHOUT selecting
        # This way we only see the yellow highlights, not a grey selection
        new_cursor = self.text_edit.textCursor()
        new_cursor.setPosition(found_cursor.selectionStart())
        self.text_edit.setTextCursor(new_cursor)
        self.text_edit.ensureCursorVisible()

    def find_previous(self):
        """Find previous occurrence"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        # Highlight all matches first
        count = self.highlight_all_matches(search_text)

        if count == 0:
            self.status_label.setText("Not found")
            return

        # Get current cursor position to search from
        current_cursor = self.text_edit.textCursor()
        current_pos = current_cursor.position()

        # Find previous occurrence using document.find (doesn't select)
        flags = self.get_find_flags() | QTextDocument.FindFlag.FindBackward
        found_cursor = self.text_edit.document().find(search_text, current_pos, flags)

        if found_cursor.isNull():
            # Try wrapping from end - use document length
            doc_length = self.text_edit.document().characterCount()
            found_cursor = self.text_edit.document().find(search_text, doc_length, flags)

            if not found_cursor.isNull():
                self.status_label.setText("Wrapped to end")
            else:
                self.status_label.setText("Not found")
                return
        else:
            self.status_label.setText("")

        # Move cursor to the found position WITHOUT selecting
        new_cursor = self.text_edit.textCursor()
        new_cursor.setPosition(found_cursor.selectionStart())
        self.text_edit.setTextCursor(new_cursor)
        self.text_edit.ensureCursorVisible()

    def find_all(self):
        """Find and highlight all occurrences"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        count = self.highlight_all_matches(search_text)

        if count > 0:
            self.status_label.setText(f"Found {count} occurrence(s)")

            # Scroll to the first match
            flags = self.get_find_flags()
            found_cursor = self.text_edit.document().find(search_text, 0, flags)

            if not found_cursor.isNull():
                # Move cursor to first match WITHOUT selecting
                new_cursor = self.text_edit.textCursor()
                new_cursor.setPosition(found_cursor.selectionStart())
                self.text_edit.setTextCursor(new_cursor)
                self.text_edit.ensureCursorVisible()
        else:
            self.status_label.setText("Not found")

    def replace_current(self):
        """Replace current selection if it matches find text"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        # Find the match at or after cursor position
        cursor = self.text_edit.textCursor()
        current_pos = cursor.position()

        flags = self.get_find_flags()
        found_cursor = self.text_edit.document().find(search_text, current_pos, flags)

        # If not found from current position, try from beginning
        if found_cursor.isNull():
            found_cursor = self.text_edit.document().find(search_text, 0, flags)

        if found_cursor.isNull():
            self.status_label.setText("Not found")
            return

        # Replace the found text
        found_cursor.insertText(self.replace_input.text())
        self.status_label.setText("Replaced 1 occurrence")

        # Update highlights (count has changed)
        remaining_count = self.highlight_all_matches(search_text)

        if remaining_count > 0:
            # Move to next occurrence - find from the position where we just replaced
            replace_pos = found_cursor.position()
            next_cursor = self.text_edit.document().find(search_text, replace_pos, flags)

            if next_cursor.isNull():
                # No more matches after this position, wrap to beginning
                next_cursor = self.text_edit.document().find(search_text, 0, flags)
                if not next_cursor.isNull():
                    self.status_label.setText("Replaced 1 occurrence - Wrapped to beginning")

            if not next_cursor.isNull():
                # Move cursor to next match WITHOUT selecting
                new_cursor = self.text_edit.textCursor()
                new_cursor.setPosition(next_cursor.selectionStart())
                self.text_edit.setTextCursor(new_cursor)
                self.text_edit.ensureCursorVisible()
        else:
            # No more matches, just position cursor where we replaced
            new_cursor = self.text_edit.textCursor()
            new_cursor.setPosition(found_cursor.position())
            self.text_edit.setTextCursor(new_cursor)
            self.text_edit.ensureCursorVisible()
            self.status_label.setText("Replaced last occurrence")

    def replace_all(self):
        """Replace all occurrences"""
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        # Save current scroll position
        scrollbar = self.text_edit.verticalScrollBar()
        scroll_position = scrollbar.value()

        # Count and replace
        count = 0
        flags = self.get_find_flags()

        # Use document's find method for more control
        cursor = self.text_edit.document().find(search_text, 0, flags)

        if not cursor.isNull():
            self.text_edit.textCursor().beginEditBlock()
            while not cursor.isNull():
                cursor.insertText(replace_text)
                count += 1
                cursor = self.text_edit.document().find(search_text, cursor, flags)
            self.text_edit.textCursor().endEditBlock()

        if count > 0:
            self.status_label.setText(f"Replaced {count} occurrence(s)")
        else:
            self.status_label.setText("Not found")

        # Restore scroll position
        scrollbar.setValue(scroll_position)

        # Clear highlights
        self.clear_all_highlights()

    def showEvent(self, event):
        """Focus find input when dialog is shown"""
        super().showEvent(event)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def closeEvent(self, event):
        """Clear highlights when dialog is closed"""
        self.clear_all_highlights()
        super().closeEvent(event)


