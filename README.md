# Batch Video Downloader for Windows

一个 Windows 10/11 桌面工具，用来批量输入页面 URL，自动解析页面中的 `m3u8` / `mp4` / `webm` 等视频地址，并异步下载。

`m3u8` 下载会调用 [N_m3u8DL-CLI](https://github.com/nilaoda/N_m3u8DL-CLI/releases)，下载后合并为视频文件。普通 `mp4/webm` 等直链会直接下载。

## 功能

- Tkinter 桌面界面，Windows 原生可运行
- 批量粘贴 URL，一行一个
- 自动提取页面标题作为视频文件名
- 从 HTML、`video/source` 标签、meta、脚本 JSON、转义 URL 中寻找视频链接
- 通过 Playwright 监听浏览器 Network 请求/响应，捕获页面源码里没有、但播放时才请求的 `m3u8/mp4`
- Network 中捕获多个 `m3u8` 时，优先按 `Content-Length` 选择最大的那个
- 支持 `m3u8` master playlist 中选择最高带宽/分辨率子流
- 异步下载，可设置并发数
- 支持 HTTP/SOCKS5 代理，并可传递给 N_m3u8DL-CLI

## 快速开始

首次初始化：

```powershell
scripts\setup_windows.bat
```

国内网络如果 PyPI 访问不稳定：

```powershell
scripts\setup_windows_cn_mirror.bat
```

启动：

```powershell
start_app.bat
```

如果启动失败，需要查看诊断输出，可以运行 `run_app.bat`。

## 手动安装

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
python -m src.app
```

## 配置 N_m3u8DL-CLI

1. 打开 [N_m3u8DL-CLI Releases](https://github.com/nilaoda/N_m3u8DL-CLI/releases)
2. 下载 Windows 版本压缩包并解压
3. 推荐把 `N_m3u8DL-CLI.exe` 放到：

```text
tools\N_m3u8DL-CLI\N_m3u8DL-CLI.exe
```

也可以在界面里手动选择 exe 路径。

## 代理

代理格式示例：

```text
http://127.0.0.1:7890
socks5://127.0.0.1:7890
```

## 自检

```powershell
.\.venv\Scripts\python.exe scripts\self_check.py
.\.venv\Scripts\python.exe scripts\network_check.py
```

更完整的迁移说明见 [PORTABLE_WINDOWS.md](PORTABLE_WINDOWS.md)。

## 注意

- 页面本身是 `mp4/m3u8` 直链时会跳过页面解析，直接下载
- 遇到需要登录、验证码或 DRM 加密的视频，本工具不会绕过权限或 DRM
- 仅下载你有权访问和保存的视频内容

## 免责声明

本项目仅用于学习、研究和下载你有合法访问权与保存权的公开视频资源。使用者应自行确认目标网站的服务条款、版权声明以及当地法律法规，并承担由使用本工具产生的全部责任。

本项目不会绕过登录权限、付费墙、验证码、DRM、加密授权或其他访问控制措施，也不鼓励、支持或协助任何侵犯版权、违反网站条款或非法传播内容的行为。

本项目依赖第三方工具 [N_m3u8DL-CLI](https://github.com/nilaoda/N_m3u8DL-CLI/releases) 处理 `m3u8` 下载与合并。第三方工具的功能、许可、行为和风险由其各自项目负责，请在使用前自行阅读其说明与许可证。

如果你是内容版权所有者或网站运营方，并认为本项目说明或示例存在不当之处，请通过 issue 联系维护者处理。
