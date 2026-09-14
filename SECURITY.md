# Security

Delay Execute creates user-level systemd timers and later submits a stored prompt to an existing Codex CLI conversation. Review the bundled hook and scripts before trusting or installing the plugin.

The plugin does not broaden Codex permissions, bypass approvals, or embed credentials. Prompts, session identifiers, runner scripts, and execution history are stored locally with user-only permissions in the Codex plugin-data directory. Session-attached delivery verifies the original tmux pane and native Codex process, then uses the official `codex queue` command. It never injects terminal keystrokes. If the original process is unavailable or queueing fails, it makes one detached resume attempt.

Do not include secrets in delayed prompts. Unattended tasks can fail when network access, repository credentials, authentication, quotas, or interactive approval are required.

Report security issues through a private repository security advisory at `https://github.com/human10356/codex-delay-execute/security/advisories/new`. Do not open a public issue containing credentials, prompt contents, session identifiers, filesystem paths, or unredacted logs.
