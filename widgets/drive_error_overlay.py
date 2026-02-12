"""
Overlay widget displayed on top of a tab's editor when its network drive
is disconnected. Shows an error message and a Retry button with a 5-second
cooldown between clicks.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class DriveErrorOverlay(QWidget):
    """Overlay widget shown when a file's network drive is inaccessible."""

    RETRY_COOLDOWN_MS = 5000  # 5 seconds between retry clicks

    def __init__(self, drive_display_name, parent=None):
        super().__init__(parent)
        self.drive_display_name = drive_display_name
        self._retry_callback = None
        self._cooldown_active = False

        self._setup_ui()

    def _setup_ui(self):
        """Build the overlay UI."""
        self.setStyleSheet("background-color: #FFF3CD; border: 2px solid #FFC107;")

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        # Warning icon and title
        title_label = QLabel("Network Drive Unavailable")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("border: none; color: #856404;")
        layout.addWidget(title_label)

        # Drive name
        self.drive_label = QLabel(f"Network drive \"{self.drive_display_name}\" not found")
        drive_font = QFont()
        drive_font.setPointSize(11)
        self.drive_label.setFont(drive_font)
        self.drive_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drive_label.setStyleSheet("border: none; color: #856404;")
        self.drive_label.setWordWrap(True)
        layout.addWidget(self.drive_label)

        # Info text
        info_label = QLabel(
            "The drive may be reconnecting after sleep/hibernate.\n"
            "Your unsaved changes are preserved in memory."
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("border: none; color: #856404;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Retry button
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.retry_button = QPushButton("Retry Connection")
        self.retry_button.setMinimumWidth(160)
        self.retry_button.setMinimumHeight(36)
        self.retry_button.setStyleSheet("""
            QPushButton {
                background-color: #FFC107;
                border: 1px solid #856404;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
                color: #856404;
            }
            QPushButton:hover {
                background-color: #FFD54F;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                border: 1px solid #BDBDBD;
                color: #9E9E9E;
            }
        """)
        self.retry_button.clicked.connect(self._on_retry_clicked)
        button_layout.addWidget(self.retry_button)
        layout.addLayout(button_layout)

        # Status label (shows countdown or result)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("border: none; color: #856404; font-style: italic;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def set_retry_callback(self, callback):
        """Set the function to call when Retry is clicked.

        The callback should return True if the drive is now accessible, False otherwise.
        """
        self._retry_callback = callback

    def update_drive_name(self, drive_display_name):
        """Update the displayed drive name."""
        self.drive_display_name = drive_display_name
        self.drive_label.setText(f"Network drive \"{self.drive_display_name}\" not found")

    def _on_retry_clicked(self):
        """Handle retry button click."""
        if self._cooldown_active:
            return

        self.retry_button.setEnabled(False)
        self.status_label.setText("Checking connection...")

        if self._retry_callback:
            success = self._retry_callback()
            if success:
                self.status_label.setText("Drive reconnected!")
                # The parent will hide this overlay
                return

        self.status_label.setText("Drive still unavailable. Try again in 5 seconds.")
        self._cooldown_active = True
        QTimer.singleShot(self.RETRY_COOLDOWN_MS, self._end_cooldown)

    def _end_cooldown(self):
        """Re-enable the retry button after cooldown."""
        self._cooldown_active = False
        self.retry_button.setEnabled(True)
        self.status_label.setText("")
