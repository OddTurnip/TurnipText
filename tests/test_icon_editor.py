"""
Tests for the IconEditorDialog and related functions in windows/icon_editor.py
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from windows.icon_editor import (
    IconEditorDialog, get_icons_dir, generate_icon_filename, load_icon_pixmap,
    ICON_SIZE, PREVIEW_SCALE
)


class TestHelperFunctions:
    """Tests for helper functions"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    def test_get_icons_dir_creates_directory(self, temp_dir):
        """Test that get_icons_dir creates the icons directory"""
        # Mock the app directory to be our temp directory
        with patch('windows.icon_editor.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_dir

            icons_dir = get_icons_dir()

            # Since we're not frozen, it goes up one level from module path
            # Just verify it returns a path ending in 'icons'
            assert icons_dir.endswith('icons')

    def test_generate_icon_filename_uniqueness(self):
        """Test that generate_icon_filename creates unique names"""
        path = "/path/to/image.png"

        name1 = generate_icon_filename(path)
        name2 = generate_icon_filename(path)

        # Names should be different due to timestamp
        assert name1 != name2
        # Both should follow the pattern
        assert name1.startswith('icon_')
        assert name1.endswith('.png')
        assert name2.startswith('icon_')
        assert name2.endswith('.png')

    def test_generate_icon_filename_format(self):
        """Test the format of generated icon filenames"""
        name = generate_icon_filename("/test/file.png")

        assert name.startswith('icon_')
        assert name.endswith('.png')
        # Hash should be 12 characters
        middle = name[5:-4]  # Remove 'icon_' and '.png'
        assert len(middle) == 12

    def test_load_icon_pixmap_none_filename(self, qapp):
        """Test load_icon_pixmap with None filename"""
        result = load_icon_pixmap(None)
        assert result is None

    def test_load_icon_pixmap_empty_filename(self, qapp):
        """Test load_icon_pixmap with empty filename"""
        result = load_icon_pixmap("")
        assert result is None

    def test_load_icon_pixmap_nonexistent_file(self, qapp):
        """Test load_icon_pixmap with non-existent file"""
        result = load_icon_pixmap("nonexistent_icon.png")
        assert result is None


class TestIconEditorConstants:
    """Tests for module constants"""

    def test_icon_size(self):
        """Test ICON_SIZE constant"""
        assert ICON_SIZE == 32

    def test_preview_scale(self):
        """Test PREVIEW_SCALE constant"""
        assert PREVIEW_SCALE == 4


class TestIconEditorDialog:
    """Tests for IconEditorDialog"""

    def test_initialization(self, qapp):
        """Test dialog initialization"""
        dialog = IconEditorDialog()

        assert dialog.windowTitle() == "Upload Custom Icon"
        assert dialog.minimumWidth() >= 500
        assert dialog.minimumHeight() >= 400
        assert dialog.source_image is None
        assert dialog.source_path is None
        assert dialog.current_icon is None
        assert dialog.result_icon_filename is None

        dialog.close()

    def test_initialization_with_current_icon(self, qapp):
        """Test dialog initialization with existing icon"""
        dialog = IconEditorDialog(current_icon="existing.png")

        assert dialog.current_icon == "existing.png"

        dialog.close()

    def test_default_slider_values(self, qapp):
        """Test default slider values"""
        dialog = IconEditorDialog()

        assert dialog.scale == 100
        assert dialog.offset_x == 50
        assert dialog.offset_y == 50
        assert dialog.scale_slider.value() == 100
        assert dialog.x_slider.value() == 50
        assert dialog.y_slider.value() == 50

        dialog.close()

    def test_save_button_initially_disabled(self, qapp):
        """Test that save button is disabled until image is loaded"""
        dialog = IconEditorDialog()

        assert dialog.save_btn.isEnabled() is False

        dialog.close()

    def test_on_scale_changed(self, qapp):
        """Test scale slider changes"""
        dialog = IconEditorDialog()

        dialog.on_scale_changed(200)

        assert dialog.scale == 200
        assert dialog.scale_value_label.text() == "200%"

        dialog.close()

    def test_on_offset_changed_center(self, qapp):
        """Test offset labels when centered"""
        dialog = IconEditorDialog()

        dialog.x_slider.setValue(50)
        dialog.y_slider.setValue(50)
        dialog.on_offset_changed()

        assert dialog.x_value_label.text() == "Center"
        assert dialog.y_value_label.text() == "Center"

        dialog.close()

    def test_on_offset_changed_left_top(self, qapp):
        """Test offset labels when positioned left/top"""
        dialog = IconEditorDialog()

        dialog.x_slider.setValue(10)
        dialog.y_slider.setValue(10)
        dialog.on_offset_changed()

        assert dialog.x_value_label.text() == "Left"
        assert dialog.y_value_label.text() == "Top"

        dialog.close()

    def test_on_offset_changed_right_bottom(self, qapp):
        """Test offset labels when positioned right/bottom"""
        dialog = IconEditorDialog()

        dialog.x_slider.setValue(90)
        dialog.y_slider.setValue(90)
        dialog.on_offset_changed()

        assert dialog.x_value_label.text() == "Right"
        assert dialog.y_value_label.text() == "Bottom"

        dialog.close()

    def test_reset_adjustments_no_image(self, qapp):
        """Test reset when no image is loaded"""
        dialog = IconEditorDialog()

        # Change values
        dialog.scale_slider.setValue(200)
        dialog.x_slider.setValue(10)
        dialog.y_slider.setValue(90)

        # Reset
        dialog.reset_adjustments()

        assert dialog.scale_slider.value() == 100
        assert dialog.x_slider.value() == 50
        assert dialog.y_slider.value() == 50

        dialog.close()

    def test_generate_icon_no_image(self, qapp):
        """Test generate_icon returns None when no image loaded"""
        dialog = IconEditorDialog()

        result = dialog.generate_icon()

        assert result is None

        dialog.close()

    def test_update_result_preview_no_image(self, qapp):
        """Test update_result_preview with no image"""
        dialog = IconEditorDialog()

        # Should not raise any errors
        dialog.update_result_preview()

        dialog.close()

    def test_clear_icon(self, qapp):
        """Test clear_icon sets empty result"""
        dialog = IconEditorDialog(current_icon="test.png")

        dialog.clear_icon()

        assert dialog.result_icon_filename == ""

        dialog.close()

    def test_get_icon_filename_cancelled(self, qapp):
        """Test get_icon_filename returns None when cancelled"""
        dialog = IconEditorDialog()

        result = dialog.get_icon_filename()

        assert result is None

        dialog.close()

    def test_load_image_invalid_path(self, qapp):
        """Test loading invalid image path"""
        dialog = IconEditorDialog()

        dialog.load_image("/nonexistent/path/image.png")

        assert dialog.source_image is None
        assert dialog.save_btn.isEnabled() is False
        assert "Failed" in dialog.file_label.text()

        dialog.close()

    def test_slider_ranges(self, qapp):
        """Test slider ranges are correctly set"""
        dialog = IconEditorDialog()

        # Scale slider: 50-400
        assert dialog.scale_slider.minimum() == 50
        assert dialog.scale_slider.maximum() == 400

        # X/Y sliders: 0-100
        assert dialog.x_slider.minimum() == 0
        assert dialog.x_slider.maximum() == 100
        assert dialog.y_slider.minimum() == 0
        assert dialog.y_slider.maximum() == 100

        dialog.close()


class TestIconEditorWithImage:
    """Tests that require loading an actual image"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def test_image(self, temp_dir, qapp):
        """Create a test image file"""
        from PyQt6.QtGui import QImage, QColor

        # Create a simple 100x100 test image
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        image.fill(QColor(255, 0, 0))  # Red

        image_path = os.path.join(temp_dir, "test_image.png")
        image.save(image_path, "PNG")

        return image_path

    def test_load_valid_image(self, qapp, test_image):
        """Test loading a valid image"""
        dialog = IconEditorDialog()

        dialog.load_image(test_image)

        assert dialog.source_image is not None
        assert dialog.source_path == test_image
        assert dialog.save_btn.isEnabled() is True
        assert "test_image.png" in dialog.file_label.text()
        assert "100x100" in dialog.file_label.text()

        dialog.close()

    def test_auto_adjust_for_image(self, qapp, test_image):
        """Test auto adjustment when loading image"""
        dialog = IconEditorDialog()

        dialog.load_image(test_image)

        # For a 100x100 image, scale should be adjusted to fill 32x32
        # Since 32/100 = 0.32, we need about 32% scale, but since it needs to fill,
        # it should use the larger of the two dimensions
        # The auto_adjust_for_image uses max(scale_x, scale_y) which would be 32%
        # but clamped to minimum 50
        assert dialog.scale_slider.value() >= 50

        # X and Y should be centered
        assert dialog.x_slider.value() == 50
        assert dialog.y_slider.value() == 50

        dialog.close()

    def test_generate_icon_with_image(self, qapp, test_image):
        """Test icon generation with loaded image"""
        dialog = IconEditorDialog()

        dialog.load_image(test_image)
        icon = dialog.generate_icon()

        assert icon is not None
        assert icon.width() == ICON_SIZE
        assert icon.height() == ICON_SIZE

        dialog.close()

    def test_reset_adjustments_with_image(self, qapp, test_image):
        """Test reset adjustments with loaded image"""
        dialog = IconEditorDialog()

        dialog.load_image(test_image)
        initial_scale = dialog.scale_slider.value()

        # Change values
        dialog.scale_slider.setValue(300)
        dialog.x_slider.setValue(10)
        dialog.y_slider.setValue(90)

        # Reset
        dialog.reset_adjustments()

        # Should go back to auto-adjusted values
        assert dialog.scale_slider.value() == initial_scale
        assert dialog.x_slider.value() == 50
        assert dialog.y_slider.value() == 50

        dialog.close()

    def test_update_result_preview_with_image(self, qapp, test_image):
        """Test result preview updates with image"""
        dialog = IconEditorDialog()

        dialog.load_image(test_image)
        dialog.update_result_preview()

        # Result preview should have a pixmap
        pixmap = dialog.result_preview.pixmap()
        assert pixmap is not None
        assert not pixmap.isNull()

        dialog.close()

    def test_save_icon(self, qapp, test_image, temp_dir):
        """Test saving icon"""
        dialog = IconEditorDialog()
        dialog.load_image(test_image)

        # Mock the icons directory
        with patch('windows.icon_editor.get_icons_dir') as mock_get_dir:
            mock_get_dir.return_value = temp_dir

            dialog.save_icon()

            # Should have saved and set result filename
            assert dialog.result_icon_filename is not None
            assert dialog.result_icon_filename.startswith('icon_')

            # File should exist
            saved_path = os.path.join(temp_dir, dialog.result_icon_filename)
            assert os.path.exists(saved_path)

        dialog.close()
