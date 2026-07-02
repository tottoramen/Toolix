"""Configuration loading, saving, and template generation."""

import json
import os
import sys
from pathlib import Path
from models import Config, Tool, Entry, Environment, Credential, Command, Field, ClaudeModel


def _config_path() -> Path:
    """Get the path to config.json in project-root user_data/ directory.

    Separated from dist/ so PyInstaller COLLECT never touches user data.
    """
    if getattr(sys, 'frozen', False):
        # exe is at dist/ToolPanel/ToolPanel.exe → go up 2 levels to project root
        base = Path(sys.executable).parent.parent.parent
    else:
        base = Path(__file__).parent  # config.py is in project root
    return base / "user_data" / "config.json"


def load_config() -> Config:
    """Load config.json, or generate a template if it doesn't exist."""
    path = _config_path()
    if not path.exists():
        _write_template(path)
        return _template_config()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return _parse_config(data)


def _parse_config(data: dict) -> Config:
    """Parse raw JSON dict into Config model."""
    environments = [
        Environment(id=e["id"], name=e["name"])
        for e in data.get("environments", [])
    ]
    tools = []
    for t in data.get("tools", []):
        entries = []
        for entry_data in t.get("entries", []):
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
        tools.append(Tool(
            id=t["id"],
            name=t["name"],
            icon=t.get("icon", ""),
            entries=entries,
        ))
    claude_models = [
        ClaudeModel(id=m["id"], name=m["name"], env=m.get("env", {}))
        for m in data.get("claude_models", [])
    ]
    return Config(tools=tools, environments=environments,
                  claude_models=claude_models,
                  filter_order=data.get("filter_order", []),
                  tool_order=data.get("tool_order", []),
                  card_order=data.get("card_order", []))


def save_config(config: Config) -> None:
    """Save config back to config.json."""
    data = {
        "filter_order": config.filter_order,
        "tool_order": config.tool_order,
        "card_order": config.card_order,
        "environments": [
            {"id": e.id, "name": e.name}
            for e in config.environments
        ],
        "claude_models": [
            {"id": m.id, "name": m.name, "env": m.env}
            for m in config.claude_models
        ],
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "icon": t.icon,
                "entries": [
                    _entry_to_dict(entry)
                    for entry in t.entries
                ]
            }
            for t in config.tools
        ]
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
    """Write a template config file with example data."""
    template = {
        "environments": [
            {"id": "prod", "name": "生产环境"},
            {"id": "test", "name": "测试环境"},
        ],
        "tools": [
            {
                "id": "example-tool",
                "name": "示例工具",
                "icon": "",
                "entries": [
                    {
                        "envs": ["prod"],
                        "url": "https://example.com",
                        "credentials": [
                            {"label": "admin", "username": "admin", "password": "your-password"}
                        ]
                    }
                ]
            }
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)


def _template_config() -> Config:
    """Return a template Config object (matches _write_template)."""
    return Config(
        environments=[
            Environment(id="prod", name="生产环境"),
            Environment(id="test", name="测试环境"),
        ],
        tools=[
            Tool(
                id="example-tool",
                name="示例工具",
                icon="",
                entries=[
                    Entry(
                        envs=["prod"],
                        url="https://example.com",
                        credentials=[
                            Credential(label="admin", username="admin", password="your-password")
                        ]
                    )
                ]
            )
        ]
    )


def open_config_in_editor() -> None:
    """Open config.json in the system default editor."""
    path = str(_config_path())
    os.startfile(path)
