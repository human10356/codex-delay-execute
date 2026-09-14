# Privacy

Delay Execute runs locally in Codex CLI. It does not operate a remote service, send telemetry, create an external account, or intentionally transmit stored task data to the plugin publisher.

## Data stored locally

The plugin stores the following information so a confirmed task can resume the correct conversation:

- delayed prompt text
- Codex session identifier
- captured working directory
- schedule and delivery metadata
- local execution logs and task history
- tmux socket, pane, terminal, and local process identifiers when session-attached delivery is available

Data is stored under `PLUGIN_DATA` when provided by the plugin host. Otherwise it uses `$CODEX_HOME/plugin-data/delay-execute`, falling back to `~/.codex/plugin-data/delay-execute` for the default Codex home. User-level systemd units are created under `~/.config/systemd/user/` only after explicit confirmation.

## Data use and retention

Stored information is used only to schedule, deliver, list, cancel, and diagnose delayed tasks. History and logs remain on the local machine until the user removes them. A task that invokes Codex can use network access according to the user's existing Codex configuration and the task's approvals; the plugin does not broaden those permissions.

Do not place passwords, tokens, private keys, or other secrets in delayed prompts.

## Removing data

Cancel active tasks through `$delay-execute cancel <task-id>` followed by the exact confirmation command. After all tasks are disabled, uninstall the plugin and remove its plugin-data directory if the retained local history is no longer needed.
