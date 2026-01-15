"""
Centralized styles for the TurnipText application.
Avoids duplication of CSS-like style strings across modules.
"""

# Standard button style used throughout the application
BUTTON_STYLE = """
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #F8F8F8, stop:1 #E0E0E0);
        border: 1px solid #B0B0B0;
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 24px;
        font-weight: bold;
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

# Dialog button style (slightly smaller padding)
DIALOG_BUTTON_STYLE = """
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #F8F8F8, stop:1 #E0E0E0);
        border: 1px solid #B0B0B0;
        border-radius: 4px;
        padding: 6px 16px;
        min-width: 60px;
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

# Warning/modified button style (yellow highlight)
MODIFIED_BUTTON_STYLE = """
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #FFFDE7, stop:1 #FFF9C4);
        border: 1px solid #F9A825;
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 24px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #FFFEF0, stop:1 #FFEB3B);
        border: 1px solid #F57F17;
    }
    QPushButton:pressed {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #FFF59D, stop:1 #FBC02D);
        border: 1px solid #E65100;
    }
"""

# Input field style
INPUT_STYLE = """
    QLineEdit {
        background-color: white;
        border: 1px solid #B0B0B0;
        border-radius: 3px;
        padding: 4px 8px;
        min-height: 20px;
    }
    QLineEdit:focus {
        border: 2px solid #2196F3;
    }
"""

# Close event dialog button style (larger)
CLOSE_DIALOG_BUTTON_STYLE = """
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #F8F8F8, stop:1 #E0E0E0);
        border: 1px solid #B0B0B0;
        border-radius: 4px;
        padding: 8px 16px;
        min-width: 100px;
        min-height: 28px;
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
