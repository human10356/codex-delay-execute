# Delay Execute Marketplace

Beta marketplace for the Linux-only Delay Execute plugin for Codex CLI.

The source tree contains the `0.1.0-beta.2` release candidate.

## Installation

Using HTTPS:

```bash
codex plugin marketplace add https://github.com/human10356/delay-execute-marketplace.git --ref main
codex plugin add delay-execute@delay-execute-marketplace
```

Using SSH, including for a private fork when local Git credentials permit access:

```bash
codex plugin marketplace add git@github.com:human10356/delay-execute-marketplace.git --ref main
codex plugin add delay-execute@delay-execute-marketplace
```

Start a new Codex CLI thread after installation. Review and trust the bundled hook with `/hooks` before using Delay Execute for the first time.

## Update

```bash
codex plugin marketplace upgrade delay-execute-marketplace
codex plugin add delay-execute@delay-execute-marketplace
```

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
