"""
Find and Replace dialog window.
Provides search and replace functionality with highlighting.
Supports searching across all tabs or just the current tab.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QRadioButton, QComboBox, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument, QTextCursor, QColor, QBrush, QTextCharFormat

import os


class FindReplaceDialog(QDialog):
    """Dialog for find and replace functionality"""

    def __init__(self, text_edit, parent=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self.main_window = parent  # TextEditorWindow
        self.last_search_text = ""
        self.all_matches = []  # Store all match positions for Find All
        self.results_data = []  # Store result data for grid (tab, line, pos, text)

        self.setWindowTitle("Find and Replace")
        self.setModal(False)
        self.resize(600, 400)

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

        # Scope row - radio buttons for All Tabs vs Current Tab
        scope_layout = QHBoxLayout()
        self.scope_group = QButtonGroup(self)

        self.all_tabs_radio = QRadioButton("All Tabs")
        self.current_tab_radio = QRadioButton("Current Tab:")
        self.current_tab_radio.setChecked(True)  # Default to current tab

        self.scope_group.addButton(self.all_tabs_radio, 0)
        self.scope_group.addButton(self.current_tab_radio, 1)

        self.tab_dropdown = QComboBox()
        self.tab_dropdown.setMinimumWidth(200)
        self._populate_tab_dropdown()

        scope_layout.addWidget(self.all_tabs_radio)
        scope_layout.addWidget(self.current_tab_radio)
        scope_layout.addWidget(self.tab_dropdown)
        scope_layout.addStretch()

        # Connect scope changes
        self.all_tabs_radio.toggled.connect(self._on_scope_changed)
        self.current_tab_radio.toggled.connect(self._on_scope_changed)
        self.tab_dropdown.currentIndexChanged.connect(self._on_tab_dropdown_changed)

        layout.addLayout(scope_layout)

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

        buttons_row2.addStretch()

        layout.addLayout(buttons_row2)

        # Results table for Find All
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Tab", "Line", "Context", ""])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.doubleClicked.connect(self._on_result_double_click)
        self.results_table.setMinimumHeight(120)
        self.results_table.hide()  # Hidden until Find All is used
        layout.addWidget(self.results_table)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # Update dropdown state based on initial radio selection
        self._on_scope_changed()

    def _populate_tab_dropdown(self):
        """Populate the tab dropdown with all open tabs"""
        self.tab_dropdown.blockSignals(True)
        self.tab_dropdown.clear()

        if not self.main_window:
            self.tab_dropdown.blockSignals(False)
            return

        current_tab = self.main_window.get_current_tab()
        current_index = 0

        from models.tab_list_item_model import TextEditorTab
        for i in range(self.main_window.content_stack.count()):
            widget = self.main_window.content_stack.widget(i)
            if isinstance(widget, TextEditorTab):
                # Get display name from tab list item
                display_name = self._get_tab_display_name(widget)
                self.tab_dropdown.addItem(display_name, widget)
                if widget == current_tab:
                    current_index = self.tab_dropdown.count() - 1

        self.tab_dropdown.setCurrentIndex(current_index)
        self.tab_dropdown.blockSignals(False)

    def _get_tab_display_name(self, tab):
        """Get display name for a tab"""
        if tab.file_path:
            return os.path.basename(tab.file_path)
        return "Untitled"

    def _on_scope_changed(self):
        """Handle scope radio button changes"""
        self.tab_dropdown.setEnabled(self.current_tab_radio.isChecked())
        self.clear_all_highlights()
        self._clear_results_table()

    def _on_tab_dropdown_changed(self, index):
        """Handle tab dropdown selection change"""
        if self.current_tab_radio.isChecked() and index >= 0:
            tab = self.tab_dropdown.itemData(index)
            if tab:
                self.text_edit = tab.text_edit
                self.clear_all_highlights()
                self._clear_results_table()

    def update_current_tab(self, tab):
        """Called when the main window switches tabs - update dropdown to match"""
        if not tab:
            return

        self.text_edit = tab.text_edit

        # Update dropdown selection to match
        for i in range(self.tab_dropdown.count()):
            if self.tab_dropdown.itemData(i) == tab:
                self.tab_dropdown.blockSignals(True)
                self.tab_dropdown.setCurrentIndex(i)
                self.tab_dropdown.blockSignals(False)
                break

        # Clear highlights when switching
        self.clear_all_highlights()

    def refresh_tab_list(self):
        """Refresh the tab dropdown (called when tabs are added/removed)"""
        self._populate_tab_dropdown()

    def _clear_results_table(self):
        """Clear the results table"""
        self.results_table.setRowCount(0)
        self.results_data = []
        self.results_table.hide()
        self.resize(600, 280)

    def on_find_text_changed(self):
        """Reset search when find text changes"""
        self.status_label.setText("")
        self.clear_all_highlights()
        self._clear_results_table()

    def clear_all_highlights(self):
        """Clear all yellow highlights on current text edit"""
        if self.text_edit:
            self.text_edit.setExtraSelections([])
        self.all_matches = []

    def _clear_all_tab_highlights(self):
        """Clear highlights on all tabs"""
        if not self.main_window:
            return

        from models.tab_list_item_model import TextEditorTab
        for i in range(self.main_window.content_stack.count()):
            widget = self.main_window.content_stack.widget(i)
            if isinstance(widget, TextEditorTab):
                widget.text_edit.setExtraSelections([])

    def _get_search_tabs(self):
        """Get list of tabs to search based on scope"""
        if not self.main_window:
            return [(self.text_edit, None)]

        from models.tab_list_item_model import TextEditorTab

        if self.all_tabs_radio.isChecked():
            # Search all tabs
            tabs = []
            for i in range(self.main_window.content_stack.count()):
                widget = self.main_window.content_stack.widget(i)
                if isinstance(widget, TextEditorTab):
                    tabs.append((widget.text_edit, widget))
            return tabs
        else:
            # Search only selected tab
            selected_tab = self.tab_dropdown.currentData()
            if selected_tab:
                return [(selected_tab.text_edit, selected_tab)]
            return [(self.text_edit, None)]

    def highlight_all_matches(self, search_text):
        """Highlight all matches in vivid yellow"""
        if not search_text:
            return 0

        # Clear previous highlights on all tabs
        self._clear_all_tab_highlights()
        self.all_matches = []

        # Create yellow highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(QColor(255, 255, 0)))  # Vivid yellow

        flags = self.get_find_flags()
        total_count = 0

        for text_edit, tab in self._get_search_tabs():
            cursor = text_edit.document().find(search_text, 0, flags)
            extra_selections = []

            while not cursor.isNull():
                selection = text_edit.ExtraSelection()
                selection.format = highlight_format
                selection.cursor = cursor
                extra_selections.append(selection)
                self.all_matches.append((text_edit, cursor.position()))
                cursor = text_edit.document().find(search_text, cursor, flags)

            # Apply highlights to this tab
            text_edit.setExtraSelections(extra_selections)
            total_count += len(extra_selections)

        return total_count

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
        """Find and highlight all occurrences, populate results grid"""
        search_text = self.find_input.text()
        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        # Clear previous results
        self._clear_all_tab_highlights()
        self.results_data = []
        self.all_matches = []  # Clear and repopulate for backward compatibility
        self.results_table.setRowCount(0)

        flags = self.get_find_flags()
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(QColor(255, 255, 0)))

        total_count = 0
        show_tab_column = self.all_tabs_radio.isChecked()

        for text_edit, tab in self._get_search_tabs():
            cursor = text_edit.document().find(search_text, 0, flags)
            extra_selections = []

            while not cursor.isNull():
                selection = text_edit.ExtraSelection()
                selection.format = highlight_format
                selection.cursor = cursor

                extra_selections.append(selection)

                # Track match for backward compatibility
                self.all_matches.append((text_edit, cursor.position()))

                # Get line info for results grid
                block = cursor.block()
                line_number = block.blockNumber() + 1
                line_text = block.text()

                # Get position within line for highlighting context
                pos_in_block = cursor.selectionStart() - block.position()

                # Store result data
                self.results_data.append({
                    'tab': tab,
                    'text_edit': text_edit,
                    'line': line_number,
                    'position': cursor.selectionStart(),
                    'line_text': line_text,
                    'match_start': pos_in_block,
                    'match_len': len(search_text)
                })

                total_count += 1
                cursor = text_edit.document().find(search_text, cursor, flags)

            # Apply highlights to this tab
            text_edit.setExtraSelections(extra_selections)

        # Populate results table
        if total_count > 0:
            self._populate_results_table(show_tab_column)
            self.status_label.setText(f"Found {total_count} occurrence(s)")
            self.results_table.show()
            self.resize(600, 400)

            # Scroll to the first match in current view
            if self.results_data:
                first_result = self.results_data[0]
                new_cursor = first_result['text_edit'].textCursor()
                new_cursor.setPosition(first_result['position'])
                first_result['text_edit'].setTextCursor(new_cursor)
                first_result['text_edit'].ensureCursorVisible()
        else:
            self.status_label.setText("Not found")
            self.results_table.hide()

    def _populate_results_table(self, show_tab_column):
        """Populate the results table with find results"""
        self.results_table.setRowCount(len(self.results_data))

        # Show/hide tab column based on scope
        if show_tab_column:
            self.results_table.showColumn(0)
        else:
            self.results_table.hideColumn(0)

        for row, result in enumerate(self.results_data):
            # Tab name
            tab_name = self._get_tab_display_name(result['tab']) if result['tab'] else "Current"
            tab_item = QTableWidgetItem(tab_name)
            self.results_table.setItem(row, 0, tab_item)

            # Line number
            line_item = QTableWidgetItem(str(result['line']))
            line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(row, 1, line_item)

            # Context - truncate long lines, highlight match position
            context = self._format_context(
                result['line_text'],
                result['match_start'],
                result['match_len']
            )
            context_item = QTableWidgetItem(context)
            self.results_table.setItem(row, 2, context_item)

            # Replace button
            replace_btn = QPushButton("Replace")
            replace_btn.clicked.connect(lambda checked, r=row: self._replace_single_result(r))
            self.results_table.setCellWidget(row, 3, replace_btn)

    def _format_context(self, line_text, match_start, match_len, max_context=60):
        """Format line text with context around match, truncating if needed"""
        # Calculate how much context to show on each side
        half_context = (max_context - match_len) // 2

        # Determine start and end of context window
        context_start = max(0, match_start - half_context)
        context_end = min(len(line_text), match_start + match_len + half_context)

        # Build context string
        prefix = "..." if context_start > 0 else ""
        suffix = "..." if context_end < len(line_text) else ""

        context = line_text[context_start:context_end].strip()

        # Add markers around the match within the context
        adjusted_match_start = match_start - context_start
        if 0 <= adjusted_match_start < len(context):
            before = context[:adjusted_match_start]
            match = context[adjusted_match_start:adjusted_match_start + match_len]
            after = context[adjusted_match_start + match_len:]
            context = f"{before}[{match}]{after}"

        return f"{prefix}{context}{suffix}"

    def _on_result_double_click(self, index):
        """Handle double-click on a result row - navigate to that match"""
        row = index.row()
        if 0 <= row < len(self.results_data):
            self._navigate_to_result(row)

    def _navigate_to_result(self, row):
        """Navigate to a specific result"""
        if row < 0 or row >= len(self.results_data):
            return

        result = self.results_data[row]
        tab = result['tab']
        text_edit = result['text_edit']
        position = result['position']

        # Switch to the tab if needed
        if tab and self.main_window:
            self.main_window.switch_to_tab(tab)
            # Also select in tab list
            for tab_item in self.main_window.tab_list.tab_items:
                if tab_item.editor_tab == tab:
                    self.main_window.tab_list.select_tab(tab_item)
                    break

        # Move cursor to position
        cursor = text_edit.textCursor()
        cursor.setPosition(position)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()

    def _replace_single_result(self, row):
        """Replace a single result from the grid"""
        if row < 0 or row >= len(self.results_data):
            return

        result = self.results_data[row]
        text_edit = result['text_edit']
        position = result['position']
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()

        # Navigate to the result first
        self._navigate_to_result(row)

        # Find the match at this exact position
        flags = self.get_find_flags()
        cursor = text_edit.document().find(search_text, position - 1, flags)

        if not cursor.isNull() and cursor.selectionStart() == position:
            # Replace the text
            cursor.insertText(replace_text)
            self.status_label.setText("Replaced 1 occurrence")

            # Re-run find all to update the grid
            self.find_all()
        else:
            self.status_label.setText("Match no longer found (text may have changed)")

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

        # Update results table if visible
        if self.results_table.isVisible():
            self.find_all()

    def replace_all(self):
        """Replace all occurrences"""
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()

        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        count = 0
        flags = self.get_find_flags()

        for text_edit, tab in self._get_search_tabs():
            # Save current scroll position
            scrollbar = text_edit.verticalScrollBar()
            scroll_position = scrollbar.value()

            # Use document's find method for more control
            cursor = text_edit.document().find(search_text, 0, flags)

            if not cursor.isNull():
                text_edit.textCursor().beginEditBlock()
                while not cursor.isNull():
                    cursor.insertText(replace_text)
                    count += 1
                    cursor = text_edit.document().find(search_text, cursor, flags)
                text_edit.textCursor().endEditBlock()

            # Restore scroll position
            scrollbar.setValue(scroll_position)

        if count > 0:
            self.status_label.setText(f"Replaced {count} occurrence(s)")
        else:
            self.status_label.setText("Not found")

        # Clear highlights and results
        self._clear_all_tab_highlights()
        self._clear_results_table()

    def showEvent(self, event):
        """Focus find input when dialog is shown"""
        super().showEvent(event)
        self._populate_tab_dropdown()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def closeEvent(self, event):
        """Clear highlights when dialog is closed"""
        self._clear_all_tab_highlights()
        super().closeEvent(event)
