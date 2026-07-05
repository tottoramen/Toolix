"""Data models for the tool control panel."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Field:
    """A key-value field within a credential."""
    key: str
    value: str


@dataclass
class Credential:
    """A credential entry with optional username/password and extra fields."""
    label: str
    username: str = ""
    password: str = ""
    fields: list[Field] = field(default_factory=list)


@dataclass
class Command:
    """A named shell command to execute."""
    label: str
    command: str


@dataclass
class Entry:
    """
    One cell in the tool×environment matrix.
    envs: list of Environment.id values this entry applies to.
    At least one action field (url/ssh/credentials/commands) should be present.
    """
    envs: list[str] = field(default_factory=list)
    url: Optional[str] = None
    ssh: Optional[str] = None
    credentials: list[Credential] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """An entry with no actionable data is considered empty."""
        return not (self.url or self.ssh or self.credentials or self.commands)


@dataclass
class FilterItem:
    """A filter chip — either a tool (with entries) or an environment tag.
    config.items order is the cross-mixed chip order shown in the filter bar."""
    type: str  # "tool" | "env"
    id: str
    name: str
    icon: str = ""
    entries: list[Entry] = field(default_factory=list)

    def get_entry(self, env_id: str) -> Optional[Entry]:
        """tool-only: first entry matching env_id, or None."""
        for e in self.entries:
            if env_id in e.envs:
                return e
        return None

    @property
    def is_empty(self) -> bool:
        """tool-only: True if no actionable entry."""
        return not any(not e.is_empty for e in self.entries)


# Backwards-compatible aliases so older code can keep importing Tool / Environment.
Tool = FilterItem
Environment = FilterItem


@dataclass
class ClaudeModel:
    """A Claude Code model option in the launch dialog."""
    id: str
    name: str
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    """Root configuration loaded from config.json."""
    items: list[FilterItem] = field(default_factory=list)         # cross-mixed tool/env chips
    claude_models: list[ClaudeModel] = field(default_factory=list)
    claude_dirs: list[str] = field(default_factory=list)          # subdir names under D:\projects\
    tool_order: list[str] = field(default_factory=list)           # [tool_id, ...]
    card_order: list[str] = field(default_factory=list)           # ["tool_id:entry_idx", ...]

    @property
    def tools(self) -> list[FilterItem]:
        return [it for it in self.items if it.type == "tool"]

    @property
    def environments(self) -> list[FilterItem]:
        return [it for it in self.items if it.type == "env"]
