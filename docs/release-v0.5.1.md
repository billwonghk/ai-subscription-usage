# AI Subscription Usage v0.5.1

## 中文：从 v0.5.0 升级

v0.5.1 新增繁體中文界面和说明，语言数量由七种增加到八种：简体中文、繁體中文、English、日本語、한국어、Français、Deutsch 和 Español。语言可在设置中即时切换，报表、设置、配置及使用说明、状态栏或系统托盘菜单同步更新，不修改用量、价格或订阅计划数据。

macOS 发布包按处理器拆分。Apple Silicon Mac（M1 及后续芯片）下载 `AI-Subscription-Usage-macOS-Apple-Silicon.zip`；Intel Mac 下载 `AI-Subscription-Usage-macOS-Intel.zip`。两个安装包分别在 GitHub 的 arm64 和 x86_64 macOS Runner 上原生构建，发布前检查应用主程序的实际架构。Intel 包已经通过自动构建、自检和隐私检查，尚未在 Intel Mac 真机人工操作。

Windows 继续提供两个独立文件：`AI-Subscription-Usage-0.5.1-Windows-Setup.exe` 是安装版，提供开始菜单入口和卸载功能；`AI-Subscription-Usage-Windows-Portable.zip` 是绿色版，解压后直接运行。Windows x64 Runner 会运行打包后的主程序和安装器，执行自检、诊断、数据源验证、后台刷新、托盘进程生命周期、UTF-8 繁体中文页面渲染以及重新安装保留用户数据测试。Windows Edge 渲染截图作为 CI 验收附件保存，不进入正式 Release。Windows 系统托盘的鼠标点击和菜单布局尚未在 Windows 真机人工操作。

下载的四个程序文件互相独立，用户只需选择与自己的操作系统和处理器对应的一个文件。正式 Release 同时提供 `SHA256SUMS.txt`。程序文件与用户数据分离；升级不会删除订阅计划、数据源配置、语言设置、诊断授权或本机报表。

发布包和源码在构建前后执行隐私检查，不包含个人订阅记录、本机用量、生成报表、密码、API Key、Cookie、OAuth/Auth Token、私人服务地址或本机绝对路径。

macOS 因没有开通 Apple Developer Program 付费会员，无法使用 Developer ID 签名和 Apple 公证，因此不提供 macOS 自动安装更新。用户需要手动下载并替换应用。Windows 应用内直接下载安装仍未实现，用户需要从 GitHub Releases 下载新版安装包或绿色版。

## English: changes since v0.5.0

v0.5.1 adds a Traditional Chinese interface and documentation, increasing the language count from seven to eight: Simplified Chinese, Traditional Chinese, English, Japanese, Korean, French, German and Spanish. Language changes apply immediately to the report, Settings, configuration guide and menu-bar or system-tray menu without changing usage, pricing or subscription-plan data.

macOS downloads are now split by processor. Apple Silicon Macs (M1 and newer) use `AI-Subscription-Usage-macOS-Apple-Silicon.zip`; Intel Macs use `AI-Subscription-Usage-macOS-Intel.zip`. Each package is built natively on the corresponding GitHub arm64 or x86_64 macOS runner, and the main executable architecture is checked before release. The Intel package passes automated build, self-test and privacy checks but has not been operated manually on a physical Intel Mac.

Windows continues to provide two independent files: `AI-Subscription-Usage-0.5.1-Windows-Setup.exe` is the normal installer with Start Menu and uninstall support; `AI-Subscription-Usage-Windows-Portable.zip` is the portable edition. The packaged application and installer run on a Windows x64 runner for self-test, diagnostics, source verification, background refresh, tray-process lifecycle, UTF-8 Traditional Chinese page rendering and reinstall data-retention checks. A Windows Edge rendering screenshot is retained as a CI verification artifact and is not included in the public Release. System-tray mouse clicks and menu layout have not been operated manually on physical Windows hardware.

The four program downloads are independent; users select one file for their operating system and processor. The Release also includes `SHA256SUMS.txt`. Application files and user data remain separate, so upgrading does not remove subscription plans, source configuration, language selection, diagnostics consent or locally generated reports.

Source and packaged artifacts pass privacy checks. They do not contain personal subscription records, local usage, generated reports, passwords, API keys, cookies, OAuth/Auth tokens, private service addresses or personal absolute paths.

macOS does not provide automatic installation because the project has no paid Apple Developer Program membership and therefore cannot use Developer ID signing or Apple notarization. Users must download and replace the application manually. Direct in-app installation is not implemented on Windows either; download the new installer or portable package from GitHub Releases.
