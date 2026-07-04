"""Action dispatchers for tool entries."""

import os
import subprocess
import sys
import webbrowser
from models import Entry


def open_url(entry: Entry) -> None:
    """Open the entry's URL in the default browser."""
    if entry.url:
        webbrowser.open(entry.url)


def copy_credential(cred_index: int, entry: Entry) -> None:
    """Copy a credential's password to clipboard. cred_index indexes into entry.credentials."""
    try:
        import pyperclip
        cred = entry.credentials[cred_index]
        pyperclip.copy(cred.password)
    except ImportError:
        pass


def run_ssh(entry: Entry) -> None:
    """Open a terminal window and run the SSH command."""
    if not entry.ssh:
        return
    _open_terminal(entry.ssh)


def run_command(cmd_index: int, entry: Entry) -> None:
    """Open a terminal window and run the command at cmd_index."""
    try:
        cmd = entry.commands[cmd_index]
        _open_terminal(cmd.command)
    except IndexError:
        pass


def _open_terminal(command: str) -> None:
    """Open a terminal window and execute the given command.

    Windows: prefers Windows Terminal (wt.exe), falls back to cmd.exe.
    macOS: opens Terminal.app.
    Linux: uses x-terminal-emulator.
    """
    if sys.platform == "darwin":
        # macOS: open Terminal.app and run the command
        escaped = command.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(
            ["open", "-a", "Terminal", "--args", escaped],
        )
    elif sys.platform == "win32":
        # Use home dir as CWD instead of exe directory,
        # otherwise orphan terminals lock dist/Toolix on rebuild.
        home = os.path.expanduser("~")
        # Try Windows Terminal first
        try:
            subprocess.Popen(
                ["wt.exe", "-d", home, "cmd", "/k", command],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return
        except FileNotFoundError:
            pass

        # Fall back to cmd.exe
        subprocess.Popen(
            ["cmd", "/k", command],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=home,
        )
    else:
        # Linux fallback
        subprocess.Popen(
            ["x-terminal-emulator", "-e", f"bash -c '{command}; exec bash'"],
        )
