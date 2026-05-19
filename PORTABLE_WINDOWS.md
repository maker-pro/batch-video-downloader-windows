# Windows 可移植部署说明

把项目拷贝到另一台 Windows 10/11 后，建议按下面的清单准备。

## 必需环境

- Windows 10 或 Windows 11
- Python 3.10+，安装时勾选 `Add Python to PATH`
- N_m3u8DL-CLI.exe

推荐目录：

```text
tools\N_m3u8DL-CLI\N_m3u8DL-CLI.exe
```

如果没有放在这个目录，也可以在软件界面里手动选择 exe。

## 首次初始化

普通网络环境：

```powershell
scripts\setup_windows.bat
```

国内网络如果 PyPI 慢，可以试：

```powershell
scripts\setup_windows_cn_mirror.bat
```

初始化脚本会完成：

- 创建 `.venv`
- 安装 `requirements.txt`
- 安装 Playwright Chromium
- 创建 `downloads` 和 `tools\N_m3u8DL-CLI` 目录

## 启动

```powershell
start_app.bat
```

或：

```powershell
.\.venv\Scripts\python.exe -m src.app
```

`run_app.bat` 会显示运行时检查和错误信息，适合排查问题；`start_app.bat` 更适合日常双击启动。

## 哪些文件建议一起拷贝

必须拷贝：

- `src\`
- `scripts\`
- `requirements.txt`
- `requirements-core.txt`
- `run_app.bat`
- `start_app.bat`
- `README.md`
- `PORTABLE_WINDOWS.md`
- `config.example.json`

建议拷贝：

- `tools\N_m3u8DL-CLI\N_m3u8DL-CLI.exe`

不建议拷贝：

- `.venv\`
- `__pycache__\`
- `downloads\`
- `config.json`

`config.json` 是本机配置，里面可能有本机路径和代理设置。迁移到新机器后重新在界面里设置更稳。

## 离线迁移建议

如果目标机器不能联网，需要提前在有网络的机器上准备：

- Python 安装包
- `N_m3u8DL-CLI.exe`
- pip wheel 缓存或完整 `.venv`
- Playwright 浏览器缓存

最稳的方式是在目标机器允许联网初始化一次；如果必须离线，建议先在同版本 Windows、同 Python 版本环境下创建 `.venv`，再整体拷贝项目。

## 自检

```powershell
.\.venv\Scripts\python.exe scripts\self_check.py
.\.venv\Scripts\python.exe scripts\network_check.py
```
