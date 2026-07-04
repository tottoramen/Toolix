"""Cell widget — renders action buttons for one matrix cell."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog,
    QLabel, QLineEdit, QFileDialog, QComboBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer, QSettings
import os
import sys
import tempfile

from models import Entry, ClaudeModel


class CellWidget(QWidget):
    """Displays action buttons for a non-empty Entry in the matrix."""

    def __init__(self, entry: Entry, tool_name: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("cell-content")
        self.entry = entry
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        name_label = QLabel(tool_name)
        name_label.setObjectName("tool-name")
        name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(name_label)

        if entry.url:
            btn = QPushButton("🔗 启动")
            btn.setProperty("action", "open")
            btn.setCursor(self.cursor())
            btn.setToolTip(entry.url)
            btn.clicked.connect(self._on_open)
            layout.addWidget(btn)

        if entry.ssh:
            btn = QPushButton("🖥 启动")
            btn.setProperty("action", "ssh")
            btn.setCursor(self.cursor())
            btn.setToolTip(entry.ssh)
            btn.clicked.connect(self._on_ssh)
            layout.addWidget(btn)

        if entry.credentials:
            btn = QPushButton("🔑 查看账密")
            btn.setProperty("action", "cmd")
            btn.setCursor(self.cursor())
            btn.clicked.connect(self._on_show_credentials)
            layout.addWidget(btn)

        for i, cmd in enumerate(entry.commands):
            btn = QPushButton(f"⚡ {cmd.label}")
            btn.setProperty("action", "cmd")
            btn.setCursor(self.cursor())
            btn.setToolTip(cmd.command)
            btn.clicked.connect(lambda checked, idx=i: self._on_run_cmd(idx))
            layout.addWidget(btn)

        layout.addStretch()

    def _on_open(self) -> None:
        from actions import open_url
        open_url(self.entry)

    def _on_ssh(self) -> None:
        from actions import run_ssh
        run_ssh(self.entry)

    def _on_show_credentials(self) -> None:
        dialog = CredentialDialog(self.entry.credentials, self)
        dialog.exec()

    def _on_run_cmd(self, cmd_index: int) -> None:
        from actions import run_command
        run_command(cmd_index, self.entry)


class CredentialDialog(QDialog):
    """Simple credential viewer: one row per field, key + value + copy."""

    def __init__(self, credentials, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查看账密")
        self.setMinimumWidth(320)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 13px; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 4px 8px; font-size: 13px; }
            QPushButton { background-color: #45475a; color: #cdd6f4; border: none;
                border-radius: 4px; padding: 4px 12px; font-size: 12px; }
            QPushButton:hover { background-color: #585b70; }
            QPushButton[copy="true"] { background-color: #a6e3a1; color: #1e1e2e; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        for cred in credentials:
            if cred.label:
                lbl = QLabel(f"<b>{cred.label}</b>")
                layout.addWidget(lbl)

            # Username
            if cred.username:
                layout.addWidget(self._row("用户", cred.username))

            # Password
            if cred.password:
                layout.addWidget(self._row("密码", cred.password))

            # Custom fields
            for f in cred.fields:
                layout.addWidget(self._row(f.key, f.value))

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _row(self, key, value):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        h.addWidget(QLabel(key))
        inp = QLineEdit(value)
        inp.setReadOnly(True)
        h.addWidget(inp, 1)

        btn = QPushButton("复制")
        btn.setProperty("copy", True)
        btn.clicked.connect(lambda: self._copy(value, btn))
        h.addWidget(btn)
        return row

    def _copy(self, text, btn):
        import pyperclip
        pyperclip.copy(text)
        original = btn.text()
        btn.setText("✓")
        QTimer.singleShot(1200, lambda: btn.setText(original))


class ClaudeCodeDialog(QDialog):
    """Custom launch dialog for local Claude Code. Models are driven by config.json claude_models."""

    def __init__(self, claude_models: list[ClaudeModel], claude_dirs: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("启动 Claude Code")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 13px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px 10px; font-size: 13px; min-height: 28px; }
            QComboBox::drop-down {
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left: 1px solid #45475a;
            }
            QComboBox QAbstractItemView { background-color: #313244; color: #cdd6f4;
                selection-background-color: #45475a; }
            QPushButton { background-color: #45475a; color: #cdd6f4; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 13px; }
            QPushButton:hover { background-color: #585b70; }
            QPushButton#launch-btn { background-color: #89b4fa; color: #1e1e2e;
                font-weight: bold; font-size: 15px; padding: 8px 24px; }
            QPushButton#launch-btn:hover { background-color: #b4d0fb; }
            QRadioButton { color: #cdd6f4; font-size: 13px; spacing: 8px; }
            QRadioButton::indicator { width: 16px; height: 16px; border-radius: 8px;
                border: 2px solid #45475a; background-color: #313244; }
            QRadioButton::indicator:checked { border-color: #89b4fa; background-color: #89b4fa; }
        """)

        self._settings = QSettings("Kiwi", "Toolix")
        self._claude_models = claude_models
        self._model_map: dict[str, dict[str, str]] = {m.id: m.env for m in claude_models}

        if sys.platform == "darwin":
            project_dir = os.path.expanduser("~/projects")
        else:
            project_dir = "D:\\projects"
        subdirs = claude_dirs if claude_dirs else ["claude", "udreader", "Toolix"]
        last_dir = self._settings.value("claude/dir") or ""
        default_dir = last_dir if last_dir and os.path.isdir(last_dir) else os.path.join(project_dir, "claude")

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        # ── 工作目录 ──
        layout.addWidget(QLabel("工作目录:"))
        self.dir_group = QButtonGroup(self)
        for sd in subdirs:
            full = os.path.join(project_dir, sd)
            rb = QRadioButton(sd)
            rb.setProperty("path", full)
            self.dir_group.addButton(rb)
            if full == default_dir:
                rb.setChecked(True)
            layout.addWidget(rb)

        # ── 模型 (from config.json claude_models) ──
        layout.addWidget(QLabel("模型:"))
        self.model_group = QButtonGroup(self)
        default_model = self._settings.value("claude/model") or (claude_models[0].id if claude_models else "")
        self._radio_models: dict[str, QRadioButton] = {}
        for cm in claude_models:
            rb = QRadioButton(cm.name)
            rb.setProperty("model", cm.id)
            self.model_group.addButton(rb)
            if cm.id == default_model:
                rb.setChecked(True)
            self._radio_models[cm.id] = rb
            layout.addWidget(rb)

        layout.addSpacing(8)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        launch_btn = QPushButton("启动")
        launch_btn.setObjectName("launch-btn")
        launch_btn.clicked.connect(self._launch)
        btn_row.addWidget(launch_btn)
        layout.addLayout(btn_row)

        self._cmd = ""

    def _launch(self):
        d = ""
        rb = self.dir_group.checkedButton()
        if rb:
            d = rb.property("path") or ""

        model_id = ""
        checked = self.model_group.checkedButton()
        if checked:
            model_id = checked.property("model") or ""

        if not d or not model_id:
            return

        s = self._settings
        s.setValue("claude/dir", d)
        s.setValue("claude/model", model_id)

        env = self._model_map.get(model_id, {})

        # Build temp script: set env vars then launch claude
        if sys.platform == "darwin":
            # macOS: .command file (native executable shell script)
            lines = [f"cd '{d}'"]
            for key, value in env.items():
                lines.append(f"export {key}='{value}'")
            lines.append("claude")

            fd, path = tempfile.mkstemp(suffix=".command", prefix="cc_")
            with os.fdopen(fd, "w") as f:
                f.write("\n".join(lines))
            os.chmod(path, 0o755)

            self._cmd = f'open -a Terminal "{path}"'
        else:
            # Windows: .ps1 PowerShell script
            lines = [f"Set-Location -LiteralPath '{d}'"]
            for key, value in env.items():
                lines.append(f"$env:{key} = '{value}'")
            lines.append("claude")

            fd, path = tempfile.mkstemp(suffix=".ps1", prefix="cc_")
            with os.fdopen(fd, "w") as f:
                f.write("\n".join(lines))

            self._cmd = f'powershell -NoExit -ExecutionPolicy Bypass -File "{path}"'
        self.accept()

    def command(self) -> str:
        return self._cmd


class EmptyCell(QWidget):
    """Placeholder for empty cells in the matrix."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cell-empty")
        self.setMinimumSize(80, 40)
