"""Tool Control Panel — main application entry point."""

import os
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QDialog, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

from config import load_config, save_config, set_config_path, Config
from ui.search_bar import SearchBar
from ui.filter_bar import FilterBar
from ui.matrix_table import MatrixTable
from ui.style import APP_STYLESHEET
import debug_log


class ConfigSetupDialog(QDialog):
    """First-run dialog: user sets TOOLIX_CONFIG_DIR env var."""

    def __init__(self, default_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置路径设置")
        self.setMinimumWidth(520)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 13px; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px 10px; font-size: 13px; }
            QPushButton { background-color: #45475a; color: #cdd6f4; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 13px; }
            QPushButton:hover { background-color: #585b70; }
            QPushButton#primary { background-color: #89b4fa; color: #1e1e2e;
                font-weight: bold; }
            QPushButton#primary:hover { background-color: #b4d0fb; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(QLabel(
            "首次运行，请选择配置文件存放目录："
        ))

        row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("例如: D:\\config")
        self._input.setText(default_path)
        row.addWidget(self._input, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        layout.addSpacing(4)
        name_label = QLabel("文件名固定为 <b>toolix.json</b>")
        name_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(name_label)

        layout.addSpacing(4)
        hint = QLabel("选择后会自动记住，下次启动无需再设。")
        hint.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("退出")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton("确认")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(self._on_ok)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "选择配置目录")
        if path:
            self._input.setText(path)

    def _on_ok(self):
        dir_path = self._input.text().strip()
        if not dir_path:
            return
        self._chosen_path = os.path.join(dir_path, "toolix.json")
        self.accept()

    def chosen_path(self) -> str:
        return getattr(self, "_chosen_path", "")


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
        self.setWindowTitle("Toolix")
        self.setWindowIcon(_make_icon())
        self.setMinimumSize(600, 400)

        settings = QSettings("Kiwi", "Toolix")
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
        self.filter_bar.tool_filter_changed.connect(self._on_tool_filter)
        self.filter_bar.env_filter_changed.connect(self._on_env_filter)
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
        if text.strip().lower() == "setting":
            self.search_bar.clear()
            self._change_config_dir()
            return
        self.filter_bar.reset()
        self.matrix.apply_filter(text)

    def _change_config_dir(self) -> None:
        """Open the config directory setup dialog to change the config path."""
        dlg = ConfigSetupDialog("", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            chosen = dlg.chosen_path()
            if chosen:
                settings = QSettings("Kiwi", "Toolix")
                set_config_path(chosen)
                settings.setValue("config_dir", chosen)
                # Reload with new config
                self._load()

    def _on_tool_filter(self, names: list[str]) -> None:
        self.matrix.set_tool_filter(names)

    def _on_env_filter(self, names: list[str]) -> None:
        self.matrix.set_env_filter(names)

    def _on_card_tool_filter(self, name: str) -> None:
        self.search_bar.clear()
        self.filter_bar.select_tool(name)  # toggle → emits → matrix updates

    def _on_card_env_filter(self, name: str) -> None:
        self.search_bar.clear()
        self.filter_bar.select_env(name)

    def _load(self) -> None:
        try:
            self._config = load_config()
            self.filter_bar.reset()
            self.filter_bar.set_config(self._config, lambda: save_config(self._config))
            tools = [t.name for t in self._config.tools]
            envs = [e.name for e in self._config.environments]
            self.filter_bar.set_filters(tools, envs)
            self.matrix._filter_text = ""
            self.matrix._tool_filter_names = set()
            self.matrix._env_filter_names = set()
            self.matrix.tool_order_changed.connect(lambda: save_config(self._config))
            self.matrix.set_config(self._config)
        except Exception as e:
            QMessageBox.critical(self, "配置加载失败", str(e))

    def closeEvent(self, event) -> None:
        settings = QSettings("Kiwi", "Toolix")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


def _excepthook(exc_type, exc_value, traceback):
    sys.__excepthook__(exc_type, exc_value, traceback)
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.critical(None, "错误", f"{exc_type.__name__}: {exc_value}")


def main():
    sys.excepthook = _excepthook
    debug_log.init()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    app.setApplicationName("Toolix")
    app.setOrganizationName("Kiwi")
    app.setWindowIcon(_make_icon())

    # Config path: QSettings memory > prompt > platform default
    settings = QSettings("Kiwi", "Toolix")
    saved = settings.value("config_dir") or ""
    if saved and os.path.isfile(saved):
        set_config_path(saved)
    else:
        # No saved path or file gone — show setup dialog
        dlg = ConfigSetupDialog("")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        chosen = dlg.chosen_path()
        if chosen:
            set_config_path(chosen)
            settings.setValue("config_dir", chosen)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
