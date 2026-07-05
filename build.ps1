# Windows PyInstaller build script for Toolix
# Output: dist/Toolix/Toolix.exe

$ErrorActionPreference = "Stop"

Write-Host "=== Killing old Toolix process ===" -ForegroundColor Cyan
Stop-Process -Name Toolix -Force -ErrorAction SilentlyContinue

Write-Host "=== Building with PyInstaller (onedir) ===" -ForegroundColor Cyan
# PyInstaller writes progress to stderr; switch to Continue so that native
# stderr output doesn't abort the script under $ErrorActionPreference=Stop.
$ErrorActionPreference = "Continue"
pyinstaller -y --onedir --windowed `
  --name "Toolix" `
  --icon icon.ico `
  --exclude-module PyQt5 `
  main.py
$build_rc = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($build_rc -ne 0) {
    throw "PyInstaller failed with exit code $build_rc"
}

Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "exe: dist/Toolix/Toolix.exe"

Write-Host ""
Write-Host "=== Launching ===" -ForegroundColor Cyan
Start-Process "dist/Toolix/Toolix.exe"
