"""Action dispatchers for tool entries."""

import os
import re
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


def _ensure_ssh_hostkey(command: str) -> str:
    """If *command* is an SSH invocation:
    1. On Windows, force C:\\Windows\\System32\\OpenSSH\\ssh.exe (native OpenSSH)
       to avoid MSYS2 SSH (Git) mangling Chinese usernames in paths.
    2. Inject -o StrictHostKeyChecking=accept-new so the terminal doesn't hang
       on the interactive (yes/no) prompt.
    """
    m = re.match(r'^(\s*(?:\S*[/\\])?ssh(?:\.exe)?)(\s|$)', command)
    if not m:
        return command

    # On Windows, always use the native OpenSSH client
    if sys.platform == "win32":
        native_ssh = os.path.expandvars(r"%SystemRoot%\System32\OpenSSH\ssh.exe")
        command = native_ssh + command[m.end(1):]

    # Avoid interactive host-key prompt
    if not re.search(r'-o\s+StrictHostKeyChecking=', command):
        return re.sub(r'(ssh(?:\.exe)?)', r'\1 -o StrictHostKeyChecking=accept-new', command, count=1)

    return command


def _open_terminal(command: str) -> None:
    """Open a terminal window and execute the given command.

    Windows: prefers Windows Terminal (wt.exe), falls back to cmd.exe.
    macOS: opens Terminal.app.
    Linux: uses x-terminal-emulator.
    """
    command = _ensure_ssh_hostkey(command)
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
