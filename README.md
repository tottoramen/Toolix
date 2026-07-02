# Toolix

> 卡片式工具快速启动面板 — URL / SSH / Claude Code / 凭据管理，一应俱全。

A tag-based tool launcher with a card layout — open URLs, SSH terminals, Claude Code sessions, and manage credentials, all from a single panel.

<img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python"> <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License"> <img src="https://img.shields.io/badge/platform-Windows-lightgrey" alt="Platform">

## ✨ 功能

- **卡片流式布局** — 工具卡片自动排列，支持拖拽排序
- **标签筛选** — 点击工具或环境的标签，即时过滤卡片
- **多标签支持** — 一个入口可以同时打上多个环境标签
- **多种启动方式** — URL → 浏览器 / SSH → 终端 / Claude Code → 专用对话框
- **凭据管理** — 内置凭据弹窗，一键复制用户名/密码/Token
- **模型切换** — Claude Code 启动时可选不同 API 端点与模型
- **配置驱动** — 纯 JSON 配置，无需改代码即可添加工具和环境
- **Catppuccin Mocha 主题** — 暗色风格，护眼舒适

## 🚀 快速开始

> **平台**: Windows 10/11。终端启动依赖 Windows Terminal (wt.exe) 或 cmd.exe。

### 开发运行

```powershell
pip install -r requirements.txt
python main.py
```

### 配置

复制 `config.example.json` 为 `user_data/config.json`，按需修改：

```bash
mkdir user_data
cp config.example.json user_data/config.json
```

配置结构见 [config.example.json](config.example.json)，或参考下方文档。

### 打包 exe

```powershell
pyinstaller -y --onedir --windowed --name "Toolix" --icon icon.ico --exclude-module PyQt5 main.py
```

`user_data/config.json` 与 exe 分离，更新配置无需重新打包。

## 🧱 架构

```
main.py              — QMainWindow, 信号连接, filter_bar ↔ matrix 双向联动
config.py            — JSON 配置加载/保存, 模板生成, 新旧格式兼容
models.py            — 数据模型: Entry, Environment, Tool, Config
actions.py           — 启动动作: 浏览器/终端/Claude Code
ui/
  search_bar.py      — 搜索框
  filter_bar.py      — 可拖拽排序标签栏 (工具+环境混排)
  matrix_table.py    — 卡片流式布局, 标签点击筛选, 拖拽排序
  cell_widget.py     — 凭据弹窗, Claude Code 启动对话框
  style.py           — Catppuccin Mocha 暗色主题
  flow_layout.py     — 自定义流式布局
  tool_list.py       — 工具列表侧边栏
user_data/config.json — 用户配置 (不入库)
```

## 📝 配置文件结构

```json
{
  "filter_order": [["工具名", "tool"], ["环境名", "env"]],
  "card_order": ["tool-id:0", "tool-id:1"],
  "claude_models": [
    {
      "id": "model-id",
      "name": "显示名称",
      "env": {
        "ANTHROPIC_BASE_URL": "https://api.example.com",
        "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
        "ANTHROPIC_MODEL": "model-name"
      }
    }
  ],
  "environments": [
    { "id": "env-id", "name": "环境名称" }
  ],
  "tools": [
    {
      "id": "tool-id",
      "name": "工具名称",
      "entries": [
        {
          "envs": ["env-id"],
          "url": "https://example.com",
          "ssh": "user@host",
          "credentials": [
            { "label": "admin", "username": "admin", "password": "xxx" }
          ],
          "commands": [
            { "label": "命令名", "command": "echo hello" }
          ]
        }
      ]
    }
  ]
}
```

### 凭据格式

```json
// 用户名 + 密码
{ "label": "admin", "username": "admin", "password": "xxx" }

// 仅 Token
{ "label": "API Key", "password": "sk-xxx" }

// 自定义字段
{ "label": "平台", "fields": [
  { "key": "租户", "value": "kiwi" },
  { "key": "账号", "value": "admin" }
]}
```

### Claude 模型配置

```json
{
  "id": "my-model",
  "name": "My Model",
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.example.com",
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_MODEL": "model-id"
  }
}
```

> **注意**: `ANTHROPIC_BASE_URL` 不要带 `/v1` 后缀，Claude Code 会自动追加。

## 🔧 技术栈

- Python 3.10+
- PySide6 (Qt for Python)
- PyInstaller (打包)

## 📄 License

Apache License 2.0 — 详见 [LICENSE](LICENSE)
