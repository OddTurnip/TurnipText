"""
Pytest configuration and fixtures for TextEditor tests.
"""

import pytest
import sys
import os
from pathlib import Path
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add parent directory to path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt


@pytest.fixture(scope='session')
def qapp():
    """Create QApplication instance for all tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit the app here as it may be used by multiple tests


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup after test
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for testing"""
    file_path = os.path.join(temp_dir, 'test_file.txt')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('Initial test content\n')
    return file_path


@pytest.fixture
def mock_messagebox():
    """Mock QMessageBox to prevent dialogs during tests"""
    with patch.object(QMessageBox, 'critical', return_value=None):
        with patch.object(QMessageBox, 'warning', return_value=None):
            with patch.object(QMessageBox, 'information', return_value=None):
                with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                    yield


@pytest.fixture
def sample_text():
    """Provide sample text for testing"""
    return """The quick brown fox jumps over the lazy dog.
This is a test document with multiple lines.
The Quick Brown Fox is different from the quick brown fox.
Search and replace functionality should work correctly.
"""
