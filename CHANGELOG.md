# Changelog

## 0.1.0-beta.2 (unreleased)

- Add CI, release validation, evaluation cases, privacy documentation, and a public-release checklist.
- Keep explicit `--state-dir` runs isolated instead of importing legacy user data.

## 0.1.0-beta.1

- Add confirmed one-time, daily, and weekly delayed prompts.
- Resume the captured Codex CLI conversation from Git and non-Git directories.
- Prefer delivery through the original tmux pane to avoid concurrent session writers.
- Fall back to detached resume only when the captured pane no longer exists.
- Store writable task state under the active Codex home and avoid fixed user paths.
- Prevent automatic restart loops after terminal failures.
