# Codex Delay Execute

Beta marketplace for the Linux-only Delay Execute plugin for Codex CLI.

The published beta release is `v0.1.0-beta.3`. This plugin supports Linux only.

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

Before uninstalling, cancel every scheduled task. Installed user-level systemd timers and copied runners are intentionally independent of the plugin cache and are not removed by uninstalling the plugin.

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
