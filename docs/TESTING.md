# Testing

## Automated checks

Run from the marketplace repository root:

```bash
python3 scripts/validate_release.py
python3 -m py_compile plugins/delay-execute/scripts/*.py
python3 -m unittest discover -s plugins/delay-execute/tests -v
```

CI runs the same checks on Linux with Python 3.10, 3.12, and 3.14.

The test suite includes runner integration tests backed by real tmux, `flock`, and GNU `timeout` processes. A controlled fake `codex` executable covers both the queue and detached-resume command boundaries, so CI never writes to a real conversation.

## Completed Linux verification

On 2026-09-14, the release candidate was tested on Linux with Codex CLI 0.154.0, Python 3.12, systemd 255, and tmux 3.4.

- Future one-time, daily, and weekly tasks were staged and installed from a non-Git `/tmp` directory with isolated state. Each real user timer became active, declared `Persistent=true`, and used a service without `Restart=`. The plugin and systemd calculated the same next run, to the second.
- A disposable real Codex session accepted and executed messages through `codex queue` while its TUI was idle. The installed HUD shim forwarded the same command successfully. Queueing while the TUI was closed persisted the message, which executed when the session was resumed.
- A generated production runner executed under a real transient `systemd --user` service, automatically bypassed the TTY-dependent Codex HUD wrapper, queued the message, and recorded `queued_to_session` without detached execution.
- Both idle and busy attached panes use the official session queue without starting a detached writer or sending terminal keystrokes.
- Destroying the captured pane produced exactly one successful `codex exec resume`. A real writer conflict became the terminal `blocked_by_active_session` state without a retry.
- A shell displaying a Codex-like idle prompt was rejected because its pane and native Codex process identities did not match.
- Cancelling both queued and actively waiting tasks removed their units and processes. Expected SIGTERM cancellation left no failed unit and did not degrade the user manager.
- A `Persistent=true` timer was stopped before its deadline and restarted after the deadline. Its generated runner executed immediately and both timer and service reported success.
- Next-run calculation was verified across both a daylight-saving offset change and a nonexistent spring-forward wall time.
- A private `v0.1.0-beta.1` installation was upgraded to the `0.1.0-beta.2` candidate. Plugin data survived both upgrade and uninstall, while the installed plugin cache was removed on uninstall.

The machine had user lingering enabled. Unit syntax, `Persistent=true`, and the active user manager were verified, but a physical logout/reboot was deliberately not performed because it would interrupt the testing session. That final operational scenario remains distinct from automated coverage.

## Git installation

Install the tagged marketplace and plugin. A private source requires matching Git credentials; a public source does not:

```bash
codex plugin marketplace add <private-git-url> --ref <release-tag>
codex plugin add delay-execute@delay-execute-marketplace
```

Start a new Codex CLI thread, open `/hooks`, review the hook command, and trust it before running the manual scenarios.

## Anonymous public-install gate

Run this only after the repository is public and `v0.1.0-beta.2` exists. Use an empty temporary Codex home and the HTTPS URL so the test cannot silently rely on the maintainer's SSH key or existing marketplace cache:

```bash
clean_codex_home="$(mktemp -d)"
env CODEX_HOME="$clean_codex_home" \
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
  codex plugin marketplace add \
  https://github.com/human10356/codex-delay-execute.git \
  --ref v0.1.0-beta.2
env CODEX_HOME="$clean_codex_home" \
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
  codex plugin add \
  delay-execute@delay-execute-marketplace
env CODEX_HOME="$clean_codex_home" codex plugin list
```

Clone the same tag with Git credential helpers disabled, then validate the complete Marketplace repository:

```bash
anonymous_checkout="$(mktemp -d)"
env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/false SSH_ASKPASS=/bin/false \
  git clone --branch v0.1.0-beta.2 --depth 1 \
  https://github.com/human10356/codex-delay-execute.git \
  "$anonymous_checkout"
python3 "$anonymous_checkout/scripts/validate_release.py"
python3 -m unittest discover \
  -s "$anonymous_checkout/plugins/delay-execute/tests" -v
```

Locate the installed plugin under `$clean_codex_home/plugins/cache`, then run the plugin validator, skill validator, Python compilation, and all 29 tests against that cache copy. The anonymous checkout and clean Codex home must not contain GitHub credentials. Remove both temporary directories after recording redacted results.

An anonymous clone or install before the visibility change must fail. A successful private SSH install does not satisfy this gate.

## Linux E2E matrix

Use disposable prompts and inspect `$delay-execute list`, task history, logs, and relevant user units after each scenario.

- [x] Stage a one-time task and verify no systemd unit exists before exact confirmation.
- [x] Confirm the task and verify its timer, service, runner, next-run timestamp, and plugin-data paths.
- [x] Repeat staging and execution from a non-Git directory.
- [x] Schedule daily and weekly tasks and verify their next-run calculations.
- [x] In tmux, let the pane become idle and verify `codex queue` delivers the prompt without terminal input.
- [x] Keep the pane busy and verify the prompt is queued without starting a detached Codex writer.
- [x] Execute a generated runner through `systemd --user` and verify Codex HUD is bypassed for non-TTY queue delivery.
- [x] Destroy the captured pane and verify exactly one detached resume attempt occurs.
- [x] Replace the captured Codex process with a shell and verify attached queue delivery is rejected without terminal input.
- [x] Hold the conversation writer lock and verify the terminal state becomes `blocked_by_active_session` without automatic restart.
- [x] Cancel queued and active tasks and verify their timer, service, and runner are stopped.
- [x] Stop a persistent timer across its deadline and verify it runs immediately after reactivation.
- [ ] Test a missed timer after a physical logout or reboot makes the user systemd manager available again.
- [x] Test migration from the legacy state directory with non-sensitive fixture data.
- [x] Uninstall the plugin and verify the documented data-retention behavior.

Record the operating system, Codex CLI version, Python version, systemd version, tmux version, scenario result, and relevant redacted logs.

When a helper command uses an explicit `--state-dir`, that directory remains isolated and does not import data from the legacy user-state location.
