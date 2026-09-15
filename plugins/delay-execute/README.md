# Delay Execute

> Beta release candidate: `0.1.0-beta.3`. Linux with user-level systemd is required.

Delay Execute schedules a confirmed prompt for the current Codex CLI conversation on Linux. When the originating tmux pane and Codex process are still available, the task submits the prompt through the official `codex queue` command. If they are no longer available, it falls back to `codex exec resume`.

The plugin is intended for users who want to continue the exact same CLI conversation later without keeping a second Codex writer alive.

Typical uses include a next-morning project summary, a post-build review, a reminder to re-check a failing test, and daily or weekly maintenance prompts. It is deliberately scoped to the conversation that created the task; it is not a replacement for a system-wide job scheduler.

## Requirements

- Linux with a user-level systemd manager
- Codex CLI available on `PATH`; attached delivery requires a version that provides `codex queue`
- Python 3.10 or later
- `flock` and GNU `timeout`
- tmux, `ps`, and Linux procfs for session-attached delivery; detached fallback does not require them

The computer and the user's systemd manager must be running when a task becomes due. On systems that stop the user manager after logout, `loginctl enable-linger <user>` may be needed.

WSL2 is not an always-running Linux host. The plugin can run inside a WSL2 distribution only while that distribution and its systemd instance are running. User lingering cannot start a stopped WSL virtual machine or wake Windows. After a Windows reboot or `wsl --shutdown`, start the distribution again; persistent timers can catch up only after its user manager becomes available.

WSL lifecycle and portability:

- A task can catch up after the *same* WSL distribution is started again, provided its Linux filesystem, Codex home, and user systemd state are intact.
- A task does not run while the distribution is stopped, and it is not transferred automatically to another distribution (for example, Ubuntu-24.04 versus a second Ubuntu instance), Windows, macOS, or another Linux user.
- To use the task in another environment, install the plugin there and create a new task from the conversation available in that environment. The original task remains owned by its source environment.

## Installation and paths

Install the plugin through the Codex plugin manager and a configured marketplace:

```bash
codex plugin add delay-execute@<marketplace-name>
```

Codex installs the package under the active Codex home (normally `~/.codex`) and passes the installed package location to hooks as `PLUGIN_ROOT`. Writable task data uses `PLUGIN_DATA`; when that variable is unavailable, the helper falls back to `$CODEX_HOME/plugin-data/delay-execute`, or `~/.codex/plugin-data/delay-execute` with the default Codex home.

No username, source-checkout path, or fixed `~/.codex/plugins/cache/...` version path is embedded in the plugin. The only files intentionally created outside Codex data are user-level systemd units under `~/.config/systemd/user/`.

On the first plugin command after upgrading from an older local build, task metadata, pending confirmations, logs, and history are imported once from `~/.local/state/codex-delay-execute`. Generated legacy runners are not copied because they can contain obsolete installation paths. Direct helper invocations and isolated test directories do not import legacy data unless explicitly requested.

After installation or an update, start a new Codex thread so the current plugin skill and hook definition are loaded. Plugin hooks are not trusted automatically; review and trust the Delay Execute hook with `/hooks` before first use.

Each confirmed task keeps a generated runner snapshot. After an update that changes delivery behavior, cancel and recreate existing tasks; upgrading the plugin does not rewrite already scheduled runners.

## Usage

Create a one-time task:

```text
$delay-execute 在 23:15 继续分析当前问题
```

The plugin first shows the resolved date, time zone, prompt, working directory, execution mode, and delivery policy. No timer is created until the exact confirmation is sent:

```text
$delay-execute confirm <task-id>
```

Recurring forms are also supported:

```text
$delay-execute 每天 09:00 汇总昨天的工作并继续
$delay-execute 每周一 09:00 继续检查项目风险
```

The beta accepts the next occurrence of a local `HH:MM`, a daily `HH:MM`, or a weekly weekday plus `HH:MM`. Explicit calendar dates and relative durations are not yet supported.

List or cancel tasks:

```text
$delay-execute list
$delay-execute cancel <task-id>
$delay-execute confirm-cancel <task-id>
```

Cancellation also stops a currently waiting service. Task installation and cancellation always require explicit confirmation.

## Uninstall and timer cleanup

Always cancel tasks before removing the plugin. For each task returned by `list`, run `cancel` and then the exact `confirm-cancel` command. This disables the timer, stops a waiting service, and removes the generated unit files.

After all tasks are cancelled, remove the plugin from Codex:

```bash
codex plugin remove delay-execute@<marketplace-name>
```

You may then remove the configured Marketplace source:

```bash
codex plugin marketplace remove <marketplace-name>
```

Plugin removal does not clean up already-created timers or retained task data. If the plugin can no longer be loaded, use the exact unit names and paths shown by the task record and stop them explicitly with `systemctl --user disable --now <name>.timer <name>.service`. Verify with `systemctl --user list-timers` and `ps`; avoid broad wildcard deletion.

## Delivery behavior

Session-attached delivery records the tmux server socket, pane, terminal, and native Codex process IDs at staging time. When due, it queues the prompt only when those identities still match. The official Codex queue accepts the message whether the session is idle or working, and the runner never sends terminal keystrokes.

If the captured pane has disappeared or its process identity has changed, the task runs a detached `codex exec resume`. Non-Git directories use `--skip-git-repo-check`; this bypasses only the repository preflight and does not bypass authentication, hook trust, sandboxing, quotas, or approval policy.

If queueing fails, the task makes one detached resume attempt. Detached writer conflicts are recorded as `blocked_by_active_session`. Terminal failures are not automatically restarted, preventing an old task from indefinitely holding a conversation lock.

A one-time task durably claims its only attempt before invoking Codex and immediately attempts to disable its timer. A disarm failure is recorded with the real systemd exit code, while the durable claim still suppresses later activation without invoking Codex. The no-retry policy favors duplicate prevention: a host failure after the claim but before delivery can leave the task undelivered.

When `codex` resolves to the Codex HUD shim, generated runners automatically use its `--no-hud --` pass-through so non-interactive systemd services invoke the native CLI without requiring a terminal.

## Runtime states and troubleshooting

New task records use these runtime states: `claimed`, `queued`, `queued_to_session`, `detached_running`, `completed`, `blocked_by_active_session`, and `failed`. `queued_to_session` means Codex accepted the attached message; it does not claim that a busy turn has already finished processing it. Legacy records can still contain `waiting_for_idle` or `injected`.

Use `$delay-execute list` for the current state. The installed task record contains exact runner, log, history, and state-directory paths.

Common issues:

- Missing active-session context: open `/hooks`, review and trust the plugin hook, then retry in a new thread.
- `blocked_by_active_session`: another Codex process owns the conversation and detached delivery was not attempted again.
- No run after logout: enable the user systemd manager to linger or keep the login session active.
- No run while WSL is stopped: start the WSL distribution. Neither this plugin nor systemd user lingering can wake a stopped WSL virtual machine.
- Prompt was not processed immediately: inspect the task log for a queue failure or detached writer conflict. Attached queue delivery requires a Codex CLI version that provides `codex queue`.

See [Uninstall and timer cleanup](#uninstall-and-timer-cleanup) before removing the plugin. Uninstalling removes its cache entry but intentionally does not stop user-level systemd timers or delete retained plugin data.

## Security model

- Every timer requires an exact confirmation.
- The plugin does not add `--full-auto`, bypass approvals, or expand permissions.
- Prompts and session identifiers are stored with user-only file permissions in the plugin data directory.
- Generated runner scripts are user-only and use a non-blocking lock.
- Review the hook command before trusting it. It invokes only the copy of `capture_context.py` under `PLUGIN_ROOT`.

## Scope

This is a Linux-first Codex CLI plugin. WSL2 is best-effort and subject to the virtual-machine lifecycle limitation above. Native Windows, macOS launchd, non-systemd Linux, and GUI-only scheduling are not currently supported.

## Development

Run the test suite and validators from the plugin source tree:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/delay_execute.py scripts/capture_context.py
```

The source plugin is validated with Codex's plugin validator before release.

## License

MIT. See [LICENSE](LICENSE).
