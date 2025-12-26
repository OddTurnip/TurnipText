"""
Main text editing widget.
Enhanced QPlainTextEdit with line numbers and markdown highlighting.
"""

import re
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtGui import (
    QFontMetrics, QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
    QPainter, QTextFormat
)
from PyQt6.QtCore import QRect, QSize, Qt


class MarkdownHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for Markdown formatting.

    Supported:
    - Headers: # bold red, ## bold orange, ### and beyond orange
    - Bold: **text** or __text__
    - Italic: *text* or _text_
    - Bold+Italic: ***text*** or ___text___
    - Blockquotes: > text (dark grey)
    - Code: `text` or ```block``` (green)
    - Escape: backslash escapes special characters

    Formatting characters are shown and styled along with the text.
    """

    def __init__(self, document):
        super().__init__(document)
        self._setup_formats()

    def _setup_formats(self):
        """Setup text formats for different markdown elements."""
        # Header 1: bold red
        self.h1_format = QTextCharFormat()
        self.h1_format.setFontWeight(QFont.Weight.Bold)
        self.h1_format.setForeground(QColor("#CC0000"))

        # Header 2: bold orange
        self.h2_format = QTextCharFormat()
        self.h2_format.setFontWeight(QFont.Weight.Bold)
        self.h2_format.setForeground(QColor("#DD6600"))

        # Header 3+: orange (not bold)
        self.h3_format = QTextCharFormat()
        self.h3_format.setForeground(QColor("#DD6600"))

        # Bold format
        self.bold_format = QTextCharFormat()
        self.bold_format.setFontWeight(QFont.Weight.Bold)

        # Italic format
        self.italic_format = QTextCharFormat()
        self.italic_format.setFontItalic(True)

        # Bold+Italic format
        self.bold_italic_format = QTextCharFormat()
        self.bold_italic_format.setFontWeight(QFont.Weight.Bold)
        self.bold_italic_format.setFontItalic(True)

        # Blockquote format: dark grey
        self.blockquote_format = QTextCharFormat()
        self.blockquote_format.setForeground(QColor("#555555"))

        # Code format: green
        self.code_format = QTextCharFormat()
        self.code_format.setForeground(QColor("#008800"))

    def highlightBlock(self, text):
        """Apply highlighting to a single block of text."""
        # Track escaped characters (positions to skip)
        escaped = set()
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text):
                escaped.add(i + 1)  # The next character is escaped
                i += 2
            else:
                i += 1

        # Check for headers at start of line (must start with # followed by space or more #)
        header_match = re.match(r'^(#{1,6})\s', text)
        if header_match and 0 not in escaped:
            level = len(header_match.group(1))
            if level == 1:
                self.setFormat(0, len(text), self.h1_format)
            elif level == 2:
                self.setFormat(0, len(text), self.h2_format)
            else:
                self.setFormat(0, len(text), self.h3_format)
            return  # Headers don't have inline formatting

        # Check for blockquote (line starting with >)
        if text.startswith('>') and 0 not in escaped:
            self.setFormat(0, len(text), self.blockquote_format)
            return  # Blockquotes don't have inline formatting

        # Apply inline formatting
        self._apply_inline_formatting(text, escaped)

    def _apply_inline_formatting(self, text, escaped):
        """Apply inline formatting (bold, italic, code) to text."""
        # Track all formatted regions to prevent overlapping
        formatted_regions = []

        # Process code blocks first (they prevent other formatting inside)
        pos = 0
        while pos < len(text):
            if text[pos] == '`' and pos not in escaped:
                # Find closing backtick
                end = pos + 1
                while end < len(text):
                    if text[end] == '`' and end not in escaped:
                        # Found closing backtick
                        self.setFormat(pos, end - pos + 1, self.code_format)
                        formatted_regions.append((pos, end))
                        pos = end + 1
                        break
                    end += 1
                else:
                    pos += 1
            else:
                pos += 1

        # Process bold+italic (*** or ___) - must be done before bold and italic
        formatted_regions.extend(
            self._apply_pattern(text, escaped, r'\*\*\*(.+?)\*\*\*', self.bold_italic_format, formatted_regions)
        )
        formatted_regions.extend(
            self._apply_pattern(text, escaped, r'___(.+?)___', self.bold_italic_format, formatted_regions)
        )

        # Process bold (** or __)
        formatted_regions.extend(
            self._apply_pattern(text, escaped, r'\*\*(.+?)\*\*', self.bold_format, formatted_regions)
        )
        formatted_regions.extend(
            self._apply_pattern(text, escaped, r'__(.+?)__', self.bold_format, formatted_regions)
        )

        # Process italic (* or _)
        # Need to be careful not to match ** or __
        self._apply_single_emphasis(text, escaped, '*', formatted_regions)
        self._apply_single_emphasis(text, escaped, '_', formatted_regions)

    def _apply_pattern(self, text, escaped, pattern, fmt, excluded_regions):
        """Apply a regex pattern format, respecting escaped chars and excluded regions.
        Returns list of newly formatted regions."""
        new_regions = []
        for match in re.finditer(pattern, text):
            start = match.start()
            end = match.end() - 1  # Convert to inclusive end for overlap check

            # Check if start delimiter is escaped
            if start in escaped:
                continue

            # Check if overlaps with any excluded region
            overlaps = False
            for region_start, region_end in excluded_regions:
                if start <= region_end and end >= region_start:
                    overlaps = True
                    break
            if overlaps:
                continue

            self.setFormat(start, match.end() - start, fmt)
            new_regions.append((start, end))

        return new_regions

    def _apply_single_emphasis(self, text, escaped, char, excluded_regions):
        """Apply single emphasis (* or _) avoiding double/triple emphasis."""
        pos = 0
        while pos < len(text):
            if text[pos] == char and pos not in escaped:
                # Check it's not part of ** or ***
                before = text[pos-1] if pos > 0 else ''
                after = text[pos+1] if pos + 1 < len(text) else ''

                if before == char or after == char:
                    pos += 1
                    continue

                # Find closing single char (not followed/preceded by same char)
                end = pos + 1
                found = False
                while end < len(text):
                    if text[end] == char and end not in escaped:
                        # Check it's not part of ** or ***
                        before_end = text[end-1] if end > 0 else ''
                        after_end = text[end+1] if end + 1 < len(text) else ''

                        if before_end != char and after_end != char:
                            # Found closing delimiter
                            # Check if overlaps with any excluded region
                            overlaps = False
                            for region_start, region_end in excluded_regions:
                                if pos <= region_end and end >= region_start:
                                    overlaps = True
                                    break

                            if not overlaps:
                                self.setFormat(pos, end - pos + 1, self.italic_format)
                            found = True
                            pos = end + 1
                            break
                    end += 1

                if not found:
                    pos += 1
            else:
                pos += 1


class LineNumberArea(QWidget):
    """Widget for displaying line numbers alongside text editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class TextEditorWidget(QPlainTextEdit):
    """
    Enhanced text editor widget with line numbers.

    Features:
    - Line numbers in left margin
    - Markdown syntax highlighting (toggleable)
    - Tab width configuration
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = None
        self._external_selections = []  # For find/replace highlights
        self._line_numbers_visible = True  # Track line number visibility

        # Set monospace font for the editor
        editor_font = QFont("Consolas", 11)
        editor_font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(editor_font)

        # Create line number area
        self.line_number_area = LineNumberArea(self)

        # Connect signals for line number updates
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        # Initialize line number area width
        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Set tab stop width to 4 spaces
        font_metrics = QFontMetrics(self.font())
        tab_width = 4 * font_metrics.horizontalAdvance(' ')
        self.setTabStopDistance(tab_width)

    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        if not self._line_numbers_visible:
            return 0

        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1

        # Minimum 3 digits width, plus padding (left + right)
        digits = max(3, digits)
        left_padding = 8
        right_padding = 12
        space = left_padding + self.fontMetrics().horizontalAdvance('9') * digits + right_padding
        return space

    def update_line_number_area_width(self, _):
        """Update the viewport margins to accommodate line numbers."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the line number area when scrolling or editing."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize to adjust line number area."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                 self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        """Highlight the line where the cursor is, preserving external selections."""
        extra_selections = []

        # Add current line highlight (only if visible and no external selections like search results)
        if self._line_numbers_visible and not self.isReadOnly() and not self._external_selections:
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.GlobalColor.yellow).lighter(180)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        # Add any external selections (from find/replace)
        extra_selections.extend(self._external_selections)

        self.setExtraSelections(extra_selections)

    def setExtraSelections(self, selections):
        """Override to track external selections."""
        # Check if this is being called from outside (not from highlight_current_line)
        # by checking if we're in the highlight_current_line call stack
        import inspect
        caller = inspect.stack()[1].function
        if caller != 'highlight_current_line':
            self._external_selections = selections
            # Merge with current line highlight
            self.highlight_current_line()
        else:
            # Called from highlight_current_line, just set directly
            super().setExtraSelections(selections)

    def line_number_area_paint_event(self, event):
        """Paint the line numbers."""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#F0F0F0"))

        # Use Calibri font for line numbers
        line_number_font = QFont("Calibri", 10)
        painter.setFont(line_number_font)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        right_padding = 12  # Padding to the right of line numbers

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#808080"))
                painter.drawText(0, top, self.line_number_area.width() - right_padding,
                                self.fontMetrics().height(),
                                Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def set_markdown_highlighting(self, enabled):
        """Enable or disable markdown syntax highlighting.

        Note: Signal blocking is not needed here because TextEditorTab.on_text_changed()
        compares actual text content against a saved baseline. Formatting changes from
        the highlighter don't modify text content, so they won't trigger false positives.
        """
        if enabled:
            if self.highlighter is None:
                self.highlighter = MarkdownHighlighter(self.document())
        else:
            if self.highlighter is not None:
                self.highlighter.setDocument(None)
                self.highlighter = None

    def set_line_numbers_visible(self, visible):
        """Show or hide line numbers and current line highlighting."""
        self._line_numbers_visible = visible
        self.line_number_area.setVisible(visible)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
