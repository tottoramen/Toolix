"""Entry edit dialog — edit all fields of a tool entry in-app."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QScrollArea, QWidget, QGroupBox, QFrame,
    QListWidget, QListWidgetItem, QComboBox, QApplication,
)
from PySide6.QtCore import Qt, Signal, QPoint, QEvent

from models import Entry, Environment, Credential, Field, Config
from config import save_config


# ── Catppuccin Mocha colour palette ──────────────────────────────
BASE      = "#1e1e2e"
SURFACE   = "#313244"
OVERLAY   = "#45475a"
TEXT      = "#cdd6f4"
SUBTEXT   = "#a6adc8"
BLUE      = "#89b4fa"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
YELLOW    = "#f9e2af"

STYLE = f"""
    QDialog {{ background-color: {BASE}; }}
    QLabel {{ color: {TEXT}; font-size: 13px; }}
    QLabel#section-title {{ color: {BLUE}; font-size: 14px; font-weight: bold; }}
    QLabel#tool-name {{ color: {BLUE}; font-size: 16px; font-weight: bold; }}
    QLineEdit {{ background-color: {SURFACE}; color: {TEXT}; border: 1px solid {OVERLAY};
        border-radius: 4px; padding: 5px 8px; font-size: 13px; }}
    QLineEdit:focus {{ border-color: {BLUE}; }}
    QGroupBox {{ color: {TEXT}; font-size: 13px; font-weight: bold;
        border: 1px solid {OVERLAY}; border-radius: 6px; margin-top: 12px; padding-top: 16px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
    QPushButton {{ background-color: {OVERLAY}; color: {TEXT}; border: none;
        border-radius: 4px; padding: 5px 14px; font-size: 12px; }}
    QPushButton:hover {{ background-color: #585b70; }}
    QPushButton#add-btn {{ background-color: {GREEN}; color: {BASE}; font-weight: bold; }}
    QPushButton#add-btn:hover {{ background-color: #c6f0c2; }}
    QPushButton#del-btn {{ background-color: {RED}; color: {BASE}; font-weight: bold; }}
    QPushButton#del-btn:hover {{ background-color: #fab7c1; }}
    QPushButton#save-btn {{ background-color: {BLUE}; color: {BASE};
        font-weight: bold; font-size: 15px; padding: 8px 28px; }}
    QPushButton#save-btn:hover {{ background-color: #b4d0fb; }}
    QComboBox {{ background-color: {SURFACE}; color: {TEXT}; border: 1px solid {OVERLAY};
        border-radius: 4px; padding: 6px 10px; font-size: 13px; }}
    QComboBox:focus {{ border-color: {BLUE}; }}
    QComboBox::drop-down {{ border: none; subcontrol-origin: padding;
        subcontrol-position: top right; width: 24px; border-left: 1px solid {OVERLAY}; }}
    QComboBox QAbstractItemView {{ background-color: {SURFACE}; color: {TEXT};
        selection-background-color: {OVERLAY}; border: 1px solid {OVERLAY}; }}
    QFrame#sep {{ background-color: {OVERLAY}; max-height: 1px; }}
    QScrollArea {{ border: none; background-color: {BASE}; }}
"""

POPUP_STYLE = f"""
    QListWidget {{ background-color: {SURFACE}; color: {TEXT}; border: 1px solid {OVERLAY};
        border-radius: 4px; font-size: 13px; outline: none; }}
    QListWidget::item {{ padding: 4px 8px; }}
    QListWidget::item:hover {{ background-color: {OVERLAY}; }}
"""


class MultiSelectCombo(QWidget):
    """Dropdown button that opens a checkable list popup — compact multi-select."""

    selection_changed = Signal()

    def __init__(self, items: list[tuple[str, str, bool]], parent=None):
        """
        items: list of (id, name, checked)
        """
        super().__init__(parent)
        self._items: list[dict] = [
            {"id": id_, "name": name, "checked": checked}
            for id_, name, checked in items
        ]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn = QPushButton()
        self._btn.setStyleSheet(f"""
            QPushButton {{ background-color: {SURFACE}; color: {TEXT};
                border: 1px solid {OVERLAY}; border-radius: 4px;
                padding: 6px 28px 6px 10px; font-size: 13px; text-align: left; }}
            QPushButton:hover {{ border-color: {BLUE}; }}
            QPushButton::after {{ content: "▾"; position: absolute; right: 10px; }}
        """)
        self._btn.clicked.connect(self._show_popup)
        layout.addWidget(self._btn)

        self._popup: QListWidget | None = None
        self._refresh_label()

    def _refresh_label(self):
        selected = [it["name"] for it in self._items if it["checked"]]
        if not selected:
            self._btn.setText("未选择")
            self._btn.setStyleSheet(self._btn.styleSheet().replace(f"color: {TEXT}", f"color: {SUBTEXT}"))
        elif len(selected) <= 3:
            self._btn.setText("、".join(selected))
        else:
            self._btn.setText(f"已选 {len(selected)} 项")

    def _show_popup(self):
        if self._popup:
            self._popup.close()
            self._popup = None
            return

        popup = QWidget(self, Qt.Window | Qt.FramelessWindowHint)
        popup.setStyleSheet(POPUP_STYLE)
        popup.installEventFilter(self)

        v = QVBoxLayout(popup)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        search = QLineEdit()
        search.setPlaceholderText("搜索…")
        search.setClearButtonEnabled(True)
        search.setStyleSheet("QLineEdit { background-color: #313244; color: #cdd6f4; "
                             "border: none; border-bottom: 1px solid #45475a; "
                             "padding: 6px 8px; border-radius: 0; }")
        v.addWidget(search)

        list_w = QListWidget()
        list_w.setMinimumWidth(self._btn.width())
        for it in self._items:
            item = QListWidgetItem(it["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if it["checked"] else Qt.Unchecked)
            item.setData(Qt.UserRole, it["id"])
            list_w.addItem(item)
        list_w.itemChanged.connect(lambda: self._on_popup_changed(list_w))
        v.addWidget(list_w)

        search.textChanged.connect(lambda t: self._filter_list(list_w, t))

        # Fixed list height = whole rows; scroll if more than max_rows.
        row_h = list_w.sizeHintForRow(0)
        if row_h > 0:
            max_rows = 10
            rows = min(len(self._items), max_rows)
            list_w.setFixedHeight(row_h * rows + 2 * list_w.frameWidth())
        popup.setMinimumWidth(max(self._btn.width(), 180))

        # Position below the button
        pos = self._btn.mapToGlobal(QPoint(0, self._btn.height() + 2))
        popup.move(pos)
        popup.show()
        search.setFocus()
        self._popup = popup

        # Install app-level event filter to close popup on outside click
        QApplication.instance().installEventFilter(self)

    def _filter_list(self, list_w, text: str) -> None:
        """Hide rows whose text doesn't contain the search string (case-insensitive)."""
        t = text.lower().strip()
        for i in range(list_w.count()):
            it = list_w.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    def eventFilter(self, obj, event):
        """Close popup when clicking outside (app-level) + track hide."""
        if event.type() == QEvent.Hide:
            if obj is self._popup:
                self._popup = None
                QApplication.instance().removeEventFilter(self)
        elif event.type() == QEvent.MouseButtonPress and self._popup:
            # Close popup if click is outside both the popup and the button
            popup = self._popup
            click_global = event.globalPos() if hasattr(event, 'globalPos') else event.globalPosition().toPoint()
            inside_popup = popup.geometry().contains(click_global)
            inside_btn = self._btn.rect().contains(self._btn.mapFromGlobal(click_global))
            if not inside_popup and not inside_btn:
                popup.close()
        return super().eventFilter(obj, event)

    def _on_popup_changed(self, popup: QListWidget):
        for i in range(popup.count()):
            item = popup.item(i)
            eid = item.data(Qt.UserRole)
            checked = item.checkState() == Qt.Checked
            for it in self._items:
                if it["id"] == eid:
                    it["checked"] = checked
                    break
        self._refresh_label()
        self.selection_changed.emit()

    def checked_ids(self) -> list[str]:
        return [it["id"] for it in self._items if it["checked"]]

    def close_popup(self):
        if self._popup:
            self._popup.close()
            self._popup = None
            QApplication.instance().removeEventFilter(self)


class EntryEditDialog(QDialog):
    """Edit all fields of an Entry: URL, SSH, envs, credentials, commands."""

    def __init__(self, entry: Entry, tool_name: str,
                 all_environments: list[Environment], config: Config, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._all_envs = all_environments
        self._config = config

        self.setWindowTitle(f"编辑 — {tool_name}")
        self.setMinimumSize(520, 500)
        self.resize(560, 640)
        self.setStyleSheet(STYLE)

        # ── scrollable root ───────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)

        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        # ── Tool name ─────────────────────────────────────────────
        tool_lbl = QLabel(tool_name)
        tool_lbl.setObjectName("tool-name")
        layout.addWidget(tool_lbl)

        sep = QFrame()
        sep.setObjectName("sep")
        layout.addWidget(sep)

        # ── Type selector ─────────────────────────────────────────
        layout.addWidget(QLabel("类型", objectName="section-title"))
        self._type_combo = QComboBox()
        self._type_combo.addItem("Web 链接", "url")
        self._type_combo.addItem("SSH 终端", "ssh")
        layout.addWidget(self._type_combo)

        # Detect initial type: SSH if entry has ssh, otherwise URL
        initial = "ssh" if entry.ssh else "url"
        for i in range(self._type_combo.count()):
            if self._type_combo.itemData(i) == initial:
                self._type_combo.setCurrentIndex(i)
                break

        # ── URL ───────────────────────────────────────────────────
        self._url_section = QWidget()
        url_v = QVBoxLayout(self._url_section)
        url_v.setContentsMargins(0, 0, 0, 0); url_v.setSpacing(6)
        url_v.addWidget(QLabel("URL", objectName="section-title"))
        self._url_edit = QLineEdit(entry.url or "")
        self._url_edit.setPlaceholderText("https://example.com")
        url_v.addWidget(self._url_edit)
        layout.addWidget(self._url_section)

        # ── SSH ───────────────────────────────────────────────────
        self._ssh_section = QWidget()
        ssh_v = QVBoxLayout(self._ssh_section)
        ssh_v.setContentsMargins(0, 0, 0, 0); ssh_v.setSpacing(6)
        ssh_v.addWidget(QLabel("SSH", objectName="section-title"))
        self._ssh_edit = QLineEdit(entry.ssh or "")
        self._ssh_edit.setPlaceholderText("ssh user@host 或 claude")
        ssh_v.addWidget(self._ssh_edit)
        layout.addWidget(self._ssh_section)

        # Wire type selector
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._on_type_changed()

        # ── Environments ──────────────────────────────────────────
        layout.addWidget(QLabel("标签", objectName="section-title"))
        env_items = [(e.id, e.name, e.id in entry.envs) for e in all_environments]
        self._env_combo = MultiSelectCombo(env_items)
        layout.addWidget(self._env_combo)

        # Close popup when clicking blank space in scroll area
        scroll.viewport().installEventFilter(self)

        # ── Credentials ───────────────────────────────────────────
        layout.addWidget(QLabel("凭据", objectName="section-title"))
        self._cred_area = QVBoxLayout()
        self._cred_area.setSpacing(8)
        layout.addLayout(self._cred_area)

        add_cred_btn = QPushButton("+ 添加凭据")
        add_cred_btn.setObjectName("add-btn")
        add_cred_btn.clicked.connect(lambda checked: self._add_credential())
        layout.addWidget(add_cred_btn)

        # ── Buttons ───────────────────────────────────────────────
        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        del_btn = QPushButton("🗑 删除此配置")
        del_btn.setObjectName("del-btn")
        del_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("save-btn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        # ── Populate existing data ────────────────────────────────
        self._cred_rows: list[dict] = []  # list of widget dicts per credential
        self._deleted = False
        for cred in entry.credentials:
            self._add_credential(cred)

    # ── Credential rows ───────────────────────────────────────────

    def eventFilter(self, obj, event):
        """Close env popup when clicking blank space in the scroll area."""
        if event.type() == QEvent.MouseButtonPress:
            self._env_combo.close_popup()
        return super().eventFilter(obj, event)

    def hideEvent(self, event):
        """Close the env popup whenever the dialog hides (accept/reject/X)."""
        self._env_combo.close_popup()
        super().hideEvent(event)

    def _add_credential(self, cred: Credential | None = None):
        """Append one credential group (pre-filled if cred given).
        Username/password rows only appear when the cred actually has them
        (or for a fresh credential) — clearing them persists as absent."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet(f"QFrame {{ background-color: {SURFACE}; border: 1px solid {OVERLAY}; "
                            f"border-radius: 6px; padding: 8px; }}")
        v = QVBoxLayout(frame)
        v.setSpacing(6)

        # Header row: label + remove
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("名称"))
        lbl_edit = QLineEdit(cred.label if cred else "")
        lbl_edit.setPlaceholderText("admin / API Key")
        hdr.addWidget(lbl_edit, 1)

        rm_btn = QPushButton("✕ 删除")
        rm_btn.setObjectName("del-btn")
        rm_btn.clicked.connect(lambda: self._remove_credential(frame))
        hdr.addWidget(rm_btn)
        v.addLayout(hdr)

        row_data: dict = {"frame": frame, "label": lbl_edit, "field_rows": []}

        # Username row — only if cred has a username (or it's a fresh credential)
        if cred is None or cred.username:
            u_row = QHBoxLayout()
            u_key_edit = QLineEdit("用户")
            u_key_edit.setPlaceholderText("键")
            u_key_edit.setFixedWidth(60)
            u_row.addWidget(u_key_edit)
            u_val_edit = QLineEdit(cred.username if cred and cred.username else "")
            u_val_edit.setPlaceholderText("值")
            u_row.addWidget(u_val_edit, 1)
            u_rm_btn = QPushButton("✕")
            u_rm_btn.setFixedWidth(28)
            u_rm_btn.setStyleSheet(
                f"QPushButton {{ background-color: {RED}; color: {BASE}; "
                f"border-radius: 3px; padding: 2px; font-size: 11px; }}")
            u_row.addWidget(u_rm_btn)
            v.addLayout(u_row)
            row_data["user_row"] = {"layout": u_row, "key_edit": u_key_edit,
                                    "value_edit": u_val_edit, "rm_btn": u_rm_btn}
            u_rm_btn.clicked.connect(lambda checked, rd=row_data: self._remove_field_row(rd, "user_row"))

        # Password row — only if cred has a password (or it's a fresh credential)
        if cred is None or cred.password:
            p_row = QHBoxLayout()
            p_key_edit = QLineEdit("密码")
            p_key_edit.setPlaceholderText("键")
            p_key_edit.setFixedWidth(60)
            p_row.addWidget(p_key_edit)
            p_val_edit = QLineEdit(cred.password if cred and cred.password else "")
            p_val_edit.setPlaceholderText("值")
            p_row.addWidget(p_val_edit, 1)
            p_rm_btn = QPushButton("✕")
            p_rm_btn.setFixedWidth(28)
            p_rm_btn.setStyleSheet(
                f"QPushButton {{ background-color: {RED}; color: {BASE}; "
                f"border-radius: 3px; padding: 2px; font-size: 11px; }}")
            p_row.addWidget(p_rm_btn)
            v.addLayout(p_row)
            row_data["pass_row"] = {"layout": p_row, "key_edit": p_key_edit,
                                    "value_edit": p_val_edit, "rm_btn": p_rm_btn}
            p_rm_btn.clicked.connect(lambda checked, rd=row_data: self._remove_field_row(rd, "pass_row"))

        # Custom fields
        fields_layout = QVBoxLayout()
        fields_layout.setSpacing(4)
        v.addLayout(fields_layout)
        row_data["fields_layout"] = fields_layout

        add_f_btn = QPushButton("+ 添加字段")
        add_f_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; color: {GREEN}; "
                                f"border: 1px dashed {OVERLAY}; font-size: 11px; padding: 3px 8px; }}")
        v.addWidget(add_f_btn)

        self._cred_rows.append(row_data)
        self._cred_area.addWidget(frame)
        add_f_btn.clicked.connect(lambda checked, rd=row_data: self._add_field(rd))

        # Pre-fill fields
        if cred:
            for f in cred.fields:
                self._add_field(row_data, f)

    def _add_field(self, row_data: dict, field: Field | None = None):
        """Add one key-value row inside a credential group."""
        f_row = QHBoxLayout()
        k_edit = QLineEdit(field.key if field else "")
        k_edit.setPlaceholderText("键")
        k_edit.setFixedWidth(60)
        f_row.addWidget(k_edit)
        v_edit = QLineEdit(field.value if field else "")
        v_edit.setPlaceholderText("值")
        f_row.addWidget(v_edit, 1)

        rm_f_btn = QPushButton("✕")
        rm_f_btn.setFixedWidth(28)
        rm_f_btn.setStyleSheet(
            f"QPushButton {{ background-color: {RED}; color: {BASE}; "
            f"border-radius: 3px; padding: 2px; font-size: 11px; }}")
        rm_f_btn.clicked.connect(lambda: self._remove_field(row_data, f_row, k_edit, v_edit, rm_f_btn))
        f_row.addWidget(rm_f_btn)

        # Insert before the + button (which is last in fields_layout's parent vbox)
        idx = row_data["fields_layout"].count()
        row_data["fields_layout"].insertLayout(idx, f_row)
        row_data["field_rows"].append((f_row, k_edit, v_edit, rm_f_btn))

    def _remove_field_row(self, row_data, row_key):
        """Remove user_row or pass_row from a credential group."""
        entry = row_data.pop(row_key, None)
        if entry is None:
            return
        self._clear_layout(entry["layout"])
        entry["key_edit"].deleteLater()
        entry["value_edit"].deleteLater()
        entry["rm_btn"].deleteLater()

    def _remove_field(self, row_data, f_row_layout, k_edit, v_edit, rm_btn):
        """Remove a single custom field row."""
        row_data["field_rows"] = [
            fr for fr in row_data["field_rows"] if fr[0] is not f_row_layout
        ]
        self._clear_layout(f_row_layout)
        k_edit.deleteLater(); v_edit.deleteLater(); rm_btn.deleteLater()

    def _remove_credential(self, frame: QFrame):
        """Remove an entire credential group."""
        idx = None
        for i, rd in enumerate(self._cred_rows):
            if rd["frame"] is frame:
                idx = i
                break
        if idx is not None:
            self._cred_rows.pop(idx)
        self._cred_area.removeWidget(frame)
        frame.hide(); frame.deleteLater()

    # ── Type / save ────────────────────────────────────────────

    def _type_key(self) -> str:
        return self._type_combo.currentData() or "url"

    def _on_type_changed(self):
        key = self._type_key()
        self._url_section.setVisible(key == "url")
        self._ssh_section.setVisible(key == "ssh")

    def _save(self):
        """Write all fields back to the entry, save config, accept."""
        # URL / SSH — clear the field not matching selected type
        key = self._type_key()
        if key == "url":
            self._entry.url = self._url_edit.text().strip() or None
            self._entry.ssh = None
        else:
            self._entry.url = None
            self._entry.ssh = self._ssh_edit.text().strip() or None

        # Envs
        self._entry.envs = self._env_combo.checked_ids()

        # Credentials
        new_creds: list[Credential] = []
        for rd in self._cred_rows:
            label = rd["label"].text().strip()
            username = ""
            password = ""
            fields: list[Field] = []

            # User row (key="用户" → username; else → custom field)
            ur = rd.get("user_row")
            if ur:
                k = ur["key_edit"].text().strip()
                v = ur["value_edit"].text().strip()
                if k or v:
                    if k == "用户":
                        username = v
                    else:
                        fields.append(Field(key=k, value=v))

            # Pass row (key="密码" → password; else → custom field)
            pr = rd.get("pass_row")
            if pr:
                k = pr["key_edit"].text().strip()
                v = pr["value_edit"].text().strip()
                if k or v:
                    if k == "密码":
                        password = v
                    else:
                        fields.append(Field(key=k, value=v))

            # Custom fields
            for _, k_edit, v_edit, _ in rd["field_rows"]:
                k = k_edit.text().strip()
                v = v_edit.text().strip()
                if k or v:
                    fields.append(Field(key=k, value=v))

            # Keep credential even if label is empty (user intent)
            new_creds.append(Credential(
                label=label, username=username, password=password, fields=fields
            ))
        self._entry.credentials = new_creds

        save_config(self._config)
        self.accept()

    def _on_delete(self):
        """Confirm and mark this entry for deletion; caller checks is_deleted()."""
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "删除配置",
                                "确定删除该配置？此操作不可撤销。"
                                ) == QMessageBox.StandardButton.Yes:
            self._deleted = True
            self.accept()

    def is_deleted(self) -> bool:
        return self._deleted

    # ── Utility ───────────────────────────────────────────────────

    @staticmethod
    def _clear_layout(layout):
        """Remove all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide(); w.setParent(None)
            sub = item.layout()
            if sub:
                EntryEditDialog._clear_layout(sub)
