"""
Main text editing widget.
Currently a simple wrapper around QTextEdit.
Future: Add markdown syntax highlighting, line numbers, etc.
"""

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFontMetrics


class TextEditorWidget(QTextEdit):
    """
    Enhanced text editor widget.

    Currently wraps QTextEdit with tab width configuration.
    Future enhancements:
    - Markdown syntax highlighting
    - Line numbers
    - Code folding
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Configure as plain text editor
        self.setAcceptRichText(False)

        # Set tab stop width to 4 spaces
        font_metrics = QFontMetrics(self.font())
        tab_width = 4 * font_metrics.horizontalAdvance(' ')
        self.setTabStopDistance(tab_width)
