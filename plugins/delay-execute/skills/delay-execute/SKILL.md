---
name: delay-execute
description: "Schedule a confirmed one-time, daily, or weekly prompt that resumes the current Codex CLI session on Linux. Use when the user invokes $delay-execute, asks to continue this exact chat later, or asks to create, list, or cancel a delayed Codex session task."
---

# Delay Execute

Use this skill only for local Linux Codex CLI sessions. It stages a task first and installs a user-level systemd timer only after explicit confirmation. When launched from tmux, a due task waits for the captured Codex pane to become idle, then submits the prompt through that pane. If the pane is gone, it falls back to a detached `codex exec resume`. Runtime states are recorded in Codex's writable plugin-data directory.

## Invocation

The preferred explicit syntax is:

`$delay-execute 在凌晨 02:15 继续第五阶段的设计、开发和测试验证。`

`/delay-execute ...` is also recognized as a prompt alias for compatibility with existing slash-command habits.

The active-session hook supplies a JSON object containing exact `session_id`, `cwd`, `helper_path`, and `state_dir` values in developer context. Use those exact values. Never infer the session ID or installation path from a transcript, never hard-code a user home directory, and never use `--last`.

## Stage a new task

1. Extract an exact task prompt and one schedule form:

   - One time: `--at HH:MM`
   - Daily: `--daily-at HH:MM`
   - Weekly: `--weekly-at HH:MM --weekday mon|tue|wed|thu|fri|sat|sun`

   If the user gives no time, date, recurrence, or unambiguous relative delay, ask one concise question and do not stage anything. If a one-time time has already passed today, state that it resolves to tomorrow before staging.
2. Run this command exactly once, replacing arguments with shell-safe values from the hook context and exactly one schedule form:

   `python3 "<helper_path>" --state-dir "<state_dir>" --import-legacy-state stage --session-id <session_id> --cwd <cwd> --at <HH:MM> --prompt <prompt>`

3. Read the JSON response and show a confirmation preview. It must include task ID, schedule type, exact next local execution time including date and timezone, current working directory, exact prompt, execution mode, delivery mode, and delivery policy. State that no timer has been created yet. For `non_git`, explain that the confirmed runner will use `--skip-git-repo-check` for the captured working directory. For a tmux-attached task, explain that it waits up to one hour for the original pane to be idle instead of opening a second session writer. It does not retry automatically after a terminal failure.
4. Ask the user to reply exactly: `$delay-execute confirm <任务ID>`.

Do not install, enable, or modify a systemd timer during staging.

## Confirm a task

Only treat `$delay-execute confirm <任务ID>` as confirmation. Do not treat a bare “确认”, “好的”, or an unrelated message as authorization.

1. Reuse the exact `helper_path` and `state_dir` from the staged task's active-session hook context. Run `python3 "<helper_path>" --state-dir "<state_dir>" --import-legacy-state install --task-id <任务ID>`.
2. Report the schedule, exact next execution time, prompt, systemd timer name, runner-script path, log path, history path, and plugin-data directory returned by the helper. Do not substitute a source checkout path.
3. Explain that the computer must be running. `Persistent=true` causes a missed timer to run after the user systemd manager becomes available; after logout, the user may need `loginctl enable-linger <user>` if their system does not keep the user manager alive.
4. State that the task uses the current Codex CLI authentication and permissions. It does not bypass quota, authentication, hook trust, or approval policies.

## List and cancel

- `$delay-execute list`: use the current hook's exact paths to run `python3 "<helper_path>" --state-dir "<state_dir>" --import-legacy-state list` and render each task's timer state, next run, schedule, and prompt succinctly.
- `$delay-execute cancel <任务ID>`: first show the task being targeted and request the exact confirmation `$delay-execute confirm-cancel <任务ID>`. Only then use the current hook's exact paths to run `python3 "<helper_path>" --state-dir "<state_dir>" --import-legacy-state cancel --task-id <任务ID>`.

## Safety rules

- Do not accept a past time silently: the helper schedules it for the next local day; disclose the resolved time before confirmation.
- Do not use `--dangerously-bypass-approvals`, `--full-auto`, or any permission-broadening option.
- Do not schedule a task in a directory that no longer exists. A confirmed runner may add `--skip-git-repo-check` when the captured working directory is not a Git repository; this only bypasses Codex's repository preflight and does not bypass authentication, hook trust, approval, or sandbox policies.
- If the task needs network, repository credentials, or interactive approval, explain that unattended execution can fail and allow the user to revise it.
- If the hook context does not contain `helper_path` and `state_dir`, stop and ask the user to review or trust the plugin hook with `/hooks`, then retry in a new thread. Do not guess a cache path.
