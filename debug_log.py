"""Debug logging for Toolix — OFF by default.

Enable by setting the environment variable ``TOOLIX_DEBUG=1`` before launch:
  PowerShell:  `$env:TOOLIX_DEBUG=1; & ".\\dist\\Toolix\\Toolix.exe"`
  cmd:         `set TOOLIX_DEBUG=1 && dist\\Toolix\\Toolix.exe`

When disabled (the default), ``log()`` / ``init()`` are no-ops and no file is
created — zero overhead for daily use. When enabled, traces go to
``~/toolix-debug.log`` (line-buffered + flushed) and faulthandler dumps the
C-level stack there on a segfault, so the last log line pinpoints the crash.
"""
import os
import sys
import datetime
import faulthandler

LOG_PATH = os.path.join(os.path.expanduser("~"), "toolix-debug.log")

_enabled_cache: bool | None = None
_fp = None


def _enabled() -> bool:
    global _enabled_cache
    if _enabled_cache is None:
        _enabled_cache = os.environ.get("TOOLIX_DEBUG", "").lower() in ("1", "true", "yes")
    return _enabled_cache


def _ensure():
    global _fp
    if _fp is None:
        try:
            # buffering=1 → line-buffered, so each written line hits disk
            _fp = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        except Exception:
            _fp = False
    return _fp


def init():
    """Call once at startup: open log + arm faulthandler. No-op when disabled."""
    if not _enabled():
        return
    fp = _ensure()
    if not fp:
        return
    faulthandler.enable(fp)
    log(f"=== Toolix start  frozen={getattr(sys, 'frozen', False)} "
        f"pid={os.getpid()} exe={sys.executable!r} ===")


def log(msg: str):
    if not _enabled():
        return
    fp = _ensure()
    if not fp:
        return
    try:
        fp.write(f"{datetime.datetime.now():%H:%M:%S.%f} {msg}\n")
        fp.flush()
    except Exception:
        pass
