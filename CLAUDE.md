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

# debug 阶段：带日志直接 python 跑（改完代码立即验证，不必打包）
$env:TOOLIX_DEBUG=1; python D:/projects/Toolix/main.py

# 打包 + 启动（推荐，发布前）
D:/projects/Toolix/build.ps1

# 带日志启动 exe（排查打包版问题，日志写入 ~/toolix-debug.log）
$env:TOOLIX_DEBUG=1; & "D:/projects/Toolix/dist/Toolix/Toolix.exe"
```

**mac 一键安装**（在 mac 上执行,产出 `/Applications/Toolix.app`,可重复运行即更新）：

```bash
bash install_mac.sh          # 装到 /Applications(可能提示 sudo 密码)
bash install_mac.sh --user   # 装到 ~/Applications(无需 sudo)
```

流程:平台检测 → Python 3.10+ → 建 `.venv` → 装依赖(requirements.txt + pyinstaller)→ killall → `pyinstaller --onedir --windowed`(命令行参数,不用 Windows 专用的 `Toolix.spec`)→ 装到目标目录 → `xattr -dr com.apple.quarantine` 去隔离 → `open` 启动。

## 调试

`debug_log.py` 提供 trace 日志 + `faulthandler`（segfault 时把 C 栈 dump 到同一文件）。**默认关闭、零开销** —— `init()`/`log()` 首行即 return，不建文件、不挂 handler。

- **开关**：环境变量 `TOOLIX_DEBUG=1`（取值 `1`/`true`/`yes`，大小写不敏感）；不设即关
  - PowerShell: `$env:TOOLIX_DEBUG=1; & "D:/projects/Toolix/dist/Toolix/Toolix.exe"`
  - cmd: `set TOOLIX_DEBUG=1 && dist\Toolix\Toolix.exe`
  - 源码同理: `$env:TOOLIX_DEBUG=1; python main.py`
- **日志路径**: `~/toolix-debug.log`（即 `C:\Users\<user>\toolix-debug.log`），追加写、行缓冲 + 每次 flush
- **判定点**: `_enabled()` 进程内只算一次（缓存到 `_enabled_cache`），运行中改环境变量必须**重启**才生效
- **埋点**: `_on_add_chip` / `_on_edit_chip` / `FilterBar._build` / `FilterBar._clear` / `MatrixTable._lay_out` / `MatrixTable.set_config` / `MainWindow._on_filters_changed`
- **segfault 定位**: faulthandler 自动把 C 栈 dump 到日志末尾 —— 最后一条 trace = 崩溃点

排查闪退：`TOOLIX_DEBUG=1` 启动 → 复现 → 看日志最后一条 + 末尾栈 dump。

## 配置修改流程

配置文件 `toolix.json`，首次运行用户选择目录，QSettings 持久化。

1. **Read** `toolix.json`，确认现有 tools/environments
2. **改** — 增删改联动：
   - 加环境 → `environments`
   - 加工具 → `tools` + `card_order`
   - 删环境 → 先确认无 entry 引用，再删 `environments`
   - 删工具 → 清理 `card_order`
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

启动本地 Claude Code 的对话框。**加/改/删模型只动 `toolix.json` 的 `claude_models`，零代码改动，重启面板生效。** 不用读 `config.py`/`cell_widget.py`/`models.py`。

`claude_models` 是数组，每项三个字段：

```json
{
  "id": "glm-5.2-2",            // 必须全局唯一：对话框按 id 建 env 映射、QSettings 存 claude/model
  "name": "GLM-5.2 (2)",        // 对话框单选项显示名
  "env": {                      // 启动时全部注入临时脚本，再跑 claude
    "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<key>",
    "ANTHROPIC_MODEL": "glm-5.2[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.2[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-5.2[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.7"
  }
}
```

- 加模型 → 复制一项，改 `id`（唯一）+ `name` + `env`，追加到 `claude_models`
- 删模型 → 直接删该项
- 改 key/端点/模型映射 → 改对应项的 `env`，别动代码
- 可选 env：`CLAUDE_CODE_SUBAGENT_MODEL`（子 agent 模型，未设回退主力）、`CLAUDE_CODE_EFFORT_LEVEL`（`low`/`medium`/`high`/`max`）、`CLAUDE_CODE_AUTO_COMPACT_WINDOW`
- env 注入：Windows 写 `$env:KEY = 'value'` 进临时 .ps1 → `powershell -NoExit -ExecutionPolicy Bypass -File`（不能用 bat）；macOS 写 `export KEY='value'` 进 .command → `chmod 755` → `open -a Terminal`
- 工作目录: `D:\projects\` 下子目录，由 `claude_dirs` 驱动（默认 `["claude", "udreader", "Toolix"]`）；macOS 自动切 `~/projects/`
- QSettings("Kiwi", "Toolix") 记 `claude/dir` + `claude/model`
