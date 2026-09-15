# Changelog

## 0.1.0-beta.3 (unreleased)

- Prevent a root Agent Plugins manifest from shadowing the canonical Codex manifest and disabling bundled hook discovery in Codex CLI 0.154.0.
- Persist an at-most-once claim before a one-time task invokes Codex.
- Attempt to disable a one-time timer as soon as its only attempt is claimed, preserving the real systemd exit code on failure.
- Suppress repeated service activation without invoking Codex while leaving daily and weekly schedules recurring.
- Add runner and real user-systemd regression coverage for duplicate activation.

## 0.1.0-beta.2 (superseded before release)

- Add CI, release validation, evaluation cases, privacy documentation, and a public-release checklist.
- Keep explicit `--state-dir` runs isolated instead of importing legacy user data.
- Exercise the generated runner against real tmux, `flock`, and `timeout` processes in CI.
- Wait briefly between pasting a prompt and sending Enter so Codex CLI 0.154.0 submits it reliably.
- Treat the expected SIGTERM from cancelling an active task as a successful systemd service exit.
- Enforce user-only permissions on runner-created logs, history, and imported legacy state.
- Update repository metadata and installation URLs for the `codex-delay-execute` repository name.
- Bind attached delivery to the original pane and native Codex process identities, then use the official `codex queue` command instead of terminal keystroke injection.
- Calculate next-run previews with an IANA system timezone across daylight-saving transitions.
- Clarify the three schedule forms supported by the beta release.
- Require tasks created by earlier beta builds to be cancelled and recreated so they use the hardened runner snapshot.

## 0.1.0-beta.1

- Add confirmed one-time, daily, and weekly delayed prompts.
- Resume the captured Codex CLI conversation from Git and non-Git directories.
- Prefer delivery through the original tmux pane to avoid concurrent session writers.
- Fall back to detached resume only when the captured pane no longer exists.
- Store writable task state under the active Codex home and avoid fixed user paths.
- Prevent automatic restart loops after terminal failures.
