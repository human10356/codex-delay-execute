# Codex Delay Execute

Beta marketplace for the Linux-only Delay Execute plugin for Codex CLI.

The published beta release is `v0.1.0-beta.3`. This plugin supports Linux only.

## What it is for

Delay Execute is useful when the next step belongs to the current Codex conversation but should happen later: a morning status summary, a follow-up review after a build, or a recurring check-in. It preserves the captured conversation, working directory, and prompt, then delivers once at the scheduled time.

It is not a general-purpose host scheduler. It does not wake a powered-off computer or a stopped WSL virtual machine, and it does not migrate a task between WSL distributions, Linux installations, or user accounts. A task belongs to the Codex session and Linux user that created it.

## Installation

Using HTTPS:

```bash
codex plugin marketplace add https://github.com/human10356/codex-delay-execute.git --ref v0.1.0-beta.3
codex plugin add delay-execute@delay-execute-marketplace
```

Using SSH, including for a private fork when local Git credentials permit access:

```bash
codex plugin marketplace add git@github.com:human10356/codex-delay-execute.git --ref v0.1.0-beta.3
codex plugin add delay-execute@delay-execute-marketplace
```

Start a new Codex CLI thread after installation. Review and trust the bundled hook with `/hooks` before using Delay Execute for the first time.

## Uninstall safely

First list and cancel every task, including recurring tasks:

```text
$delay-execute list
$delay-execute cancel <task-id>
$delay-execute confirm-cancel <task-id>
```

Wait for cancellation to complete, then remove the plugin and (optionally) its Marketplace source:

```bash
codex plugin remove delay-execute@delay-execute-marketplace
codex plugin marketplace remove delay-execute-marketplace
```

Uninstalling only removes the plugin cache. Confirmed tasks create independent user-level systemd units and runner snapshots, so uninstalling or removing the Marketplace source does not stop them. If the plugin is already unavailable, stop only the units listed by the task record (under `~/.config/systemd/user/`) with `systemctl --user disable --now <unit>.timer <unit>.service`, then remove the corresponding runner after verifying no task is running. Do not delete units by a broad wildcard.

## Update

```bash
codex plugin marketplace upgrade delay-execute-marketplace
codex plugin add delay-execute@delay-execute-marketplace
```

The installation above pins `v0.1.0-beta.3`; select a newer release ref before upgrading when one becomes available. After an update that changes delivery behavior, cancel and recreate existing tasks. Each confirmed task has its own runner snapshot, so upgrading the plugin does not rewrite an already scheduled runner.

## Contents

- `.agents/plugins/marketplace.json`: marketplace catalog
- `plugins/delay-execute/`: installable plugin package

See the [plugin README](plugins/delay-execute/README.md) for requirements, usage, delivery behavior, and security details.

## Release readiness

- [Automated and manual testing](docs/TESTING.md)
- [Evaluation cases](docs/EVALS.md)
- [Release checklist](RELEASE_CHECKLIST.md)
- [Privacy](PRIVACY.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)
