# CLAUDE.md

## 项目

Toolix — 桌面工具控制面板。Python + PySide6。用户说"面板"即指此应用。

## 开发

```
改 Python → 杀进程 → PyInstaller --onedir → 启动 exe
```

```powershell
# 运行
python D:/projects/Toolix/main.py

# 打包 + 启动（推荐）
D:/projects/Toolix/build.ps1
```

## 配置修改流程

配置文件 `toolix.json`，首次运行用户选择目录，QSettings 持久化。

1. **Read** `toolix.json`，确认现有 tools/environments
2. **改** — 增删改联动：
   - 加环境 → `environments` + `filter_order`
   - 加工具 → `tools` + `filter_order` + `card_order`
   - 删环境 → 先确认无 entry 引用，再删 `environments` + `filter_order`
   - 删工具 → 清理 `filter_order` + `card_order`
   - 加模型 → 追加到 `claude_models` 数组
3. **校验** — `python -c "import json; c=json.load(open('toolix.json','r',encoding='utf-8')); print('OK')"`
4. **重启** — `Stop-Process -Name Toolix -Force; Start-Process "dist/Toolix/Toolix.exe"`

关键约束：
- `envs` 用数组 `["env-id"]`，不用字符串
- `credentials` 复数，值是数组
- `tools[].id` kebab-case 全局唯一
- `ANTHROPIC_BASE_URL` 不带 `/v1`
- 打包用 `--onedir`，不用 `--onefile`

## ClaudeCodeDialog

- 工作目录: `D:\projects\` 下的子目录，由 `toolix.json` 的 `claude_dirs` 数组驱动（默认 `["claude", "udreader", "Toolix"]`）
- macOS 下工作目录自动切换为 `~/projects/`
- 模型列表由 `toolix.json` 的 `claude_models` 驱动
- 启动: Windows 写临时 ps1 → `powershell -NoExit -ExecutionPolicy Bypass -File`（不能用 bat）
- 启动: macOS 写临时 .command → `chmod 755` → `open -a Terminal`
- QSettings("Kiwi", "Toolix") 记忆选择
