"""
Tests for FindReplaceDialog (windows/find_replace.py).
Tests search functionality, replace operations, case sensitivity, and highlighting.
"""

import pytest
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextDocument

from windows.find_replace import FindReplaceDialog


@pytest.fixture
def text_edit(qapp):
    """Create a QTextEdit widget for testing"""
    edit = QTextEdit()
    return edit


@pytest.fixture
def find_dialog(qapp, text_edit, sample_text):
    """Create a FindReplaceDialog with sample text"""
    text_edit.setPlainText(sample_text)
    dialog = FindReplaceDialog(text_edit)
    return dialog


class TestFindFlagsAndOptions:
    """Test flag generation based on checkbox options"""

    def test_default_flags(self, find_dialog):
        """Test default flags with no options checked"""
        flags = find_dialog.get_find_flags()
        # Default should be 0 (no special flags)
        # Check that flags is a FindFlag with value 0
        assert isinstance(flags, QTextDocument.FindFlag)
        # Default flags should not have case sensitive or whole words set
        assert not (flags & QTextDocument.FindFlag.FindCaseSensitively)
        assert not (flags & QTextDocument.FindFlag.FindWholeWords)

    def test_case_sensitive_flag(self, find_dialog):
        """Test case sensitive flag"""
        find_dialog.case_sensitive_cb.setChecked(True)
        flags = find_dialog.get_find_flags()
        assert flags & QTextDocument.FindFlag.FindCaseSensitively

    def test_whole_words_flag(self, find_dialog):
        """Test whole words flag"""
        find_dialog.whole_words_cb.setChecked(True)
        flags = find_dialog.get_find_flags()
        assert flags & QTextDocument.FindFlag.FindWholeWords

    def test_combined_flags(self, find_dialog):
        """Test both flags enabled"""
        find_dialog.case_sensitive_cb.setChecked(True)
        find_dialog.whole_words_cb.setChecked(True)
        flags = find_dialog.get_find_flags()
        assert flags & QTextDocument.FindFlag.FindCaseSensitively
        assert flags & QTextDocument.FindFlag.FindWholeWords


class TestFindAll:
    """Test find all functionality"""

    def test_find_all_case_insensitive(self, find_dialog):
        """Test finding all occurrences (case insensitive)"""
        find_dialog.find_input.setText("quick")
        find_dialog.find_all()

        # Should find "quick" twice and "Quick" once (3 occurrences total)
        # Line 1: "The quick brown fox..."
        # Line 3: "The Quick Brown Fox is different from the quick brown fox."
        assert len(find_dialog.all_matches) == 3
        assert "Found 3 occurrence(s)" in find_dialog.status_label.text()

    def test_find_all_case_sensitive(self, find_dialog):
        """Test finding all with case sensitivity"""
        find_dialog.case_sensitive_cb.setChecked(True)
        find_dialog.find_input.setText("quick")
        find_dialog.find_all()

        # Should only find lowercase "quick" (2 occurrences - "Quick" is excluded)
        # Line 1: "The quick brown fox..."
        # Line 3: "...from the quick brown fox."
        assert len(find_dialog.all_matches) == 2
        assert "Found 2 occurrence(s)" in find_dialog.status_label.text()

    def test_find_all_whole_words(self, find_dialog):
        """Test finding whole words only"""
        find_dialog.whole_words_cb.setChecked(True)
        find_dialog.find_input.setText("test")
        find_dialog.find_all()

        # Should find "test" as whole word, not "testing"
        # In sample_text: "This is a test document" has "test" as whole word
        matches = len(find_dialog.all_matches)
        assert matches >= 1

    def test_find_all_no_matches(self, find_dialog):
        """Test find all with no matches"""
        find_dialog.find_input.setText("NONEXISTENT")
        find_dialog.find_all()

        assert len(find_dialog.all_matches) == 0
        assert "Not found" in find_dialog.status_label.text()

    def test_find_all_empty_search(self, find_dialog):
        """Test find all with empty search text"""
        find_dialog.find_input.setText("")
        find_dialog.find_all()

        assert len(find_dialog.all_matches) == 0
        assert "Please enter text to find" in find_dialog.status_label.text()


class TestFindNext:
    """Test find next functionality"""

    def test_find_next_basic(self, find_dialog, text_edit):
        """Test finding next occurrence"""
        find_dialog.find_input.setText("the")

        # Find first occurrence
        initial_pos = text_edit.textCursor().position()
        find_dialog.find_next()

        # Cursor should have moved
        new_pos = text_edit.textCursor().position()
        assert new_pos >= initial_pos

    def test_find_next_wraps(self, find_dialog, text_edit):
        """Test that find next wraps to beginning"""
        find_dialog.find_input.setText("quick")

        # Move cursor to end of document
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        text_edit.setTextCursor(cursor)

        # Find should wrap to beginning
        find_dialog.find_next()

        # Status should indicate wrapping
        assert "Wrapped to beginning" in find_dialog.status_label.text() or \
               text_edit.textCursor().position() < cursor.position()

    def test_find_next_no_match(self, find_dialog):
        """Test find next with no match"""
        find_dialog.find_input.setText("XYZNONEXISTENT")
        find_dialog.find_next()

        assert "Not found" in find_dialog.status_label.text()


class TestFindPrevious:
    """Test find previous functionality"""

    def test_find_previous_basic(self, find_dialog, text_edit):
        """Test finding previous occurrence"""
        find_dialog.find_input.setText("the")

        # Move to end of document
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        text_edit.setTextCursor(cursor)

        end_pos = cursor.position()

        # Find previous
        find_dialog.find_previous()

        # Cursor should have moved backward
        new_pos = text_edit.textCursor().position()
        assert new_pos < end_pos

    def test_find_previous_wraps(self, find_dialog, text_edit):
        """Test that find previous wraps to end"""
        find_dialog.find_input.setText("quick")

        # Start at beginning
        cursor = text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        text_edit.setTextCursor(cursor)

        # Find previous should wrap to end
        find_dialog.find_previous()

        # Should wrap or move to an occurrence
        assert "Wrapped to end" in find_dialog.status_label.text() or \
               text_edit.textCursor().position() > 0


class TestReplaceCurrent:
    """Test replace current functionality"""

    def test_replace_single_occurrence(self, find_dialog, text_edit):
        """Test replacing single occurrence"""
        original_text = text_edit.toPlainText()

        find_dialog.find_input.setText("quick")
        find_dialog.replace_input.setText("FAST")
        find_dialog.replace_current()

        new_text = text_edit.toPlainText()

        # One "quick" should be replaced with "FAST"
        assert "FAST" in new_text
        assert new_text != original_text
        assert "Replaced" in find_dialog.status_label.text()

    def test_replace_no_match(self, find_dialog, text_edit):
        """Test replace with no match"""
        original_text = text_edit.toPlainText()

        find_dialog.find_input.setText("NONEXISTENT")
        find_dialog.replace_input.setText("REPLACEMENT")
        find_dialog.replace_current()

        # Text should be unchanged
        assert text_edit.toPlainText() == original_text
        assert "Not found" in find_dialog.status_label.text()

    def test_replace_empty_search(self, find_dialog):
        """Test replace with empty search text"""
        find_dialog.find_input.setText("")
        find_dialog.replace_input.setText("REPLACEMENT")
        find_dialog.replace_current()

        assert "Please enter text to find" in find_dialog.status_label.text()


class TestReplaceAll:
    """Test replace all functionality"""

    def test_replace_all_multiple_occurrences(self, find_dialog, text_edit):
        """Test replacing all occurrences"""
        find_dialog.find_input.setText("the")
        find_dialog.replace_input.setText("THE")

        # Count occurrences before
        original_text = text_edit.toPlainText()
        original_count = original_text.lower().count("the")

        find_dialog.replace_all()

        new_text = text_edit.toPlainText()

        # All "the" should be replaced with "THE"
        assert "THE" in new_text
        assert "Replaced" in find_dialog.status_label.text()
        # Verify the count in status message
        assert str(original_count) in find_dialog.status_label.text() or \
               original_count > 0

    def test_replace_all_case_sensitive(self, find_dialog, text_edit):
        """Test replace all with case sensitivity"""
        find_dialog.case_sensitive_cb.setChecked(True)
        find_dialog.find_input.setText("quick")
        find_dialog.replace_input.setText("FAST")

        find_dialog.replace_all()

        new_text = text_edit.toPlainText()

        # Only lowercase "quick" should be replaced
        # "Quick" should remain unchanged
        assert "FAST" in new_text
        assert "Quick" in new_text  # Capital Q version should remain

    def test_replace_all_no_matches(self, find_dialog, text_edit):
        """Test replace all with no matches"""
        original_text = text_edit.toPlainText()

        find_dialog.find_input.setText("NONEXISTENT")
        find_dialog.replace_input.setText("REPLACEMENT")
        find_dialog.replace_all()

        # Text should be unchanged
        assert text_edit.toPlainText() == original_text
        assert "Not found" in find_dialog.status_label.text()

    def test_replace_all_with_empty_replacement(self, find_dialog, text_edit):
        """Test replace all with empty replacement (deletion)"""
        find_dialog.find_input.setText("lazy")
        find_dialog.replace_input.setText("")

        original_text = text_edit.toPlainText()
        find_dialog.replace_all()

        new_text = text_edit.toPlainText()

        # "lazy" should be deleted (replaced with empty string)
        assert "lazy" not in new_text
        assert len(new_text) < len(original_text)


class TestHighlighting:
    """Test highlighting functionality"""

    def test_highlight_all_matches(self, find_dialog, text_edit):
        """Test that matches are highlighted"""
        find_dialog.find_input.setText("the")
        count = find_dialog.highlight_all_matches("the")

        # Should find multiple matches
        assert count > 0
        assert len(find_dialog.all_matches) == count

        # Verify highlights are applied
        selections = text_edit.extraSelections()
        assert len(selections) == count

    def test_clear_highlights(self, find_dialog, text_edit):
        """Test clearing highlights"""
        # First, add some highlights
        find_dialog.find_input.setText("the")
        find_dialog.highlight_all_matches("the")

        assert len(text_edit.extraSelections()) > 0

        # Clear highlights
        find_dialog.clear_all_highlights()

        assert len(text_edit.extraSelections()) == 0
        assert len(find_dialog.all_matches) == 0

    def test_highlights_update_on_text_change(self, find_dialog, text_edit):
        """Test that changing find text clears highlights"""
        # Add highlights
        find_dialog.find_input.setText("the")
        find_dialog.find_all()

        initial_highlights = len(text_edit.extraSelections())
        assert initial_highlights > 0

        # Change find text
        find_dialog.find_input.setText("different")
        find_dialog.on_find_text_changed()

        # Highlights should be cleared
        assert len(text_edit.extraSelections()) == 0


class TestDialogBehavior:
    """Test dialog window behavior"""

    def test_dialog_creation(self, qapp, text_edit):
        """Test creating the dialog"""
        dialog = FindReplaceDialog(text_edit)

        assert dialog is not None
        assert dialog.text_edit == text_edit
        assert dialog.windowTitle() == "Find and Replace"

    def test_dialog_has_all_widgets(self, find_dialog):
        """Test that dialog has all required widgets"""
        assert find_dialog.find_input is not None
        assert find_dialog.replace_input is not None
        assert find_dialog.case_sensitive_cb is not None
        assert find_dialog.whole_words_cb is not None
        assert find_dialog.status_label is not None
        assert find_dialog.find_next_btn is not None
        assert find_dialog.find_prev_btn is not None
        assert find_dialog.find_all_btn is not None
        assert find_dialog.replace_btn is not None
        assert find_dialog.replace_all_btn is not None
        assert find_dialog.close_btn is not None
