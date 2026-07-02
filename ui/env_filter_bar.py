"""Environment filter bar — wrapping chips to filter by group."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal


class EnvFilterBar(QWidget):
    """Wrapping chips, auto-wrap on resize."""

    filter_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(8, 0, 8, 0)
        self._outer.setSpacing(2)
        self._chips: list[QPushButton] = []
        self._active_chip: QPushButton | None = None
        self._names: list[str] = []
        self._last_w = 0
        self._rebuilding = False

    def set_environments(self, names: list[str]) -> None:
        self._names = list(names)
        self._lay_out()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._names and not self._rebuilding and self.width() != self._last_w:
            self._last_w = self.width()
            self._lay_out()

    def _lay_out(self):
        if self._rebuilding:
            return
        self._rebuilding = True

        while self._outer.count():
            item = self._outer.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
            sub = item.layout()
            if sub:
                while sub.count():
                    si = sub.takeAt(0)
                    if si.widget():
                        si.widget().hide()
                        si.widget().setParent(None)
        self._chips.clear()
        self._active_chip = None

        if not self._names:
            self._rebuilding = False
            return

        avail = max(self.width() - 16, 100)
        row = QHBoxLayout()
        row.setSpacing(4)
        self._outer.addLayout(row)
        x = 0

        for name in self._names:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244; color: #a6adc8;
                    border: none; border-radius: 12px;
                    padding: 3px 12px; font-size: 13px;
                }
                QPushButton:hover { background-color: #45475a; color: #cdd6f4; }
                QPushButton[active="true"] {
                    background-color: #a6e3a1; color: #1e1e2e; font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, b=btn, n=name: self._on_click(b, n))
            self._chips.append(btn)
            bw = btn.sizeHint().width() + 4
            if x + bw > avail and x > 0:
                row.addStretch()
                row = QHBoxLayout()
                row.setSpacing(4)
                self._outer.addLayout(row)
                x = 0
            row.addWidget(btn)
            x += bw

        row.addStretch()
        self._rebuilding = False

    def _on_click(self, btn: QPushButton, name: str) -> None:
        if self._active_chip is btn:
            self.reset()
            return
        if self._active_chip:
            self._active_chip.setProperty("active", False)
            self._active_chip.style().unpolish(self._active_chip)
            self._active_chip.style().polish(self._active_chip)
        btn.setProperty("active", True)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        self._active_chip = btn
        self.filter_clicked.emit(name)

    def reset(self) -> None:
        had = self._active_chip is not None
        if self._active_chip:
            self._active_chip.setProperty("active", False)
            self._active_chip.style().unpolish(self._active_chip)
            self._active_chip.style().polish(self._active_chip)
        self._active_chip = None
        if had:
            self.filter_clicked.emit("")
