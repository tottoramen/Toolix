"""Configuration loading, saving, and template generation."""

import json
import os
import subprocess
import sys
from pathlib import Path
from models import Config, FilterItem, Entry, Credential, Command, Field, ClaudeModel

# Module-level config path, set by main.py on startup
_config_file_path: Path | None = None


def set_config_path(path: str | Path) -> None:
    """Set the config file path. Called by main.py on startup."""
    global _config_file_path
    _config_file_path = Path(path)


def _config_path() -> Path | None:
    """Get config.json path, or None if not set."""
    return _config_file_path


def load_config() -> Config:
    """Load config.json, or generate a template if it doesn't exist."""
    path = _config_path()
    if path is None:
        raise RuntimeError("Config path not set. Call set_config_path() first.")
    if not path.exists():
        _write_template(path)
        return _template_config()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = _parse_config(data)
    if _dedupe(config):
        save_config(config)  # persist the auto-repair
    return config


def _dedupe(config: Config) -> bool:
    """Auto-repair duplicate / stale data so a polluted config can't crash the app.

    - items with the same (name, type): keep the first; tools absorb non-empty
      entries from the dupes.
    - card_order: drop stale + duplicate keys, append any missing.
    Returns True if anything changed (caller persists).
    """
    changed = False

    # items: merge by (name, type)
    by_key: dict[tuple, FilterItem] = {}
    order: list[tuple] = []
    for it in config.items:
        key = (it.name, it.type)
        if key in by_key:
            if it.type == "tool":
                for e in it.entries:
                    if not e.is_empty:
                        by_key[key].entries.append(e)
            changed = True
        else:
            by_key[key] = it
            order.append(key)
    if changed:
        config.items = [by_key[k] for k in order]

    # card_order: keep valid + unique, append any missing entry keys (tools only)
    valid = {f"{it.id}:{i}" for it in config.items if it.type == "tool"
             for i in range(len(it.entries))}
    seen_k: set[str] = set()
    new_card: list[str] = []
    for k in config.card_order:
        if k in valid and k not in seen_k:
            seen_k.add(k)
            new_card.append(k)
    for it in config.items:
        if it.type != "tool":
            continue
        for i in range(len(it.entries)):
            k = f"{it.id}:{i}"
            if k not in seen_k:
                seen_k.add(k)
                new_card.append(k)
    if len(new_card) != len(config.card_order):
        config.card_order = new_card
        changed = True

    return changed


def _parse_config(data: dict) -> Config:
    """Parse raw JSON dict into Config model."""
    items: list[FilterItem] = []

    # New format: single cross-mixed "items" array
    for it in data.get("items", []):
        t = it.get("type", "tool")
        if t == "tool":
            items.append(FilterItem(
                type="tool",
                id=it["id"],
                name=it["name"],
                icon=it.get("icon", ""),
                entries=_parse_entries(it),
            ))
        else:
            items.append(FilterItem(type="env", id=it["id"], name=it["name"]))

    # Backward compat: old format had separate "tools" + "environments" arrays.
    # If the old "filter_order" field exists, use it to preserve the user's
    # custom cross-mixed chip order; otherwise default to tools then envs.
    if not items:
        by_key: dict[tuple, FilterItem] = {}
        for t in data.get("tools", []):
            by_key[(t["name"], "tool")] = FilterItem(
                type="tool", id=t["id"], name=t["name"],
                icon=t.get("icon", ""), entries=_parse_entries(t))
        for e in data.get("environments", []):
            by_key[(e["name"], "env")] = FilterItem(type="env", id=e["id"], name=e["name"])

        for entry in data.get("filter_order", []):
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                key = (entry[0], entry[1])
                if key in by_key:
                    items.append(by_key.pop(key))
        for t in data.get("tools", []):
            key = (t["name"], "tool")
            if key in by_key:
                items.append(by_key.pop(key))
        for e in data.get("environments", []):
            key = (e["name"], "env")
            if key in by_key:
                items.append(by_key.pop(key))

    claude_models = [
        ClaudeModel(id=m["id"], name=m["name"], env=m.get("env", {}))
        for m in data.get("claude_models", [])
    ]
    claude_dirs = data.get("claude_dirs", ["claude", "udreader", "Toolix"])
    return Config(items=items,
                  claude_models=claude_models,
                  claude_dirs=claude_dirs,
                  tool_order=data.get("tool_order", []),
                  card_order=data.get("card_order", []))


def save_config(config: Config) -> None:
    """Save config back to config.json."""
    data = {
        "tool_order": config.tool_order,
        "card_order": config.card_order,
        "claude_dirs": config.claude_dirs,
        "claude_models": [
            {"id": m.id, "name": m.name, "env": m.env}
            for m in config.claude_models
        ],
        "items": [
            {"type": "tool", "id": it.id, "name": it.name, "icon": it.icon,
             "entries": [_entry_to_dict(e) for e in it.entries]}
            if it.type == "tool"
            else {"type": "env", "id": it.id, "name": it.name}
            for it in config.items
        ],
    }
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _parse_envs(entry_data: dict) -> list[str]:
    """Parse envs from entry data, supporting both old 'env' and new 'envs'."""
    envs = entry_data.get("envs")
    if envs is not None:
        return envs if isinstance(envs, list) else [envs]
    env = entry_data.get("env")
    if env is not None:
        return [env] if isinstance(env, str) else env
    return []


def _parse_entries(item: dict) -> list[Entry]:
    """Parse the 'entries' array of a tool item."""
    entries = []
    for entry_data in item.get("entries", []):
        creds = [
            Credential(
                label=c["label"],
                username=c.get("username", ""),
                password=c.get("password", ""),
                fields=[Field(key=f["key"], value=f["value"]) for f in c.get("fields", [])]
            )
            for c in entry_data.get("credentials", [])
        ]
        cmds = [
            Command(label=c["label"], command=c["command"])
            for c in entry_data.get("commands", [])
        ]
        entries.append(Entry(
            envs=_parse_envs(entry_data),
            url=entry_data.get("url"),
            ssh=entry_data.get("ssh"),
            credentials=creds,
            commands=cmds,
        ))
    return entries


def _entry_to_dict(entry: Entry) -> dict:
    d: dict = {"envs": entry.envs}
    if entry.url:
        d["url"] = entry.url
    if entry.ssh:
        d["ssh"] = entry.ssh
    if entry.credentials:
        d["credentials"] = [
            {"label": c.label, "username": c.username, "password": c.password,
             "fields": [{"key": f.key, "value": f.value} for f in c.fields]} if c.fields else
            {"label": c.label, "username": c.username, "password": c.password}
            for c in entry.credentials
        ]
    if entry.commands:
        d["commands"] = [
            {"label": c.label, "command": c.command}
            for c in entry.commands
        ]
    return d


def _write_template(path: Path) -> None:
    """Write an empty template config file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write("{}")


def _template_config() -> Config:
    """Return an empty template Config (matches _write_template)."""
    return Config()


def open_config_in_editor() -> None:
    """Open config.json in the system default editor."""
    path = str(_config_path())
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])
