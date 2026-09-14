# Delay Execute

> Beta 候选版本：`0.1.0-beta.2`。需要支持用户级 systemd 的 Linux。

Delay Execute 是一个面向 Linux Codex CLI 的延时任务插件。它可以在用户明确确认后，于指定时间把提示词提交到当前对话。

如果创建任务时所在的 tmux 窗格及 Codex 进程仍然存在，插件会通过官方 `codex queue` 向原会话排队提示词，不启动第二个会话写入器。如果原窗格已经关闭，才会降级执行 `codex exec resume`。

## 环境要求

- Linux 和用户级 systemd
- 已加入 `PATH` 的 Codex CLI；原会话投递需要提供 `codex queue` 的版本
- Python 3.10 或更高版本
- `flock` 和 GNU `timeout`
- 原会话投递需要 tmux、`ps` 和 Linux procfs；仅使用 detached 降级模式时不要求它们

任务到期时，电脑和用户级 systemd 管理器必须处于运行状态。如果注销后用户服务会停止，可能需要执行 `loginctl enable-linger <user>`。

WSL2 不是持续运行的 Linux 主机。插件只能在 WSL2 发行版及其 systemd 已运行时工作；用户 lingering 无法启动已停止的 WSL 虚拟机，也无法唤醒 Windows。Windows 重启或执行 `wsl --shutdown` 后，需要先启动该发行版，`Persistent` timer 才能在用户管理器可用后补执行。

## 安装位置与可移植性

通过 Codex 插件管理器和已配置的 marketplace 安装：

```bash
codex plugin add delay-execute@<marketplace-name>
```

Codex 会把插件安装到当前 Codex home（默认是 `~/.codex`）管理的插件缓存中。hook 使用 Codex 提供的 `PLUGIN_ROOT` 动态定位已安装脚本，任务数据使用 `PLUGIN_DATA`。如果该变量不可用，才会回退到 `$CODEX_HOME/plugin-data/delay-execute`；默认 Codex home 下对应 `~/.codex/plugin-data/delay-execute`。

插件不包含用户名、源码目录或固定缓存版本路径。只有用户级 systemd unit 按系统规范写入 `~/.config/systemd/user/`。

从旧版升级后，第一次执行插件命令时会把 `~/.local/state/codex-delay-execute` 中的任务元数据、待确认记录、日志和历史记录一次性导入新数据目录。旧 runner 可能包含过期安装路径，因此不会复制。直接调用 helper 或使用隔离测试目录时，除非显式请求，否则不会导入旧数据。

安装或升级后，请新建 Codex 对话以加载新版 skill 和 hook。首次使用前需要通过 `/hooks` 审查并信任 Delay Execute hook；安装插件本身不会自动信任 hook。

每个已确认任务都会保留一份生成时的 runner 快照。涉及投递行为的插件升级不会重写现有 runner，因此升级后需要取消并重新创建旧任务。

## 使用方式

创建一次性任务：

```text
$delay-execute 在 23:15 继续分析当前问题
```

插件会先展示实际执行日期、时区、提示词、工作目录、Git 模式和投递策略。只有回复下面的精确确认命令后才会创建 timer：

```text
$delay-execute confirm <任务ID>
```

也支持每日和每周任务：

```text
$delay-execute 每天 09:00 汇总昨天的工作并继续
$delay-execute 每周一 09:00 继续检查项目风险
```

当前 Beta 只接受下一次本机 `HH:MM`、每日 `HH:MM`，或每周某日加 `HH:MM`。暂不支持显式日历日期和相对时长。

任务管理：

```text
$delay-execute list
$delay-execute cancel <任务ID>
$delay-execute confirm-cancel <任务ID>
```

取消操作也会停止正在等待的服务，并且必须经过明确确认。

## 执行规则

- 原 tmux 窗格存在：记录并验证窗格、终端和原生 Codex 进程标识；身份匹配后使用官方 `codex queue`，无论会话空闲或工作中都由 Codex 自己排队，runner 不发送终端按键。
- 原窗格不存在或进程身份已变化：降级为 detached `codex exec resume`，不会把提示词发送给 shell 或替换后的 Codex 会话。
- `codex queue` 失败：记录失败并进行一次 detached 降级尝试。
- 非 Git 目录：增加 `--skip-git-repo-check`，但不会绕过认证、hook 信任、sandbox、配额或审批策略。
- detached 模式遇到会话 writer 冲突：记录为 `blocked_by_active_session`，不无限重启。
- 终态失败：记录失败，不自动重试。

如果 `codex` 指向 Codex HUD shim，生成的 runner 会自动通过 `--no-hud --` 调用原生 CLI，使无 TTY 的 systemd 服务也能使用 queue。

新任务的运行状态包括 `queued`、`queued_to_session`、`detached_running`、`completed`、`blocked_by_active_session` 和 `failed`；`queued_to_session` 表示 Codex 已接受消息，不代表忙碌中的上一轮和排队消息都已处理完成。旧任务记录仍可能包含 `waiting_for_idle` 或 `injected`。使用 `$delay-execute list` 查看；任务记录会包含实际 runner、日志、历史记录和数据目录。

## 已知边界

原会话投递依赖提供 `codex queue` 的 Codex CLI 版本；如果 queue 不可用或失败，会记录日志并尝试一次 detached 恢复。

如果 WSL 已停止，必须先启动 WSL 发行版；本插件和 systemd 用户 lingering 都无法唤醒已停止的 WSL 虚拟机。

卸载插件前应取消所有已计划任务。卸载只移除插件缓存，不会自动停止用户级 systemd timer，也不会删除保留的插件数据。

WSL2 仅提供尽力支持，并受上述虚拟机生命周期限制。目前不支持原生 Windows、macOS launchd、无 systemd 的 Linux，以及只在 GUI 环境中运行的计划任务。

## 安全模型

- 创建和取消 timer 都要求精确确认。
- 不使用 `--full-auto`，不绕过审批，也不扩大权限。
- 提示词、session ID 和 runner 使用仅当前用户可读写的权限保存。
- hook 只调用 `PLUGIN_ROOT` 下随插件安装的 `capture_context.py`。

## 开发验证

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/delay_execute.py scripts/capture_context.py
```

## 许可证

MIT，详见 [LICENSE](LICENSE)。
