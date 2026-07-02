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
class Tool:
    """A tool row in the matrix."""
    id: str
    name: str
    icon: str = ""
    entries: list[Entry] = field(default_factory=list)

    def get_entry(self, env_id: str) -> Optional[Entry]:
        """Return the first entry matching the given env_id, or None."""
        for e in self.entries:
            if env_id in e.envs:
                return e
        return None


@dataclass
class Environment:
    """An environment tag."""
    id: str
    name: str


@dataclass
class ClaudeModel:
    """A Claude Code model option in the launch dialog."""
    id: str
    name: str
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    """Root configuration loaded from config.json."""
    tools: list[Tool] = field(default_factory=list)
    environments: list[Environment] = field(default_factory=list)
    claude_models: list[ClaudeModel] = field(default_factory=list)
    filter_order: list[list[str]] = field(default_factory=list)  # [[name, ftype], ...]
    tool_order: list[str] = field(default_factory=list)           # [tool_id, ...]
    card_order: list[str] = field(default_factory=list)           # ["tool_id:entry_idx", ...]
