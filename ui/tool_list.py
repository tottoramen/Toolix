"""Tool list — grouped by environment, tool name on buttons."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, QTimer

from models import Config, Entry


class ToolList(QScrollArea):
    """Scrollable list grouped by environment. Buttons show tool names."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._config: Config | None = None
        self._filter_text = ""
        self._env_names: dict[str, str] = {}

        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self.setWidget(self._inner)

    def set_config(self, config: Config) -> None:
        self._config = config
        self._env_names = {e.id: e.name for e in config.environments}
        self._rebuild()

    def apply_filter(self, text: str) -> None:
        self._filter_text = text.lower().strip()
        if self._config:
            self._rebuild()

    def _rebuild(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._config:
            return

        # Group entries by environment
        env_entries: dict[str, list[tuple[str, Entry]]] = {}
        env_order: list[str] = []
        for env in self._config.environments:
            env_id = env.id
            entries = []
            for tool in self._config.tools:
                entry = tool.get_entry(env_id)
                if entry and not entry.is_empty:
                    if self._entry_visible(tool.name, entry):
                        entries.append((tool.name, entry))
            if entries:
                if env_id not in env_entries:
                    env_order.append(env_id)
                env_entries.setdefault(env_id, []).extend(entries)

        for env_id in env_order:
            entries = env_entries[env_id]
            if not entries:
                continue

            env_name = self._env_names.get(env_id, env_id)

            # Group header
            header_text = env_name
            header = QLabel(header_text)
            header.setObjectName("group-header")
            header.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._layout.addWidget(header)

            # Entry rows
            for tool_name, entry in entries:
                row = self._build_row(tool_name, entry)
                self._layout.addWidget(row)

        self._layout.addStretch()

    def _entry_visible(self, tool_name: str, entry: Entry) -> bool:
        if not self._filter_text:
            return True
        if self._filter_text in tool_name.lower():
            return True
        for env_id in entry.envs:
            env_name = self._env_names.get(env_id, env_id)
            if self._filter_text in env_name.lower():
                return True
        for cred in entry.credentials:
            if self._filter_text in cred.label.lower():
                return True
        for cmd in entry.commands:
            if self._filter_text in cmd.label.lower():
                return True
        return False

    def _build_row(self, tool_name: str, entry: Entry) -> QWidget:
        """One row: tool name on button + credential/command buttons."""
        row = QWidget()
        row.setObjectName("entry-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)

        # Open URL → button with tool name
        if entry.url:
            btn = QPushButton(f"🔗 {tool_name}")
            btn.setProperty("action", "open")
            btn.setCursor(row.cursor())
            btn.setToolTip(entry.url)
            btn.clicked.connect(lambda: self._on_open(entry))
            layout.addWidget(btn)

        # SSH → button with tool name
        if entry.ssh:
            btn = QPushButton(f"🖥 {tool_name}")
            btn.setProperty("action", "ssh")
            btn.setCursor(row.cursor())
            btn.setToolTip(entry.ssh)
            btn.clicked.connect(lambda: self._on_ssh(entry))
            layout.addWidget(btn)

        # No URL or SSH but has other content → show tool name as label
        if not entry.url and not entry.ssh:
            label = QLabel(tool_name)
            label.setObjectName("tool-name")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(label)

        # Credential copy buttons
        for i, cred in enumerate(entry.credentials):
            btn = QPushButton(f"📋 {cred.label}")
            btn.setProperty("action", "copy")
            btn.setCursor(row.cursor())
            if cred.username:
                btn.setToolTip(f"点击复制密码\n用户: {cred.username}")
            else:
                btn.setToolTip("点击复制密码")
            btn.clicked.connect(lambda checked, e=entry, idx=i, b=btn: self._on_copy(e, idx, b))
            layout.addWidget(btn)

        # Command buttons
        for i, cmd in enumerate(entry.commands):
            btn = QPushButton(f"⚡ {cmd.label}")
            btn.setProperty("action", "cmd")
            btn.setCursor(row.cursor())
            btn.setToolTip(cmd.command)
            btn.clicked.connect(lambda checked, e=entry, idx=i: self._on_run_cmd(e, idx))
            layout.addWidget(btn)

        layout.addStretch()
        return row

    def _on_open(self, entry: Entry) -> None:
        from actions import open_url
        open_url(entry)

    def _on_ssh(self, entry: Entry) -> None:
        from actions import run_ssh
        run_ssh(entry)

    def _on_copy(self, entry: Entry, cred_index: int, button: QPushButton) -> None:
        from actions import copy_credential
        copy_credential(cred_index, entry)

        original = button.text()
        button.setText("✓ 已复制")
        button.setProperty("copied", True)
        button.style().unpolish(button)
        button.style().polish(button)
        QTimer.singleShot(1500, lambda: self._reset(button, original))

    def _reset(self, button: QPushButton, text: str) -> None:
        button.setText(text)
        button.setProperty("copied", False)
        button.style().unpolish(button)
        button.style().polish(button)

    def _on_run_cmd(self, entry: Entry, cmd_index: int) -> None:
        from actions import run_command
        run_command(cmd_index, entry)
