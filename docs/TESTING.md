# Testing

## Automated checks

Run from the marketplace repository root:

```bash
python3 scripts/validate_release.py
python3 -m py_compile plugins/delay-execute/scripts/*.py
python3 -m unittest discover -s plugins/delay-execute/tests -v
```

CI runs the same checks on Linux with Python 3.10, 3.12, and 3.14.

## Completed infrastructure smoke test

On 2026-09-14, future one-time, daily, and weekly tasks were staged and installed from the non-Git `/tmp` directory with an isolated state directory. Each real user-level systemd timer became active, declared `Persistent=true`, and used a service without a `Restart=` directive. All three tasks were cancelled before their due times, and their timer and service unit files were removed. No Codex resume command ran during this test.

This smoke test covers helper-to-systemd integration. It does not replace the session-delivery scenarios below.

## Private Git installation

The testing machine must already be able to clone the private repository. Install the tagged marketplace and plugin:

```bash
codex plugin marketplace add <private-git-url> --ref <release-tag>
codex plugin add delay-execute@delay-execute-marketplace
```

Start a new Codex CLI thread, open `/hooks`, review the hook command, and trust it before running the manual scenarios.

## Manual Linux E2E matrix

Use disposable prompts and inspect `$delay-execute list`, task history, logs, and relevant user units after each scenario.

- [ ] Stage a one-time task and verify no systemd unit exists before exact confirmation.
- [ ] Confirm the task and verify its timer, service, runner, next-run timestamp, and plugin-data paths.
- [ ] Repeat staging and execution from a non-Git directory.
- [ ] Schedule daily and weekly tasks and verify their next-run calculations.
- [ ] In tmux, let the pane become idle and verify the prompt is injected into that pane.
- [ ] Keep the pane busy and verify no detached Codex writer starts.
- [ ] Destroy the captured pane and verify exactly one detached resume attempt occurs.
- [ ] Hold the conversation writer lock and verify the terminal state becomes `blocked_by_active_session` without automatic restart.
- [ ] Cancel a queued task and verify its timer and service are disabled.
- [ ] Test a missed timer after the user systemd manager becomes available again.
- [ ] Test migration from the legacy state directory with non-sensitive fixture data.
- [ ] Uninstall the plugin and verify the documented data-retention behavior.

Record the operating system, Codex CLI version, Python version, systemd version, tmux version, scenario result, and relevant redacted logs.

When a helper command uses an explicit `--state-dir`, that directory remains isolated and does not import data from the legacy user-state location.
