"""
Find and Replace dialog window.
Provides search and replace functionality with highlighting.
Supports searching across all tabs or just the current tab.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QRadioButton, QComboBox, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument, QTextCursor, QColor, QBrush, QTextCharFormat

import html
import os
import re


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
        self.regex_cb = QCheckBox("Regex")
        self.regex_cb.toggled.connect(self._on_regex_toggled)

        self.regex_info_btn = QPushButton("ℹ")
        self.regex_info_btn.setToolTip("Show regex help")
        self.regex_info_btn.setFixedWidth(24)
        self.regex_info_btn.clicked.connect(self._show_regex_help)

        options_layout.addWidget(self.case_sensitive_cb)
        options_layout.addWidget(self.whole_words_cb)
        options_layout.addWidget(self.regex_cb)
        options_layout.addWidget(self.regex_info_btn)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Scope row - radio buttons for All Tabs vs Current Tab vs Selection
        scope_layout = QHBoxLayout()
        self.scope_group = QButtonGroup(self)

        self.all_tabs_radio = QRadioButton("All Tabs")
        self.current_tab_radio = QRadioButton("Current Tab:")
        self.selection_radio = QRadioButton("Selection")
        self.current_tab_radio.setChecked(True)  # Default to current tab

        self.scope_group.addButton(self.all_tabs_radio, 0)
        self.scope_group.addButton(self.current_tab_radio, 1)
        self.scope_group.addButton(self.selection_radio, 2)

        self.tab_dropdown = QComboBox()
        self.tab_dropdown.setMinimumWidth(200)
        self._populate_tab_dropdown()

        scope_layout.addWidget(self.all_tabs_radio)
        scope_layout.addWidget(self.current_tab_radio)
        scope_layout.addWidget(self.tab_dropdown)
        scope_layout.addWidget(self.selection_radio)
        scope_layout.addStretch()

        # Connect scope changes
        self.all_tabs_radio.toggled.connect(self._on_scope_changed)
        self.current_tab_radio.toggled.connect(self._on_scope_changed)
        self.selection_radio.toggled.connect(self._on_scope_changed)
        self.tab_dropdown.currentIndexChanged.connect(self._on_tab_dropdown_changed)

        # Store selection range for "Selection" scope
        self._selection_start = 0
        self._selection_end = 0

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
        self._update_selection_radio_state()

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
        """Get list of tabs to search based on scope.
        Returns list of (text_edit, tab, start_pos, end_pos) tuples.
        start_pos/end_pos are None for full document search."""
        if not self.main_window:
            return [(self.text_edit, None, None, None)]

        from models.tab_list_item_model import TextEditorTab

        if self.all_tabs_radio.isChecked():
            # Search all tabs
            tabs = []
            for i in range(self.main_window.content_stack.count()):
                widget = self.main_window.content_stack.widget(i)
                if isinstance(widget, TextEditorTab):
                    tabs.append((widget.text_edit, widget, None, None))
            return tabs
        elif self.selection_radio.isChecked():
            # Search only within selection
            return [(self.text_edit, None, self._selection_start, self._selection_end)]
        else:
            # Search only selected tab
            selected_tab = self.tab_dropdown.currentData()
            if selected_tab:
                return [(selected_tab.text_edit, selected_tab, None, None)]
            return [(self.text_edit, None, None, None)]

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

        total_count = 0

        for text_edit, tab, start_pos, end_pos in self._get_search_tabs():
            extra_selections = []
            search_start = start_pos if start_pos is not None else 0

            if self.regex_cb.isChecked():
                # Regex mode: use Python's re module
                doc_text = text_edit.toPlainText()
                matches = self._find_regex_matches(doc_text, search_text, search_start, end_pos)

                for match_start, match_end, matched_text in matches:
                    cursor = text_edit.textCursor()
                    cursor.setPosition(match_start)
                    cursor.setPosition(match_end, QTextCursor.MoveMode.KeepAnchor)

                    selection = QTextEdit.ExtraSelection()
                    selection.format = highlight_format
                    selection.cursor = cursor
                    extra_selections.append(selection)
                    self.all_matches.append((text_edit, match_end))
            else:
                # Normal mode: use QTextDocument.find
                flags = self.get_find_flags()
                cursor = text_edit.document().find(search_text, search_start, flags)

                while not cursor.isNull():
                    # Stop if we've gone past the selection end
                    if end_pos is not None and cursor.selectionStart() >= end_pos:
                        break

                    selection = QTextEdit.ExtraSelection()
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

        if self.regex_cb.isChecked():
            # Regex mode
            doc_text = self.text_edit.toPlainText()
            matches = self._find_regex_matches(doc_text, search_text, current_pos)

            if not matches:
                # Try wrapping from beginning
                matches = self._find_regex_matches(doc_text, search_text, 0)
                if matches:
                    self.status_label.setText("Wrapped to beginning")
                    found_pos = matches[0][0]
                else:
                    self.status_label.setText("Not found")
                    return
            else:
                self.status_label.setText("")
                found_pos = matches[0][0]
        else:
            # Normal mode
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

            found_pos = found_cursor.selectionStart()

        # Move cursor to the found position WITHOUT selecting
        # This way we only see the yellow highlights, not a grey selection
        new_cursor = self.text_edit.textCursor()
        new_cursor.setPosition(found_pos)
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

        if self.regex_cb.isChecked():
            # Regex mode: find all matches before current position
            doc_text = self.text_edit.toPlainText()
            # Get all matches, filter to those before current position
            all_matches = self._find_regex_matches(doc_text, search_text, 0)
            matches_before = [(s, e, t) for s, e, t in all_matches if e <= current_pos]

            if not matches_before:
                # Try wrapping from end
                if all_matches:
                    self.status_label.setText("Wrapped to end")
                    found_pos = all_matches[-1][0]
                else:
                    self.status_label.setText("Not found")
                    return
            else:
                self.status_label.setText("")
                found_pos = matches_before[-1][0]  # Last match before current pos
        else:
            # Normal mode
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

            found_pos = found_cursor.selectionStart()

        # Move cursor to the found position WITHOUT selecting
        new_cursor = self.text_edit.textCursor()
        new_cursor.setPosition(found_pos)
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

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(QColor(255, 255, 0)))

        total_count = 0
        show_tab_column = self.all_tabs_radio.isChecked()

        for text_edit, tab, start_pos, end_pos in self._get_search_tabs():
            search_start = start_pos if start_pos is not None else 0
            extra_selections = []

            if self.regex_cb.isChecked():
                # Regex mode
                doc_text = text_edit.toPlainText()
                matches = self._find_regex_matches(doc_text, search_text, search_start, end_pos)

                for match_start, match_end, matched_text in matches:
                    cursor = text_edit.textCursor()
                    cursor.setPosition(match_start)
                    cursor.setPosition(match_end, QTextCursor.MoveMode.KeepAnchor)

                    selection = QTextEdit.ExtraSelection()
                    selection.format = highlight_format
                    selection.cursor = cursor
                    extra_selections.append(selection)

                    # Track match for backward compatibility
                    self.all_matches.append((text_edit, match_end))

                    # Get line info for results grid
                    block = cursor.block()
                    line_number = block.blockNumber() + 1
                    line_text = block.text()
                    pos_in_block = match_start - block.position()

                    # Store result data
                    self.results_data.append({
                        'tab': tab,
                        'text_edit': text_edit,
                        'line': line_number,
                        'position': match_start,
                        'line_text': line_text,
                        'match_start': pos_in_block,
                        'match_len': len(matched_text)
                    })
                    total_count += 1
            else:
                # Normal mode
                flags = self.get_find_flags()
                cursor = text_edit.document().find(search_text, search_start, flags)

                while not cursor.isNull():
                    # Stop if we've gone past the selection end
                    if end_pos is not None and cursor.selectionStart() >= end_pos:
                        break

                    selection = QTextEdit.ExtraSelection()
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
            context_html = self._format_context(
                result['line_text'],
                result['match_start'],
                result['match_len']
            )
            # Use QLabel for HTML rendering
            context_label = QLabel(context_html)
            context_label.setTextFormat(Qt.TextFormat.RichText)
            context_label.setStyleSheet("padding: 2px;")
            self.results_table.setCellWidget(row, 2, context_label)

            # Replace button
            replace_btn = QPushButton("Replace")
            replace_btn.clicked.connect(lambda checked, r=row: self._replace_single_result(r))
            self.results_table.setCellWidget(row, 3, replace_btn)

    def _format_context(self, line_text, match_start, match_len, max_context=60):
        """Format line text with context around match, truncating if needed.
        Returns HTML with yellow-highlighted match."""
        # Calculate how much context to show on each side
        half_context = (max_context - match_len) // 2

        # Determine start and end of context window
        context_start = max(0, match_start - half_context)
        context_end = min(len(line_text), match_start + match_len + half_context)

        # Build context string
        prefix = "..." if context_start > 0 else ""
        suffix = "..." if context_end < len(line_text) else ""

        context = line_text[context_start:context_end]

        # Calculate how much leading whitespace to strip and adjust match position
        stripped_context = context.lstrip()
        leading_stripped = len(context) - len(stripped_context)
        context = stripped_context.rstrip()

        # Adjust match position for the stripped leading whitespace
        adjusted_match_start = match_start - context_start - leading_stripped

        # Build HTML with highlighted match
        if 0 <= adjusted_match_start < len(context):
            before = html.escape(context[:adjusted_match_start])
            match = html.escape(context[adjusted_match_start:adjusted_match_start + match_len])
            after = html.escape(context[adjusted_match_start + match_len:])
            context_html = f'{before}<span style="background-color: #FFFF00; font-weight: bold;">{match}</span>{after}'
        else:
            context_html = html.escape(context)

        return f"{prefix}{context_html}{suffix}"

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
        match_len = result['match_len']
        search_text = self.find_input.text()
        replace_text = self.replace_input.text()

        # Navigate to the result first
        self._navigate_to_result(row)

        if self.regex_cb.isChecked():
            # Regex mode - get the match at this position
            doc_text = text_edit.toPlainText()
            matches = self._find_regex_matches(doc_text, search_text, position)

            if matches and matches[0][0] == position:
                match_start, match_end, matched_text = matches[0]

                cursor = text_edit.textCursor()
                cursor.setPosition(match_start)
                cursor.setPosition(match_end, QTextCursor.MoveMode.KeepAnchor)

                try:
                    regex_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
                    regex = re.compile(search_text, regex_flags)
                    actual_replace_text = regex.sub(replace_text, matched_text)
                except re.error:
                    actual_replace_text = replace_text

                cursor.insertText(actual_replace_text)
                self.status_label.setText("Replaced 1 occurrence")
                self.find_all()
            else:
                self.status_label.setText("Match no longer found (text may have changed)")
        else:
            # Normal mode
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
        replace_text = self.replace_input.text()
        if not search_text:
            self.status_label.setText("Please enter text to find")
            return

        # Find the match at or after cursor position
        cursor = self.text_edit.textCursor()
        current_pos = cursor.position()

        if self.regex_cb.isChecked():
            # Regex mode
            doc_text = self.text_edit.toPlainText()
            matches = self._find_regex_matches(doc_text, search_text, current_pos)

            if not matches:
                # Try from beginning
                matches = self._find_regex_matches(doc_text, search_text, 0)

            if not matches:
                self.status_label.setText("Not found")
                return

            match_start, match_end, matched_text = matches[0]

            # Create cursor to select the match
            found_cursor = self.text_edit.textCursor()
            found_cursor.setPosition(match_start)
            found_cursor.setPosition(match_end, QTextCursor.MoveMode.KeepAnchor)

            # Perform regex replacement with group substitution
            try:
                regex_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
                regex = re.compile(search_text, regex_flags)
                actual_replace_text = regex.sub(replace_text, matched_text)
            except re.error:
                actual_replace_text = replace_text

            found_cursor.insertText(actual_replace_text)
            replace_pos = found_cursor.position()
        else:
            # Normal mode
            flags = self.get_find_flags()
            found_cursor = self.text_edit.document().find(search_text, current_pos, flags)

            # If not found from current position, try from beginning
            if found_cursor.isNull():
                found_cursor = self.text_edit.document().find(search_text, 0, flags)

            if found_cursor.isNull():
                self.status_label.setText("Not found")
                return

            # Replace the found text
            found_cursor.insertText(replace_text)
            replace_pos = found_cursor.position()

        self.status_label.setText("Replaced 1 occurrence")

        # Update highlights (count has changed)
        remaining_count = self.highlight_all_matches(search_text)

        if remaining_count > 0:
            # Move to next occurrence
            if self.regex_cb.isChecked():
                doc_text = self.text_edit.toPlainText()
                next_matches = self._find_regex_matches(doc_text, search_text, replace_pos)
                if not next_matches:
                    next_matches = self._find_regex_matches(doc_text, search_text, 0)
                    if next_matches:
                        self.status_label.setText("Replaced 1 occurrence - Wrapped to beginning")

                if next_matches:
                    new_cursor = self.text_edit.textCursor()
                    new_cursor.setPosition(next_matches[0][0])
                    self.text_edit.setTextCursor(new_cursor)
                    self.text_edit.ensureCursorVisible()
            else:
                flags = self.get_find_flags()
                next_cursor = self.text_edit.document().find(search_text, replace_pos, flags)

                if next_cursor.isNull():
                    next_cursor = self.text_edit.document().find(search_text, 0, flags)
                    if not next_cursor.isNull():
                        self.status_label.setText("Replaced 1 occurrence - Wrapped to beginning")

                if not next_cursor.isNull():
                    new_cursor = self.text_edit.textCursor()
                    new_cursor.setPosition(next_cursor.selectionStart())
                    self.text_edit.setTextCursor(new_cursor)
                    self.text_edit.ensureCursorVisible()
        else:
            # No more matches, just position cursor where we replaced
            new_cursor = self.text_edit.textCursor()
            new_cursor.setPosition(replace_pos)
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

        for text_edit, tab, start_pos, end_pos in self._get_search_tabs():
            # Save current scroll position
            scrollbar = text_edit.verticalScrollBar()
            scroll_position = scrollbar.value()

            search_start = start_pos if start_pos is not None else 0

            if self.regex_cb.isChecked():
                # Regex mode - get all matches first, then replace from end to start
                # to avoid position shifting issues
                doc_text = text_edit.toPlainText()
                matches = self._find_regex_matches(doc_text, search_text, search_start, end_pos)

                if matches:
                    try:
                        regex_flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE
                        regex = re.compile(search_text, regex_flags)
                    except re.error:
                        continue

                    # Process matches in reverse order to preserve positions
                    text_edit.textCursor().beginEditBlock()
                    for match_start, match_end, matched_text in reversed(matches):
                        cursor = text_edit.textCursor()
                        cursor.setPosition(match_start)
                        cursor.setPosition(match_end, QTextCursor.MoveMode.KeepAnchor)

                        # Perform regex replacement with group substitution
                        actual_replace_text = regex.sub(replace_text, matched_text)
                        cursor.insertText(actual_replace_text)
                        count += 1
                    text_edit.textCursor().endEditBlock()
            else:
                # Normal mode
                flags = self.get_find_flags()
                cursor = text_edit.document().find(search_text, search_start, flags)

                if not cursor.isNull():
                    text_edit.textCursor().beginEditBlock()
                    while not cursor.isNull():
                        # Stop if we've gone past the selection end
                        if end_pos is not None and cursor.selectionStart() >= end_pos:
                            break
                        cursor.insertText(replace_text)
                        count += 1
                        # Adjust end_pos for replaced text length difference
                        if end_pos is not None:
                            end_pos += len(replace_text) - len(search_text)
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
        self._capture_selection()
        self._update_selection_radio_state()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def _capture_selection(self):
        """Capture current text selection for Selection scope"""
        if self.text_edit:
            cursor = self.text_edit.textCursor()
            if cursor.hasSelection():
                self._selection_start = cursor.selectionStart()
                self._selection_end = cursor.selectionEnd()
            else:
                self._selection_start = 0
                self._selection_end = 0

    def _update_selection_radio_state(self):
        """Enable/disable Selection radio based on whether there's a selection"""
        has_selection = self._selection_end > self._selection_start
        self.selection_radio.setEnabled(has_selection)
        if not has_selection and self.selection_radio.isChecked():
            self.current_tab_radio.setChecked(True)

    def _on_regex_toggled(self, checked):
        """Handle regex checkbox toggle"""
        # Whole words doesn't work with regex mode
        if checked:
            self.whole_words_cb.setChecked(False)
            self.whole_words_cb.setEnabled(False)
        else:
            self.whole_words_cb.setEnabled(True)
        # Clear highlights when toggling
        self.clear_all_highlights()
        self._clear_results_table()

    def _show_regex_help(self):
        """Show a dialog with regex help"""
        help_text = """<h3>Regular Expression Quick Reference</h3>
<table>
<tr><td><b>.</b></td><td>Any single character</td></tr>
<tr><td><b>*</b></td><td>Zero or more of preceding</td></tr>
<tr><td><b>+</b></td><td>One or more of preceding</td></tr>
<tr><td><b>?</b></td><td>Zero or one of preceding</td></tr>
<tr><td><b>^</b></td><td>Start of line</td></tr>
<tr><td><b>$</b></td><td>End of line</td></tr>
<tr><td><b>\\d</b></td><td>Any digit (0-9)</td></tr>
<tr><td><b>\\w</b></td><td>Word character (a-z, A-Z, 0-9, _)</td></tr>
<tr><td><b>\\s</b></td><td>Whitespace (space, tab, newline)</td></tr>
<tr><td><b>[abc]</b></td><td>Any of a, b, or c</td></tr>
<tr><td><b>[^abc]</b></td><td>Not a, b, or c</td></tr>
<tr><td><b>(abc)</b></td><td>Capture group</td></tr>
<tr><td><b>a|b</b></td><td>a or b</td></tr>
</table>
<br>
<b>Examples:</b><br>
• <code>\\d+</code> - one or more digits<br>
• <code>^#.*</code> - lines starting with #<br>
• <code>\\bword\\b</code> - "word" as whole word<br>
• <code>(cat|dog)</code> - "cat" or "dog"<br>
<br>
<b>Replace with groups:</b><br>
Use <code>\\1</code>, <code>\\2</code> etc. to reference captured groups.
"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Regex Help")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def _find_regex_matches(self, text, pattern, start_pos=0, end_pos=None):
        """Find all regex matches in text.
        Returns list of (start, end, matched_text) tuples."""
        matches = []
        flags = 0 if self.case_sensitive_cb.isChecked() else re.IGNORECASE

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            self.status_label.setText(f"Regex error: {e}")
            return []

        search_text = text if end_pos is None else text[:end_pos]
        for match in regex.finditer(search_text):
            if match.start() >= start_pos:
                matches.append((match.start(), match.end(), match.group()))
        return matches

    def closeEvent(self, event):
        """Clear highlights when dialog is closed"""
        self._clear_all_tab_highlights()
        super().closeEvent(event)
