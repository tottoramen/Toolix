#!/bin/bash
# macOS PyInstaller build script for Toolix
# Output: dist/Toolix/Toolix.app

set -e

echo "=== Killing old Toolix process ==="
killall Toolix 2>/dev/null || true

echo "=== Building with PyInstaller (onedir) ==="
pyinstaller -y --onedir --windowed \
  --name "Toolix" \
  --exclude-module PyQt5 \
  main.py

echo "=== Build complete ==="
echo "App bundle: dist/Toolix/Toolix.app"

echo ""
echo "=== Launching app ==="
open dist/Toolix/Toolix.app
