# Release checklist

## Completed for the 0.1.0-beta.2 candidate

- [x] Portable root `plugin.json` and Codex compatibility manifest agree.
- [x] Marketplace catalog points to `./plugins/delay-execute`.
- [x] Hook resolves its helper through `PLUGIN_ROOT`.
- [x] Git and non-Git directories have automated coverage.
- [x] Detached services do not automatically restart after terminal failures.
- [x] Unit tests, Python compilation, release validation, and secret scanning pass.
- [x] The tagged `0.1.0-beta.1` private Git marketplace installs into the Codex plugin cache.
- [x] The locally installed `0.1.0-beta.2` candidate matches its source and passes the plugin validator and unit tests.
- [x] Requirements, security behavior, privacy behavior, and limitations are documented.
- [x] Explicit test state directories do not import real legacy user state.
- [x] Real user-level systemd accepts future one-time, daily, and weekly timers from a non-Git directory.
- [x] Cancelling those smoke-test tasks removes their active timer and service units.
- [x] The full Git history and staged release candidate are free of credential patterns and machine-specific paths.

## Required before making the repository public

- [ ] Complete the manual Linux E2E matrix in `docs/TESTING.md`.
- [ ] Verify session-attached delivery in an idle tmux pane.
- [ ] Verify a busy pane never starts a second writer.
- [ ] Verify pane disappearance produces one detached attempt without a restart loop.
- [ ] Verify behavior after logout or reboot, with and without user lingering.
- [ ] Change repository visibility to public.
- [ ] Install from a clean Linux account without GitHub credentials.
- [ ] Update private-beta wording and publish final release notes.
