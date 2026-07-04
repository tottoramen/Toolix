"""Tool grid — entries flow horizontally, wrap to next row."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QDialog, QLineEdit, QComboBox,
)
from PySide6.QtCore import Qt, Signal, QPoint

from models import Config, Entry, Tool


class MatrixTable(QScrollArea):
    tool_filter_requested = Signal(str)
    env_filter_requested = Signal(str)
    tool_order_changed = Signal()  # also fires for card_order changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._config: Config | None = None
        self._filter_text = ""
        self._tool_filter = ""
        self._env_filter = ""
        self._env_names: dict[str, str] = {}
        self._last_w = 0
        self._rebuilding = False

        self._inner = QWidget()
        self._layout = QVBoxLayout(self._inner)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self.setWidget(self._inner)

        # drag state
        self._drag_key: str | None = None      # "tool_id:entry_idx" being dragged
        self._drag_candidate: str | None = None
        self._drag_press_pos: QPoint | None = None

        self._inner.mousePressEvent = self._inner_press
        self._inner.mouseMoveEvent = self._inner_move
        self._inner.mouseReleaseEvent = self._inner_release

    # ── config / filter ──────────────────────────────────────────

    def set_config(self, config: Config) -> None:
        self._config = config
        self._env_names = {e.id: e.name for e in config.environments}
        self._lay_out()

    def apply_filter(self, text: str) -> None:
        self._filter_text = text.lower().strip()
        self._tool_filter = ""
        self._env_filter = ""
        if self._config:
            self._lay_out()

    def set_tool_filter(self, tool_name: str) -> None:
        self._tool_filter = tool_name
        self._filter_text = ""
        self._env_filter = ""
        if self._config:
            self._lay_out()

    def set_env_filter(self, env_name: str) -> None:
        self._env_filter = env_name
        self._filter_text = ""
        self._tool_filter = ""
        if self._config:
            self._lay_out()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._config and self.width() != self._last_w:
            self._last_w = self.width()
            self._lay_out()

    def _all_entry_keys(self) -> list[str]:
        """Generate stable "tool_id:entry_idx" keys for all entries."""
        keys = []
        for tool in self._config.tools:
            for i in range(len(tool.entries)):
                keys.append(f"{tool.id}:{i}")
        return keys

    def _ordered_entries(self) -> list[tuple[str, Tool, Entry]]:
        """Return (key, tool, entry) in card_order, then any unlisted ones."""
        if not self._config:
            return []
        tool_map = {t.id: t for t in self._config.tools}
        all_keys = set(self._all_entry_keys())

        result = []
        seen = set()
        for key in self._config.card_order:
            if key not in all_keys:
                continue
            tid, idx_s = key.rsplit(":", 1)
            tool = tool_map.get(tid)
            if tool is None:
                continue
            idx = int(idx_s)
            if idx >= len(tool.entries):
                continue
            result.append((key, tool, tool.entries[idx]))
            seen.add(key)

        # Append any entries not yet in card_order (new entries)
        for tool in self._config.tools:
            for i, entry in enumerate(tool.entries):
                key = f"{tool.id}:{i}"
                if key not in seen:
                    result.append((key, tool, entry))
        return result

    def _lay_out(self):
        if self._rebuilding:
            return
        self._rebuilding = True

        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide(); w.setParent(None)
            sub = item.layout()
            if sub:
                while sub.count():
                    si = sub.takeAt(0)
                    if si.widget():
                        si.widget().hide(); si.widget().setParent(None)

        if not self._config:
            self._rebuilding = False
            return

        items: list[tuple[str, Tool, Entry]] = []
        for key, tool, entry in self._ordered_entries():
            if entry.is_empty:
                continue
            if self._tool_filter and tool.name != self._tool_filter:
                continue
            if self._env_filter:
                env_names = [self._env_names.get(eid, eid) for eid in entry.envs]
                if self._env_filter not in env_names:
                    continue
            if not self._entry_visible(tool.name, entry):
                continue
            items.append((key, tool, entry))

        if not items:
            self._rebuilding = False
            return

        avail = max(self.width() - 24, 200)
        row = QHBoxLayout()
        row.setSpacing(4)
        self._layout.addLayout(row)
        x = 0

        # + add card
        add_card = self._build_add_card()
        if add_card:
            cw = add_card.sizeHint().width() + 4
            row.addWidget(add_card)
            x += cw

        for key, tool, entry in items:
            card = self._build_card(key, tool, entry)
            cw = card.sizeHint().width() + 4
            if x + cw > avail and x > 0:
                row.addStretch()
                row = QHBoxLayout()
                row.setSpacing(4)
                self._layout.addLayout(row)
                x = 0
            row.addWidget(card)
            x += cw

        row.addStretch()
        self._layout.addStretch()
        self._rebuilding = False

    def _entry_visible(self, tool_name: str, entry: Entry) -> bool:
        if not self._filter_text:
            return True
        if self._filter_text in tool_name.lower():
            return True
        for env_id in entry.envs:
            if self._filter_text in self._env_names.get(env_id, env_id).lower():
                return True
        for cred in entry.credentials:
            if self._filter_text in cred.label.lower():
                return True
        for cmd in entry.commands:
            if self._filter_text in cmd.label.lower():
                return True
        return False

    def _build_card(self, key: str, tool: Tool, entry: Entry) -> QWidget:
        card = QWidget()
        card.setObjectName("cell-content-dragging" if key == self._drag_key else "cell-content")
        card.setProperty("drag_key", key)
        row = QHBoxLayout(card)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)

        tool_tag = QLabel(tool.name)
        tool_tag.setObjectName("tool-tag")
        tool_tag.setCursor(Qt.PointingHandCursor)
        tool_tag.setProperty("drag_key", key)
        self._make_clickable(tool_tag, lambda n=tool.name: self.tool_filter_requested.emit(n))
        row.addWidget(tool_tag)

        for env_id in entry.envs:
            env_name = self._env_names.get(env_id, env_id)
            if env_name != "通用":
                env_tag = QLabel(env_name)
                env_tag.setObjectName("env-tag")
                env_tag.setCursor(Qt.PointingHandCursor)
                env_tag.setProperty("drag_key", key)
                self._make_clickable(env_tag, lambda n=env_name: self.env_filter_requested.emit(n))
                row.addWidget(env_tag)

        if entry.url or entry.ssh:
            btn = QPushButton("▶")
            btn.setFixedSize(32, 32)
            btn.setProperty("action", "launch")
            btn.clicked.connect(lambda checked, e=entry: (
                self._on_open(e) if e.url else self._on_ssh(e)
            ))
            row.addWidget(btn)

        if entry.credentials:
            btn = QPushButton("🔑")
            btn.setFixedSize(32, 32)
            btn.setProperty("action", "cmd")
            btn.clicked.connect(lambda checked, e=entry: self._on_show_creds(e))
            row.addWidget(btn)

        # ⚙ Settings button
        btn = QPushButton("⚙")
        btn.setFixedSize(32, 32)
        btn.setProperty("action", "settings")
        btn.clicked.connect(lambda checked, e=entry, t=tool: self._on_edit_entry(e, t))
        row.addWidget(btn)

        return card

    def _build_add_card(self) -> QWidget | None:
        if not self._config or not self._config.tools:
            return None
        card = QWidget()
        card.setObjectName("cell-content")
        row = QHBoxLayout(card)
        row.setContentsMargins(4, 4, 4, 4)
        btn = QPushButton("+")
        btn.setFixedSize(32, 32)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: #a6adc8;
                border: 1px dashed #45475a; border-radius: 6px;
                font-size: 20px; font-weight: bold; }}
            QPushButton:hover {{ border-color: #89b4fa; color: #89b4fa; background-color: #313244; }}
        """)
        btn.clicked.connect(self._on_add_entry)
        row.addWidget(btn)
        return card

    def _on_add_entry(self):
        dlg = _AddEntryDialog(self._config, self)
        if dlg.exec():
            self._lay_out()
            self.tool_order_changed.emit()

    @staticmethod
    def _make_clickable(label: QLabel, callback):
        press_pos = [None]

        def on_press(event):
            if event.button() == Qt.LeftButton:
                press_pos[0] = event.pos()
            event.ignore()

        def on_release(event):
            if press_pos[0] is not None:
                if (event.pos() - press_pos[0]).manhattanLength() < 5:
                    callback()
                press_pos[0] = None

        label.mousePressEvent = on_press
        label.mouseReleaseEvent = on_release

    # ── card drag (entry-level) ───────────────────────────────────

    def _inner_press(self, event):
        if event.button() != Qt.LeftButton:
            return
        child = self._inner.childAt(event.pos())
        while child and not child.property("drag_key"):
            child = child.parent()
        if child:
            self._drag_candidate = child.property("drag_key")
            self._drag_press_pos = event.pos()

    def _inner_move(self, event):
        if self._drag_candidate and not self._drag_key:
            if self._drag_press_pos and (event.pos() - self._drag_press_pos).manhattanLength() > 8:
                self._drag_key = self._drag_candidate
                self._drag_candidate = None
                self._inner.grabMouse()
            return

        if not self._drag_key or not self._config:
            return

        visible_keys = [k for k, _, _ in self._get_visible_items()]
        clean = [k for k in visible_keys if k != self._drag_key]
        idx = self._drop_index(event.pos(), clean)
        new_order = list(clean)
        new_order.insert(idx, self._drag_key)
        if new_order == visible_keys:
            return

        # Update card_order: merge new visible order with hidden entries
        all_keys = self._all_entry_keys()
        visible_set = set(visible_keys)
        hidden = [k for k in (self._config.card_order or all_keys) if k not in visible_set]
        merged = new_order + [k for k in hidden if k in set(all_keys)]
        # deduplicate while preserving order
        seen = set()
        deduped = []
        for k in merged:
            if k not in seen:
                deduped.append(k)
                seen.add(k)
        self._config.card_order = deduped
        self._lay_out()

    def _inner_release(self, event):
        if self._drag_candidate:
            self._drag_candidate = None
            self._drag_press_pos = None
            return
        if not self._drag_key:
            return
        self._inner.releaseMouse()
        self._drag_key = None
        self._lay_out()
        self.tool_order_changed.emit()

    def _get_visible_items(self) -> list[tuple[str, Tool, Entry]]:
        """Same filter logic as _lay_out but without rebuilding widgets."""
        result = []
        for key, tool, entry in self._ordered_entries():
            if entry.is_empty:
                continue
            if self._tool_filter and tool.name != self._tool_filter:
                continue
            if self._env_filter:
                env_names = [self._env_names.get(eid, eid) for eid in entry.envs]
                if self._env_filter not in env_names:
                    continue
            if not self._entry_visible(tool.name, entry):
                continue
            result.append((key, tool, entry))
        return result

    def _drop_index(self, pos: QPoint, clean: list[str]) -> int:
        chips = []
        seen = set()
        for i in range(self._layout.count()):
            rl = self._layout.itemAt(i).layout()
            if not rl:
                continue
            for j in range(rl.count()):
                w = rl.itemAt(j).widget()
                if not w:
                    continue
                key = w.property("drag_key")
                if not key or key not in clean or key in seen:
                    continue
                seen.add(key)
                tl = w.mapTo(self._inner, QPoint(0, 0))
                chips.append((clean.index(key), tl.x() + w.width() // 2, tl.y() + w.height() // 2))
        if not chips:
            return len(clean)

        chips.sort(key=lambda c: (c[2], c[1]))

        rows: list[list] = []
        cur = [chips[0]]
        for c in chips[1:]:
            if abs(c[2] - cur[0][2]) < 10:
                cur.append(c)
            else:
                rows.append(cur)
                cur = [c]
        rows.append(cur)

        for ri, row in enumerate(rows):
            row_cy = sum(c[2] for c in row) / len(row)
            boundary = (row_cy + sum(c[2] for c in rows[ri + 1]) / len(rows[ri + 1])) / 2 \
                if ri < len(rows) - 1 else float('inf')
            if pos.y() <= boundary:
                for idx, cx, _ in sorted(row, key=lambda c: c[1]):
                    if pos.x() < cx:
                        return idx
                return sorted(row, key=lambda c: c[1])[-1][0] + 1

        return chips[-1][0] + 1

    def _on_open(self, entry: Entry) -> None:
        from actions import open_url
        open_url(entry)

    def _on_ssh(self, entry: Entry) -> None:
        cmd = entry.ssh
        if cmd and cmd.startswith("claude"):
            from ui.cell_widget import ClaudeCodeDialog
            dlg = ClaudeCodeDialog(self._config.claude_models if self._config else [],
                                    self._config.claude_dirs if self._config else None, self)
            if dlg.exec():
                cmd = dlg.command()
            else:
                cmd = ""
        if entry.credentials:
            try:
                import pyperclip
                pyperclip.copy(entry.credentials[0].password)
            except Exception:
                pass
        if cmd:
            from actions import _open_terminal
            _open_terminal(cmd)

    def _on_show_creds(self, entry: Entry) -> None:
        from ui.cell_widget import CredentialDialog
        CredentialDialog(entry.credentials, self).exec()

    def _on_edit_entry(self, entry: Entry, tool: Tool) -> None:
        from ui.entry_edit_dialog import EntryEditDialog
        dlg = EntryEditDialog(entry, tool.name, self._config.environments,
                              self._config, self)
        if dlg.exec():
            self._lay_out()
            self.tool_order_changed.emit()


class _AddEntryDialog(QDialog):
    """Quick dialog to add a new entry to an existing tool."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("新增条目")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #1e1e2e; }}
            QLabel {{ color: #cdd6f4; font-size: 13px; }}
            QLineEdit {{ background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px 8px; font-size: 13px; }}
            QLineEdit:focus {{ border-color: #89b4fa; }}
            QComboBox {{ background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px 10px; font-size: 13px; }}
            QComboBox:focus {{ border-color: #89b4fa; }}
            QComboBox::drop-down {{ border: none; subcontrol-origin: padding;
                subcontrol-position: top right; width: 24px; border-left: 1px solid #45475a; }}
            QComboBox QAbstractItemView {{ background-color: #313244; color: #cdd6f4;
                selection-background-color: #45475a; border: 1px solid #45475a; }}
            QPushButton {{ background-color: #45475a; color: #cdd6f4; border: none;
                border-radius: 4px; padding: 6px 16px; font-size: 13px; }}
            QPushButton:hover {{ background-color: #585b70; }}
            QPushButton#save-btn {{ background-color: #89b4fa; color: #1e1e2e;
                font-weight: bold; font-size: 14px; padding: 8px 24px; }}
            QPushButton#save-btn:hover {{ background-color: #b4d0fb; }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Tool selector
        layout.addWidget(QLabel("工具"))
        self._tool_combo = QComboBox()
        for t in config.tools:
            self._tool_combo.addItem(t.name, t.id)
        layout.addWidget(self._tool_combo)

        # Type
        layout.addWidget(QLabel("类型"))
        self._type_combo = QComboBox()
        self._type_combo.addItem("Web 链接", "url")
        self._type_combo.addItem("SSH 终端", "ssh")
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self._type_combo)

        # URL / SSH field
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://example.com")
        layout.addWidget(self._url_edit)

        self._ssh_edit = QLineEdit()
        self._ssh_edit.setPlaceholderText("ssh user@host 或 claude")
        self._ssh_edit.hide()
        layout.addWidget(self._ssh_edit)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("save-btn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _on_type_changed(self):
        key = self._type_combo.currentData()
        self._url_edit.setVisible(key == "url")
        self._ssh_edit.setVisible(key == "ssh")

    def _save(self):
        tool_id = self._tool_combo.currentData()
        entry_type = self._type_combo.currentData()
        url = self._url_edit.text().strip() if entry_type == "url" else None
        ssh = self._ssh_edit.text().strip() if entry_type == "ssh" else None
        if not url and not ssh:
            return

        from models import Entry as E
        from config import save_config
        entry = E(envs=["general"], url=url or None, ssh=ssh or None)

        for t in self._config.tools:
            if t.id == tool_id:
                t.entries.append(entry)
                idx = len(t.entries) - 1
                self._config.card_order.append(f"{tool_id}:{idx}")
                break

        save_config(self._config)
        self.accept()
