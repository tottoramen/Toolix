"""Search bar widget with real-time filtering."""

from PySide6.QtWidgets import QLineEdit, QHBoxLayout, QWidget
from PySide6.QtCore import Signal


class SearchBar(QWidget):
    """A search input that emits textChanged for real-time filtering."""

    filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("搜索...")
        self.input.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.input, 1)

    def _on_text_changed(self, text: str) -> None:
        self.filter_changed.emit(text)

    def clear(self) -> None:
        self.input.clear()
