"""Tool Control Panel — main application entry point."""

import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QMessageBox,
)
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from config import load_config, save_config, Config
from ui.search_bar import SearchBar
from ui.filter_bar import FilterBar
from ui.matrix_table import MatrixTable
from ui.style import APP_STYLESHEET


def _make_icon() -> QIcon:
    """Generate a tool-panel icon: dark rounded rect with 4 accent squares."""
    s = 64; m = 2; r = 12
    px = QPixmap(s, s)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    # dark outer rounded square
    p.setBrush(QColor("#1e1e2e"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(m, m, s - 2*m, s - 2*m, r, r)
    # blue inner rounded square
    im = 12
    p.setBrush(QColor("#89b4fa"))
    p.drawRoundedRect(im, im, s - 2*im, s - 2*im, 8, 8)
    # 4 dark squares (tool grid)
    p.setBrush(QColor("#1e1e2e"))
    gap = 4; sq = 13
    positions = [
        (im + 4, im + 4),
        (im + sq + gap + 4, im + 4),
        (im + 4, im + sq + gap + 4),
        (im + sq + gap + 4, im + sq + gap + 4),
    ]
    for x, y in positions:
        p.drawRoundedRect(x, y, sq, sq, 3, 3)
    p.end()
    return QIcon(px)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("工具控制面板")
        self.setWindowIcon(_make_icon())
        self.setMinimumSize(600, 400)

        settings = QSettings("Kiwi", "ToolPanel")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search_bar = SearchBar()
        layout.addWidget(self.search_bar)

        self.filter_bar = FilterBar()
        layout.addWidget(self.filter_bar)

        self.matrix = MatrixTable()
        layout.addWidget(self.matrix, 1)

        self._config: Config | None = None
        self._load()

        self.search_bar.filter_changed.connect(self._on_search)
        self.filter_bar.tool_clicked.connect(self._on_tool_filter)
        self.filter_bar.env_clicked.connect(self._on_env_filter)
        self.filter_bar.filters_changed.connect(self._on_filters_changed)
        self.matrix.tool_filter_requested.connect(self._on_card_tool_filter)
        self.matrix.env_filter_requested.connect(self._on_card_env_filter)

    def _on_filters_changed(self) -> None:
        """Reload matrix when filter chips are added/edited."""
        if self._config:
            tools = [t.name for t in self._config.tools]
            envs = [e.name for e in self._config.environments]
            self.filter_bar.set_filters(tools, envs)
            self.matrix.set_config(self._config)

    def _on_search(self, text: str) -> None:
        self.filter_bar.reset()
        self.matrix.apply_filter(text)

    def _on_tool_filter(self, tool_name: str) -> None:
        self.search_bar.clear()
        self.matrix.set_tool_filter(tool_name)

    def _on_env_filter(self, env_name: str) -> None:
        self.search_bar.clear()
        self.matrix.set_env_filter(env_name)

    def _on_card_tool_filter(self, name: str) -> None:
        self.search_bar.clear()
        self.filter_bar.select_tool(name)
        self.matrix.set_tool_filter(name)

    def _on_card_env_filter(self, name: str) -> None:
        self.search_bar.clear()
        self.filter_bar.select_env(name)
        self.matrix.set_env_filter(name)

    def _load(self) -> None:
        try:
            self._config = load_config()
            self.filter_bar.reset()
            self.filter_bar.set_config(self._config, lambda: save_config(self._config))
            tools = [t.name for t in self._config.tools]
            envs = [e.name for e in self._config.environments]
            self.filter_bar.set_filters(tools, envs)
            self.matrix._filter_text = ""
            self.matrix._tool_filter = ""
            self.matrix._env_filter = ""
            self.matrix.tool_order_changed.connect(lambda: save_config(self._config))
            self.matrix.set_config(self._config)
        except Exception as e:
            QMessageBox.critical(self, "配置加载失败", str(e))

    def closeEvent(self, event) -> None:
        settings = QSettings("Kiwi", "ToolPanel")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def _excepthook(exc_type, exc_value, traceback):
    sys.__excepthook__(exc_type, exc_value, traceback)
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.critical(None, "错误", f"{exc_type.__name__}: {exc_value}")


def main():
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("ToolPanel")
    app.setOrganizationName("Kiwi")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
