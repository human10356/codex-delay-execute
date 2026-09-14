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
- [x] Idle-pane delivery, busy-pane waiting, pane-loss fallback, and real writer-lock handling pass against Codex CLI 0.154.0.
- [x] Session-attached delivery rejects a shell with Codex-like screen text and a reused or replaced Codex process identity.
- [x] Cancelling an active runner is reported as a successful SIGTERM service exit and leaves no failed user unit.
- [x] Private Git upgrade from `0.1.0-beta.1` to the `0.1.0-beta.2` candidate preserves plugin data; uninstall removes the cache and retains documented data.
- [x] Real systemd next-run timestamps match plugin calculations for one-time, daily, and weekly schedules.
- [x] Next-run previews preserve the named system timezone across daylight-saving changes and skip nonexistent wall times.
- [x] A stopped persistent timer catches up immediately when reactivated after its deadline.
- [x] A cache-busted candidate installs from the local Marketplace into an isolated Codex home; the installed copy passes manifest, skill, and all 25 automated tests.
- [x] The full Git history and staged release candidate are free of credential patterns and machine-specific paths.

## Required before making the repository public

- [ ] Verify behavior after logout or reboot, with and without user lingering.
- [ ] Change repository visibility to public.
- [ ] Install from a clean Linux account without GitHub credentials.
- [ ] Update private-beta wording and publish final release notes.
