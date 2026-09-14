# Evaluation cases

These cases are written so another tester can evaluate the plugin without internal implementation context. All tests use a Linux Codex CLI session with the hook reviewed and trusted.

## Positive cases

### 1. Confirmed one-time task

- User prompt: `$delay-execute 在 23:15 继续分析当前问题`
- Setup: The requested time is still in the future today.
- Expected workflow: Stage the task, show the resolved local date and timezone, and require the exact confirmation command.
- Expected result: No timer exists before confirmation; confirmation creates one timer and reports its paths and next run.

### 2. Passed time resolves to tomorrow

- User prompt: `$delay-execute 在 00:05 继续整理文档`
- Setup: Local time is later than 00:05.
- Expected workflow: Resolve the execution date to tomorrow and disclose that date before requesting confirmation.
- Expected result: The confirmed timer uses tomorrow's date rather than running immediately.

### 3. Non-Git working directory

- User prompt: `$delay-execute 在 22:00 继续处理这个目录的任务`
- Setup: Start Codex CLI in an existing directory that is not a Git work tree.
- Expected workflow: Identify `non_git` mode and explain the repository preflight exception before confirmation.
- Expected result: The runner uses `--skip-git-repo-check` without changing authentication, sandbox, or approval settings.

### 4. List scheduled tasks

- User prompt: `$delay-execute list`
- Setup: At least one confirmed task exists.
- Expected workflow: Read the current plugin-data task records.
- Expected result: Return each task's identifier, schedule, next run, runtime state, and prompt without modifying timers.

### 5. Confirmed cancellation

- User prompt: `$delay-execute cancel <task-id>`
- Setup: The referenced task exists.
- Expected workflow: Display the target and require `$delay-execute confirm-cancel <task-id>`.
- Expected result: No cancellation occurs before exact confirmation; confirmation disables the timer and service.

### 6. Session-attached delivery

- User prompt: A previously confirmed task becomes due.
- Setup: The original tmux pane still exists and reaches the standard idle Codex prompt.
- Expected workflow: Wait for idle, paste the stored prompt, and press Enter in the captured pane.
- Expected result: Runtime state becomes `injected`; no detached writer is launched.

## Negative cases

### 1. Missing schedule

- User prompt: `$delay-execute 稍后继续这个任务`
- Reason: No unambiguous time, date, recurrence, or relative delay is provided.
- Expected behavior: Ask one concise scheduling question and do not stage or install anything.

### 2. Non-exact confirmation

- User prompt: `好的，确认`
- Reason: The response is not `$delay-execute confirm <task-id>`.
- Expected behavior: Do not create a timer and repeat the exact confirmation syntax.

### 3. Missing trusted hook context

- User prompt: `$delay-execute 在 23:15 继续当前任务`
- Setup: The active context lacks `helper_path` or `state_dir`.
- Reason: Guessing an installation cache path or session identifier could target the wrong conversation.
- Expected behavior: Stop and ask the user to review or trust the hook with `/hooks`, then retry in a new thread.

### 4. Active conversation writer conflict

- User prompt: A detached task becomes due while another writer owns the conversation.
- Reason: Starting or repeatedly restarting another writer could lock the session.
- Expected behavior: Record `blocked_by_active_session`, stop without automatic restart, and preserve diagnostic logs.
