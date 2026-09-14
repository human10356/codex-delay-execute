# Delay Execute

> Beta release candidate: `0.1.0-beta.2`. Linux with user-level systemd is required.

Delay Execute schedules a confirmed prompt for the current Codex CLI conversation on Linux. When the originating tmux pane is still available, the task waits for that pane to become idle and submits the prompt there. If the pane no longer exists, it falls back to `codex exec resume`.

The plugin is intended for users who want to continue the exact same CLI conversation later without keeping a second Codex writer alive.

## Requirements

- Linux with a user-level systemd manager
- Codex CLI available on `PATH`
- Python 3.10 or later
- `flock` and GNU `timeout`
- tmux for session-attached delivery; detached fallback does not require tmux

The computer and the user's systemd manager must be running when a task becomes due. On systems that stop the user manager after logout, `loginctl enable-linger <user>` may be needed.

## Installation and paths

Install the plugin through the Codex plugin manager and a configured marketplace:

```bash
codex plugin add delay-execute@<marketplace-name>
```

Codex installs the package under the active Codex home (normally `~/.codex`) and passes the installed package location to hooks as `PLUGIN_ROOT`. Writable task data uses `PLUGIN_DATA`; when that variable is unavailable, the helper falls back to `$CODEX_HOME/plugin-data/delay-execute`, or `~/.codex/plugin-data/delay-execute` with the default Codex home.

No username, source-checkout path, or fixed `~/.codex/plugins/cache/...` version path is embedded in the plugin. The only files intentionally created outside Codex data are user-level systemd units under `~/.config/systemd/user/`.

On the first plugin command after upgrading from an older local build, task metadata, pending confirmations, logs, and history are imported once from `~/.local/state/codex-delay-execute`. Generated legacy runners are not copied because they can contain obsolete installation paths. Direct helper invocations and isolated test directories do not import legacy data unless explicitly requested.

After installation or an update, start a new Codex thread so the current plugin skill and hook definition are loaded. Plugin hooks are not trusted automatically; review and trust the Delay Execute hook with `/hooks` before first use.

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

List or cancel tasks:

```text
$delay-execute list
$delay-execute cancel <task-id>
$delay-execute confirm-cancel <task-id>
```

Cancellation also stops a currently waiting service. Task installation and cancellation always require explicit confirmation.

## Delivery behavior

Session-attached delivery records the tmux server socket and pane ID at staging time. When due, it polls for up to one hour and submits the prompt only after the Codex pane appears idle. It never starts a second writer while that pane is available.

If the captured pane has disappeared, the task runs a detached `codex exec resume`. Non-Git directories use `--skip-git-repo-check`; this bypasses only the repository preflight and does not bypass authentication, hook trust, sandboxing, quotas, or approval policy.

Detached writer conflicts are recorded as `blocked_by_active_session`. Terminal failures are not automatically restarted, preventing an old task from indefinitely holding a conversation lock.

## Runtime states and troubleshooting

Task records use these runtime states: `queued`, `waiting_for_idle`, `injected`, `detached_running`, `completed`, `blocked_by_active_session`, and `failed`.

Use `$delay-execute list` for the current state. The installed task record contains exact runner, log, history, and state-directory paths.

Common issues:

- Missing active-session context: open `/hooks`, review and trust the plugin hook, then retry in a new thread.
- `blocked_by_active_session`: another Codex process owns the conversation and detached delivery was not attempted again.
- No run after logout: enable the user systemd manager to linger or keep the login session active.
- Prompt never injected into an existing pane: the current idle detector targets the standard English Codex CLI prompt. A changed or localized UI can time out safely instead of injecting into an uncertain terminal state.

## Security model

- Every timer requires an exact confirmation.
- The plugin does not add `--full-auto`, bypass approvals, or expand permissions.
- Prompts and session identifiers are stored with user-only file permissions in the plugin data directory.
- Generated runner scripts are user-only and use a non-blocking lock.
- Review the hook command before trusting it. It invokes only the copy of `capture_context.py` under `PLUGIN_ROOT`.

## Scope

This is a Linux-first Codex CLI plugin. Native Windows, macOS launchd, non-systemd Linux, and GUI-only scheduling are not currently supported.

## Development

Run the test suite and validators from the plugin source tree:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/delay_execute.py scripts/capture_context.py
```

The source plugin is validated with Codex's plugin validator before release.

## License

MIT. See [LICENSE](LICENSE).
