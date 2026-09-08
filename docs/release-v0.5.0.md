# AI Subscription Usage v0.5.0

## 中文：从 v0.4.1 升级

本版本增加平台管理。用户在设置中添加或移除需要统计的平台，顶部汇总、平台标签和曲线随选择变化；没有用量记录的平台不绘制曲线。新增 MiniMax 本机用量读取，统计普通输入、缓存和输出，并进入 API 等价价值与 DeepSeek 对比计算。

新增 Kimi CLI Wire 格式读取，以及 Kimi、GLM、阿里百炼的专用 Claude Code 日志目录绑定。绑定目录按订阅平台归属，不按模型名称猜测订阅来源；已绑定目录排除在默认 Claude 扫描之外，重叠目录配置被拒绝。Kimi Wire 不记录模型 ID 时只统计 Token，不虚构模型或单价。三平台适配依据公开格式和测试样本实现，不承诺所有桌面客户端或混合订阅历史均可读取。

订阅计划支持人民币与美元。金额保留原始币种，报表按日期使用 ECB 参考汇率换算；提供生效日期、计划历史和设置内的删除入口。模型单价与 DeepSeek 对应关系按平台分组显示。价格更新保留日期区间，缓存写入价格变化也建立历史记录；无法计价的记录保留 Token，并标明计算范围。

明确标为 Auto 的记录按配置中该日期适用的订阅最低价模型估算，同时对应 DeepSeek V4 Flash；MiniMax M3 对应 V4 Pro，M2.7 对应 V4 Flash。记录有准确时间时按配置的高峰与空闲价格计算，缺少准确时间时使用空闲价格。金额是公开 API 价格下的参考估算，不是订阅服务商账单。

报表采用缓存优先：点击状态栏打开已有报表，不先等待扫描。应用运行时按本机时间凌晨 3:00 调度后台刷新；当天尚未成功更新时，启动 15 分钟后补更新。手动刷新保留。新增单实例控制，重复启动通知已有应用，退出取消定时任务并关闭本机监听。Windows 安装器关闭运行中的应用后替换程序。

设置中可即时切换中文与英文，同步报表、说明及状态栏菜单，不修改用量或订阅数据。补齐货币、汇率、保存失败、Auto 估算和部分计价的英文提示。修正无效设置误报成功、请求长度校验、价格非有限数与重叠日期校验，以及旧 Release 被错误提示为新版本的问题。

发布包不携带个人配置、密码、API Key、私人服务地址、诊断日志、订阅记录或用量报表。旧版用量截图不再包含在本版本源码中。安装包和待发布源码均执行隐私规则检查；已有 Git 历史不在本次重写范围内。

升级时下载对应平台安装包。Windows 支持安装器或便携版；应用内直接下载安装尚未实现。macOS 因没有开通 Apple Developer Program 付费会员，不使用 Developer ID 签名和 Apple 公证，需要手动下载并替换应用。程序文件与用户数据分离，更新保留现有配置和订阅记录。语音、实时音频和 Dictation 的独立消耗不纳入本版本统计。

## English: changes since v0.4.1

Provider management lets users add or remove the platforms they want to track. Summary totals, equal-width provider tabs and charts follow that selection. Providers without usage records do not create chart lines. MiniMax local metering now contributes regular input, cache and output usage to API-equivalent value and DeepSeek comparisons.

Added Kimi CLI Wire parsing and explicit, dedicated Claude Code log-directory bindings for Kimi, GLM and Alibaba Bailian. Ownership follows the subscription binding rather than the model name. Bound directories are excluded from default Claude scanning, and overlapping bindings are rejected. Kimi records without a model ID retain token counts but remain unpriced. These adapters are based on public formats and test fixtures; support for every desktop client or mixed-subscription history is not claimed.

Subscription plans retain their original USD or CNY currency. Reports use dated ECB reference exchange rates, effective dates and plan history. Deletion stays in Settings. Pricing and DeepSeek mappings are grouped by provider. Dated pricing updates preserve history, including cache-write price changes. Unpriced usage remains visible and partial calculations are labelled.

Explicit Auto records use the configured lowest-priced subscription model applicable on the record date and compare with DeepSeek V4 Flash. MiniMax M3 compares with V4 Pro; M2.7 compares with V4 Flash. Exact timestamps select the configured peak or off-peak rate; records without precise timestamps use off-peak pricing. Values are public API-price estimates, not subscription-provider invoices.

Opening the tray report uses the cached page without waiting for a scan. Daily background refresh is scheduled for 03:00 local time, with a 15-minute post-launch catch-up when no successful refresh has occurred that day. Manual refresh remains available. Single-instance ownership prevents duplicate app listeners; quitting cancels timers and closes the local listener. The Windows installer closes the running application before replacement.

Chinese and English switch immediately in Settings, the report, the guide and the tray menu without changing usage or subscription data. Added missing currency, exchange-rate, error and estimation translations. Fixed false-success settings responses, invalid request lengths, nonfinite and overlapping pricing records, and update checks that previously offered older releases.

Public artifacts exclude personal configuration, credentials, private service addresses, diagnostics, subscription records and usage reports. Historical usage screenshots are removed from the current source tree. Source and packaged-code privacy checks run before release; existing Git history is not rewritten by this release.

Download the installer or portable application to upgrade; in-app installer downloading is not implemented. macOS uses manual download and replacement because the project has no paid Apple Developer Program membership, Developer ID signing or Apple notarization. User data is kept separate from application files. Independent voice, realtime-audio and dictation usage is not included.
