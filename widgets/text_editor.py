"""
Main text editing widget.
Currently a simple wrapper around QTextEdit.
Includes markdown syntax highlighting support.
"""

import re
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFontMetrics, QSyntaxHighlighter, QTextCharFormat, QColor, QFont


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


class TextEditorWidget(QTextEdit):
    """
    Enhanced text editor widget.

    Currently wraps QTextEdit with tab width configuration.
    Supports:
    - Markdown syntax highlighting (toggleable)
    - Line numbers (future)
    - Code folding (future)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = None

        # Configure as plain text editor
        self.setAcceptRichText(False)

        # Set tab stop width to 4 spaces
        font_metrics = QFontMetrics(self.font())
        tab_width = 4 * font_metrics.horizontalAdvance(' ')
        self.setTabStopDistance(tab_width)

    def set_markdown_highlighting(self, enabled):
        """Enable or disable markdown syntax highlighting."""
        if enabled:
            if self.highlighter is None:
                # Block signals on both widget and document to prevent textChanged
                self.blockSignals(True)
                self.document().blockSignals(True)
                self.highlighter = MarkdownHighlighter(self.document())
                self.document().blockSignals(False)
                self.blockSignals(False)
        else:
            if self.highlighter is not None:
                # Block signals during highlighter removal as well
                self.blockSignals(True)
                self.document().blockSignals(True)
                self.highlighter.setDocument(None)
                self.highlighter = None
                self.document().blockSignals(False)
                self.blockSignals(False)
