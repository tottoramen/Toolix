"""Qt stylesheet constants for the tool panel."""

APP_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 18px;
    selection-background-color: #89b4fa;
}

QLineEdit:focus {
    border: 1px solid #89b4fa;
}

QPushButton {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 18px;
}

QPushButton:hover {
    background-color: #313244;
}

QPushButton[action="open"] {
    background-color: transparent;
    color: #89b4fa;
    font-size: 18px;
}
QPushButton[action="open"]:hover {
    background-color: #313244;
}

QPushButton[action="ssh"] {
    background-color: transparent;
    color: #fab387;
    font-size: 18px;
}
QPushButton[action="ssh"]:hover {
    background-color: #313244;
}

QPushButton[action="cmd"] {
    background-color: transparent;
    color: #cba6f7;
    font-size: 18px;
}
QPushButton[action="cmd"]:hover {
    background-color: #313244;
}

QPushButton[action="launch"] {
    background-color: transparent;
    color: #a6e3a1;
    font-size: 20px;
}
QPushButton[action="launch"]:hover {
    background-color: #313244;
}

QPushButton[action="settings"] {
    background-color: transparent;
    color: #f9e2af;
    font-size: 18px;
}
QPushButton[action="settings"]:hover {
    background-color: #313244;
}

QScrollBar:horizontal {
    background-color: #1e1e2e;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 10px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QStatusBar {
    background-color: #313244;
    color: #a6adc8;
    font-size: 13px;
}

QLabel#tool-tag {
    color: #89b4fa;
    background-color: #1e2a3a;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 13px;
    font-weight: bold;
}
QLabel#env-tag {
    color: #a6adc8;
    background-color: #252a35;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 12px;
}

QWidget#entry-row {
    background-color: transparent;
}
QWidget#entry-row:hover {
    background-color: #181825;
    border-radius: 4px;
}

QWidget#cell-content {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
}
QWidget#cell-content:hover {
    border: 1px solid #45475a;
}
QWidget#cell-content-dragging {
    background-color: #2a2a3d;
    border: 1px dashed #89b4fa;
    border-radius: 6px;
}
"""
