"""Unified filter bar — auto-wrap. Drag-reorderable chips with live animation."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QDialog, QLabel, QLineEdit, QButtonGroup, QRadioButton,
)
from PySide6.QtCore import Signal, Qt, QPoint, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
import re

from models import Tool, Entry, Environment


def _to_kebab(name: str) -> str:
    """Convert Chinese/English name to kebab-case id."""
    # Try pinyin-like: just use a sanitized version
    s = name.lower().strip().replace(" ", "-")
    s = re.sub(r"[^a-z0-9一-鿿-]", "", s)
    return s if s else "new-item"


BASE      = "#1e1e2e"
SURFACE   = "#313244"
OVERLAY   = "#45475a"
TEXT      = "#cdd6f4"
SUBTEXT   = "#a6adc8"
BLUE      = "#89b4fa"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"

CHIP_DIALOG_STYLE = f"""
    QDialog {{ background-color: {BASE}; }}
    QLabel {{ color: {TEXT}; font-size: 13px; }}
    QLineEdit {{ background-color: {SURFACE}; color: {TEXT}; border: 1px solid {OVERLAY};
        border-radius: 4px; padding: 5px 8px; font-size: 13px; }}
    QLineEdit:focus {{ border-color: {BLUE}; }}
    QRadioButton {{ color: {TEXT}; font-size: 13px; spacing: 8px; }}
    QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 8px;
        border: 2px solid {OVERLAY}; background-color: {SURFACE}; }}
    QRadioButton::indicator:checked {{ border-color: {BLUE}; background-color: {BLUE}; }}
    QPushButton {{ background-color: {OVERLAY}; color: {TEXT}; border: none;
        border-radius: 4px; padding: 5px 14px; font-size: 12px; }}
    QPushButton:hover {{ background-color: #585b70; }}
    QPushButton#save-btn {{ background-color: {BLUE}; color: {BASE};
        font-weight: bold; font-size: 14px; padding: 6px 20px; }}
    QPushButton#save-btn:hover {{ background-color: #b4d0fb; }}
"""


class _ChipEditDialog(QDialog):
    """Edit a filter chip's name and type (tool / env)."""

    def __init__(self, name: str, ftype: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增标签" if not name else "编辑标签")
        self.setMinimumWidth(320)
        self.setStyleSheet(CHIP_DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Name
        layout.addWidget(QLabel("名称"))
        self._name_edit = QLineEdit(name)
        layout.addWidget(self._name_edit)

        # Type
        layout.addWidget(QLabel("类型"))
        self._type_group = QButtonGroup(self)
        type_row = QHBoxLayout()
        type_row.setSpacing(16)
        for key, label in [("tool", "工具"), ("env", "标签")]:
            rb = QRadioButton(label)
            rb.setProperty("type_key", key)
            rb.setChecked(key == ftype)
            self._type_group.addButton(rb)
            type_row.addWidget(rb)
        type_row.addStretch()
        layout.addLayout(type_row)

        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("save-btn")
        save_btn.clicked.connect(self.accept)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def result(self) -> tuple[str, str] | None:
        """Return (name, ftype) if accepted, else None."""
        if self.exec() == QDialog.Rejected:
            return None
        name = self._name_edit.text().strip()
        if not name:
            return None
        rb = self._type_group.checkedButton()
        ftype = rb.property("type_key") if rb else "tool"
        return (name, ftype)


class _DragButton(QPushButton):
    clicked_signal = Signal(str)
    gear_clicked = Signal(str, str)  # (name, ftype)

    def __init__(self, text, ftype, color, bg, parent=None):
        super().__init__(text, parent)
        self._drag_start: QPoint | None = None
        self._ftype = ftype
        self._color = QColor(color)
        self._bg = QColor(bg)
        self._hover = False
        self._gear_hover = False
        self._active = False
        self.setMouseTracking(True)
        self.setMinimumHeight(30)
        # strip global stylesheet
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self._gear_hover = False
        self.update()

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()

    def mouseMoveEvent(self, event):
        # gear / text hover tracking
        on_gear = self.width() - event.pos().x() < 32
        if on_gear != self._gear_hover:
            self._gear_hover = on_gear
            self.update()
        self.setCursor(Qt.PointingHandCursor if on_gear else Qt.ArrowCursor)
        # drag detection
        if self._drag_start and (event.buttons() & Qt.LeftButton):
            if (event.pos() - self._drag_start).manhattanLength() >= 8:
                self._drag_start = None
                fb = self.parent()
                while fb and not isinstance(fb, FilterBar):
                    fb = fb.parent()
                if isinstance(fb, FilterBar):
                    fb.start_drag(self._chip_name(), self._ftype)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            ds = self._drag_start
            self._drag_start = None
            if (event.pos() - ds).manhattanLength() < 8:
                if self.width() - event.pos().x() < 32:
                    self.gear_clicked.emit(self._chip_name(), self._ftype)
                else:
                    self.clicked_signal.emit(self._chip_name())

    def paintEvent(self, event):
        from PySide6.QtGui import QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gear_w = 28

        # Colors
        if self._active:
            bg, fg, border = self._color, QColor("#1e1e2e"), self._color
            gear_bg = self._color
        elif self._gear_hover:
            bg, fg, border = self._bg, self._color, self._color
            gear_bg = QColor("#313244")
        elif self._hover:
            bg, fg, border = self._bg, self._color, self._color
            gear_bg = self._bg
        else:
            bg, fg, border = self._bg, self._color, Qt.transparent
            gear_bg = self._bg

        # Clip to pill shape for clean gear overlay
        pill_path = QPainterPath()
        pill_path.addRoundedRect(r, 10, 10)
        p.setClipPath(pill_path)

        # Full pill background
        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(r, 10, 10)

        # Gear area overlay
        if self._gear_hover and not self._active:
            gear_r = QRectF(r.right() - gear_w, r.y(), gear_w, r.height())
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(gear_bg))
            p.drawRect(gear_r)  # clipped to pill, so right corners follow pill shape

        # Re-draw border over everything
        p.setClipping(False)
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 10, 10)

        # Text
        p.setPen(QPen(fg))
        font = QFont(self.font())
        font.setPixelSize(16)
        font.setBold(True)
        p.setFont(font)
        p.drawText(r.adjusted(16, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        p.end()

    def _chip_name(self) -> str:
        t = self.text()
        if t.endswith("⚙"):
            t = t[:-1].strip()
        return t


class FilterBar(QWidget):
    tool_clicked = Signal(str)
    env_clicked = Signal(str)
    filters_changed = Signal()  # emitted when chips are added/edited/deleted

    def __init__(self, parent=None):
        super().__init__(parent)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(8, 2, 8, 2)
        self._outer.setSpacing(2)
        self._active_chip: QPushButton | None = None
        self._items: list[tuple[str, str]] = []
        self._last_w = 0
        self._drag_item: str | None = None
        self._drag_ftype: str | None = None
        self._config = None
        self._save_fn = None

    def set_config(self, config, save_fn) -> None:
        self._config = config
        self._save_fn = save_fn

    def set_filters(self, tools: list[str], envs: list[str]) -> None:
        all_items = [(t, "tool") for t in tools] + [(e, "env") for e in envs]
        saved = self._config.filter_order if self._config else []
        if saved:
            valid = set(all_items)
            ordered = [(x[0], x[1]) for x in saved if isinstance(x, (list, tuple)) and len(x) == 2 and tuple(x[:2]) in valid]
            self._items = ordered + [x for x in all_items if x not in ordered]
        else:
            self._items = all_items
        self._last_w = 0
        self._build()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() != self._last_w:
            self._last_w = self.width()
            self._build()

    def _build(self):
        self._clear()
        w = max(self.width() - 16, 200)
        row = QHBoxLayout(); row.setSpacing(2)
        self._outer.addLayout(row)
        x = 0

        # + add button
        add_btn = self._make_add_btn()
        row, x = self._place(row, x, w, add_btn)

        for name, ftype in self._items:
            btn = self._make_chip(name, ftype)
            row, x = self._place(row, x, w, btn)
        row.addStretch()

    def _make_add_btn(self):
        btn = QPushButton("+")
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; color: {SUBTEXT};
                border: 1px dashed {OVERLAY}; border-radius: 14px;
                font-size: 16px; font-weight: bold; padding: 0; }}
            QPushButton:hover {{ border-color: {BLUE}; color: {BLUE}; background-color: #313244; }}
        """)
        btn.clicked.connect(self._on_add_chip)
        return btn

    def _on_add_chip(self):
        dlg = _ChipEditDialog("", "tool", self)
        res = dlg.result()
        if res is None:
            return
        name, ftype = res
        if self._config is None:
            return

        # Add to config
        if ftype == "tool":
            tid = _to_kebab(name)
            self._config.tools.append(Tool(id=tid, name=name, entries=[Entry(envs=["general"])]))
            self._config.card_order.append(f"{tid}:0")
        else:
            eid = _to_kebab(name)
            self._config.environments.append(Environment(id=eid, name=name))

        self._items.append((name, ftype))
        self._save_order()
        self._build()
        self.filters_changed.emit()

    def _make_chip(self, name: str, ftype: str):
        color, bg = ("#89b4fa", "#1e2a3a") if ftype == "tool" else ("#a6adc8", "#252a35")

        display = f"{name}  ⚙"
        btn = _DragButton(display, ftype, color, bg)
        btn.setProperty("filter_type", ftype)
        btn.setProperty("drag_key", f"{name}:{ftype}")
        btn.clicked_signal.connect(self._on_tool if ftype == "tool" else self._on_env)
        btn.gear_clicked.connect(self._on_edit_chip)

        return btn

    def _place(self, row, x, max_w, widget):
        bw = widget.sizeHint().width() + 4
        if x > 0 and x + bw > max_w:
            row.addStretch()
            row = QHBoxLayout(); row.setSpacing(2)
            self._outer.addLayout(row)
            x = 0
        row.addWidget(widget)
        return row, x + bw

    def _clear(self):
        while self._outer.count():
            item = self._outer.takeAt(0)
            w = item.widget()
            if w: w.hide(); w.setParent(None)
            sub = item.layout()
            if sub:
                while sub.count():
                    si = sub.takeAt(0)
                    if si.widget(): si.widget().hide(); si.widget().setParent(None)
        self._active_chip = None

    # ── chip edit ─────────────────────────────────────────────────

    def _on_edit_chip(self, name: str, ftype: str = ""):
        dlg = _ChipEditDialog(name, ftype, self)
        res = dlg.result()
        if res is None:
            return
        new_name, new_ftype = res

        # Update filter_order
        old_key = (name, ftype)
        new_key = (new_name, new_ftype)
        if new_key == old_key:
            return

        # Update items list
        for i, item in enumerate(self._items):
            if item == old_key:
                self._items[i] = new_key
                break

        # Update underlying config objects
        if self._config:
            if ftype == "tool":
                for t in self._config.tools:
                    if t.name == name:
                        t.name = new_name
                        break
            else:
                for e in self._config.environments:
                    if e.name == name:
                        e.name = new_name
                        break

        self._save_order()
        self._build()
        self.filters_changed.emit()

    # ── drag ─────────────────────────────────────────────────────

    def start_drag(self, name: str, ftype: str):
        if self._drag_item:
            return
        self._drag_item = name
        self._drag_ftype = ftype
        QTimer.singleShot(0, lambda: self.grabMouse())

    def mouseMoveEvent(self, event):
        if not self._drag_item:
            return
        key = (self._drag_item, self._drag_ftype)
        clean = [x for x in self._items if x != key]
        idx = self._drop_index(event.pos(), clean)
        new_items = list(clean)
        new_items.insert(idx, key)
        if new_items == self._items:
            return
        self._items = new_items
        self._build()

    def mouseReleaseEvent(self, event):
        if not self._drag_item:
            return
        self.releaseMouse()
        self._drag_item = None
        self._drag_ftype = None
        self._build()
        self._save_order()

    def _drop_index(self, pos: QPoint, clean: list[tuple[str, str]]) -> int:
        rows: dict[int, list[tuple[tuple, int, int]]] = {}
        for i in range(self._outer.count()):
            row_layout = self._outer.itemAt(i).layout()
            if not row_layout:
                continue
            for j in range(row_layout.count()):
                w = row_layout.itemAt(j).widget()
                if not isinstance(w, _DragButton):
                    continue
                key = (w._chip_name(), w.property("filter_type") or "")
                if key not in clean:
                    continue
                center = w.mapTo(self, w.rect().center())
                ry = round(center.y() / 10) * 10
                rows.setdefault(ry, []).append((key, center.x(), clean.index(key)))
        if not rows:
            return len(clean)
        nearest_y = min(rows, key=lambda y: abs(pos.y() - y))
        chips = sorted(rows[nearest_y], key=lambda c: c[1])
        for key, cx, list_idx in chips:
            if pos.x() < cx:
                return list_idx
        return chips[-1][2] + 1

    def _save_order(self):
        if self._config is not None:
            self._config.filter_order = [[n, ft] for n, ft in self._items]
            if self._save_fn:
                self._save_fn()

    # ── click / toggle ───────────────────────────────────────────

    def _on_tool(self, name): self._toggle(name, self.tool_clicked)
    def _on_env(self, name):  self._toggle(name, self.env_clicked)

    def _toggle(self, name, signal):
        btn = self._find(name)
        if self._active_chip is btn:
            self._deactivate(); signal.emit(""); return
        if self._active_chip:
            self._active_chip.set_active(False)
        self._active_chip = btn
        btn.set_active(True)
        signal.emit(name)

    def _find(self, name):
        for i in range(self._outer.count()):
            sub = self._outer.itemAt(i).layout()
            if sub:
                for j in range(sub.count()):
                    w = sub.itemAt(j).widget()
                    if isinstance(w, _DragButton) and w._chip_name() == name:
                        return w
        return None

    def _deactivate(self):
        if self._active_chip:
            self._active_chip.set_active(False)
        self._active_chip = None

    def select_tool(self, name: str) -> None:
        btn = self._find(name)
        if btn is None: return
        self._deactivate()
        self._active_chip = btn
        btn.set_active(True)

    def select_env(self, name: str) -> None:
        btn = self._find(name)
        if btn is None: return
        self._deactivate()
        self._active_chip = btn
        btn.set_active(True)

    def reset(self):
        self._deactivate()
