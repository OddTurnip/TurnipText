"""
Icon Editor Dialog for custom tab icons.
Allows users to upload, scale, and position images to create 32x32 icons.
"""

import os
import hashlib
import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFileDialog, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor


# Icon size constants
ICON_SIZE = 32
PREVIEW_SCALE = 4  # Show preview at 4x size for easier editing


def get_icons_dir():
    """Get the icons directory, creating it if necessary."""
    import sys
    if getattr(sys, 'frozen', False):
        # Running as compiled exe (PyInstaller)
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running as script
        app_dir = os.path.dirname(os.path.dirname(__file__))

    icons_dir = os.path.join(app_dir, 'icons')
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
    return icons_dir


def generate_icon_filename(source_path):
    """Generate a unique filename for a processed icon."""
    # Use hash of source path + timestamp for uniqueness
    unique_str = f"{source_path}_{time.time()}"
    hash_str = hashlib.md5(unique_str.encode()).hexdigest()[:12]
    return f"icon_{hash_str}.png"


def load_icon_pixmap(icon_filename):
    """Load an icon pixmap from the icons directory.

    Returns QPixmap if found, None otherwise.
    """
    if not icon_filename:
        return None

    icon_path = os.path.join(get_icons_dir(), icon_filename)
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            return pixmap
    return None


class IconEditorDialog(QDialog):
    """Dialog for creating custom 32x32 icons from images."""

    def __init__(self, parent=None, current_icon=None):
        super().__init__(parent)
        self.setWindowTitle("Upload Custom Icon")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.source_image = None  # Original QImage
        self.source_path = None   # Path to source file
        self.current_icon = current_icon  # Existing icon filename
        self.result_icon_filename = None  # Will be set on accept

        # Editor state
        self.scale = 100  # Percentage (100 = fit to 32x32)
        self.offset_x = 50  # Percentage (50 = centered)
        self.offset_y = 50  # Percentage (50 = centered)

        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()

        # Styles
        button_style = """
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #F8F8F8, stop:1 #E0E0E0);
                border: 1px solid #B0B0B0;
                border-radius: 4px;
                padding: 6px 16px;
                min-width: 80px;
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

        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #B0B0B0;
                height: 8px;
                background: #E0E0E0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: 1px solid #1976D2;
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #42A5F5;
            }
        """

        # File selection section
        file_group = QGroupBox("Source Image")
        file_layout = QHBoxLayout()

        self.file_label = QLabel("No image selected")
        self.file_label.setStyleSheet("color: #666666;")
        file_layout.addWidget(self.file_label, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setStyleSheet(button_style)
        browse_btn.clicked.connect(self.browse_image)
        file_layout.addWidget(browse_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QHBoxLayout()

        # Source preview (scaled down to fit)
        source_frame = QVBoxLayout()
        source_label = QLabel("Original:")
        source_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        source_frame.addWidget(source_label)

        self.source_preview = QLabel()
        self.source_preview.setFixedSize(128, 128)
        self.source_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.source_preview.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        source_frame.addWidget(self.source_preview)
        preview_layout.addLayout(source_frame)

        # Arrow
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 24px; color: #666666;")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(arrow_label)

        # Result preview (at 4x for visibility)
        result_frame = QVBoxLayout()
        result_label = QLabel(f"Result ({ICON_SIZE}x{ICON_SIZE}):")
        result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_frame.addWidget(result_label)

        self.result_preview = QLabel()
        self.result_preview.setFixedSize(ICON_SIZE * PREVIEW_SCALE, ICON_SIZE * PREVIEW_SCALE)
        self.result_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_preview.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
        """)
        result_frame.addWidget(self.result_preview)
        preview_layout.addLayout(result_frame)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Controls section
        controls_group = QGroupBox("Adjustments")
        controls_layout = QVBoxLayout()

        # Scale slider
        scale_layout = QHBoxLayout()
        scale_label = QLabel("Scale:")
        scale_label.setFixedWidth(80)
        scale_layout.addWidget(scale_label)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(50, 400)  # 50% to 400%
        self.scale_slider.setValue(100)
        self.scale_slider.setStyleSheet(slider_style)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        scale_layout.addWidget(self.scale_slider)

        self.scale_value_label = QLabel("100%")
        self.scale_value_label.setFixedWidth(50)
        scale_layout.addWidget(self.scale_value_label)

        controls_layout.addLayout(scale_layout)

        # X offset slider
        x_layout = QHBoxLayout()
        x_label = QLabel("Position X:")
        x_label.setFixedWidth(80)
        x_layout.addWidget(x_label)

        self.x_slider = QSlider(Qt.Orientation.Horizontal)
        self.x_slider.setRange(0, 100)
        self.x_slider.setValue(50)
        self.x_slider.setStyleSheet(slider_style)
        self.x_slider.valueChanged.connect(self.on_offset_changed)
        x_layout.addWidget(self.x_slider)

        self.x_value_label = QLabel("Center")
        self.x_value_label.setFixedWidth(50)
        x_layout.addWidget(self.x_value_label)

        controls_layout.addLayout(x_layout)

        # Y offset slider
        y_layout = QHBoxLayout()
        y_label = QLabel("Position Y:")
        y_label.setFixedWidth(80)
        y_layout.addWidget(y_label)

        self.y_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_slider.setRange(0, 100)
        self.y_slider.setValue(50)
        self.y_slider.setStyleSheet(slider_style)
        self.y_slider.valueChanged.connect(self.on_offset_changed)
        y_layout.addWidget(self.y_slider)

        self.y_value_label = QLabel("Center")
        self.y_value_label.setFixedWidth(50)
        y_layout.addWidget(self.y_value_label)

        controls_layout.addLayout(y_layout)

        # Reset button
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        reset_btn = QPushButton("Reset to Center")
        reset_btn.setStyleSheet(button_style)
        reset_btn.clicked.connect(self.reset_adjustments)
        reset_layout.addWidget(reset_btn)
        controls_layout.addLayout(reset_layout)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Clear icon option (if there's a current icon)
        if self.current_icon:
            clear_layout = QHBoxLayout()
            clear_label = QLabel("Current icon will be replaced.")
            clear_label.setStyleSheet("color: #666666; font-style: italic;")
            clear_layout.addWidget(clear_label)
            clear_layout.addStretch()

            clear_btn = QPushButton("Remove Icon")
            clear_btn.setStyleSheet(button_style)
            clear_btn.clicked.connect(self.clear_icon)
            clear_layout.addWidget(clear_btn)

            layout.addLayout(clear_layout)

        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(button_style)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.save_btn = QPushButton("Save Icon")
        self.save_btn.setStyleSheet(button_style)
        self.save_btn.clicked.connect(self.save_icon)
        self.save_btn.setEnabled(False)  # Disabled until image is loaded
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def browse_image(self):
        """Open file dialog to select an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.ico);;All Files (*)"
        )

        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        """Load an image from the given path."""
        image = QImage(file_path)

        if image.isNull():
            self.file_label.setText("Failed to load image")
            self.file_label.setStyleSheet("color: #D32F2F;")
            self.source_image = None
            self.save_btn.setEnabled(False)
            return

        self.source_image = image
        self.source_path = file_path

        # Update file label
        filename = os.path.basename(file_path)
        size_str = f"{image.width()}x{image.height()}"
        self.file_label.setText(f"{filename} ({size_str})")
        self.file_label.setStyleSheet("color: #333333;")

        # Update source preview
        scaled = image.scaled(
            128, 128,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.source_preview.setPixmap(QPixmap.fromImage(scaled))

        # Reset adjustments based on aspect ratio
        self.auto_adjust_for_image()

        # Enable save button
        self.save_btn.setEnabled(True)

        # Update result preview
        self.update_result_preview()

    def auto_adjust_for_image(self):
        """Auto-adjust scale and position based on image dimensions."""
        if not self.source_image:
            return

        w = self.source_image.width()
        h = self.source_image.height()

        # Calculate scale to fit the smaller dimension to ICON_SIZE
        # This ensures we can crop rather than having empty space
        scale_x = ICON_SIZE / w * 100
        scale_y = ICON_SIZE / h * 100

        # Use the larger scale factor so the image fills the icon
        optimal_scale = max(scale_x, scale_y)

        # Clamp to slider range
        optimal_scale = max(50, min(400, int(optimal_scale)))

        self.scale_slider.setValue(optimal_scale)
        self.x_slider.setValue(50)
        self.y_slider.setValue(50)

    def reset_adjustments(self):
        """Reset all adjustments to defaults."""
        if self.source_image:
            self.auto_adjust_for_image()
        else:
            self.scale_slider.setValue(100)
            self.x_slider.setValue(50)
            self.y_slider.setValue(50)

    def on_scale_changed(self, value):
        """Handle scale slider change."""
        self.scale = value
        self.scale_value_label.setText(f"{value}%")
        self.update_result_preview()

    def on_offset_changed(self):
        """Handle X/Y offset slider changes."""
        self.offset_x = self.x_slider.value()
        self.offset_y = self.y_slider.value()

        # Update labels
        x_text = "Left" if self.offset_x < 40 else "Right" if self.offset_x > 60 else "Center"
        y_text = "Top" if self.offset_y < 40 else "Bottom" if self.offset_y > 60 else "Center"
        self.x_value_label.setText(x_text)
        self.y_value_label.setText(y_text)

        self.update_result_preview()

    def update_result_preview(self):
        """Update the result preview based on current settings."""
        if not self.source_image:
            self.result_preview.clear()
            return

        result = self.generate_icon()
        if result:
            # Scale up for preview
            preview = result.scaled(
                ICON_SIZE * PREVIEW_SCALE,
                ICON_SIZE * PREVIEW_SCALE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation  # Nearest neighbor for pixel art look
            )
            self.result_preview.setPixmap(QPixmap.fromImage(preview))

    def generate_icon(self):
        """Generate the final 32x32 icon based on current settings.

        Returns a QImage of the icon.
        """
        if not self.source_image:
            return None

        src_w = self.source_image.width()
        src_h = self.source_image.height()

        # Calculate scaled dimensions
        scale_factor = self.scale / 100.0
        scaled_w = int(src_w * scale_factor)
        scaled_h = int(src_h * scale_factor)

        # Ensure minimum size
        scaled_w = max(1, scaled_w)
        scaled_h = max(1, scaled_h)

        # Scale the source image
        scaled = self.source_image.scaled(
            scaled_w, scaled_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Calculate crop position based on offset percentages
        # offset_x/y = 0 means left/top edge, 100 means right/bottom edge, 50 means center
        max_offset_x = max(0, scaled_w - ICON_SIZE)
        max_offset_y = max(0, scaled_h - ICON_SIZE)

        crop_x = int(max_offset_x * self.offset_x / 100)
        crop_y = int(max_offset_y * self.offset_y / 100)

        # Create result image with transparent background
        result = QImage(ICON_SIZE, ICON_SIZE, QImage.Format.Format_ARGB32)
        result.fill(QColor(0, 0, 0, 0))

        # Calculate where to place the scaled image if it's smaller than ICON_SIZE
        paste_x = max(0, (ICON_SIZE - scaled_w) // 2)
        paste_y = max(0, (ICON_SIZE - scaled_h) // 2)

        # Copy pixels from scaled image to result
        painter = QPainter(result)

        # Define source and destination rectangles
        src_rect = QRect(crop_x, crop_y, min(scaled_w - crop_x, ICON_SIZE), min(scaled_h - crop_y, ICON_SIZE))
        dst_rect = QRect(paste_x, paste_y, src_rect.width(), src_rect.height())

        painter.drawImage(dst_rect, scaled, src_rect)
        painter.end()

        return result

    def save_icon(self):
        """Save the icon and accept the dialog."""
        icon_image = self.generate_icon()
        if not icon_image:
            return

        # Generate filename
        filename = generate_icon_filename(self.source_path)
        icon_path = os.path.join(get_icons_dir(), filename)

        # Save the icon
        if icon_image.save(icon_path, "PNG"):
            self.result_icon_filename = filename
            self.accept()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", "Failed to save icon file.")

    def clear_icon(self):
        """Clear the current icon (set result to empty string to indicate removal)."""
        self.result_icon_filename = ""  # Empty string means remove
        self.accept()

    def get_icon_filename(self):
        """Get the result icon filename after dialog closes.

        Returns:
            - None if dialog was cancelled
            - "" (empty string) if icon should be removed
            - filename string if a new icon was created
        """
        return self.result_icon_filename
