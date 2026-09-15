# Release checklist

## Completed for the 0.1.0-beta.3 candidate

- [x] The canonical `.codex-plugin/plugin.json` passes Codex validation, and no root `plugin.json` shadows it.
- [x] Marketplace catalog points to `./plugins/delay-execute`.
- [x] Hook resolves its helper through `PLUGIN_ROOT`.
- [x] Git and non-Git directories have automated coverage.
- [x] Detached services do not automatically restart after terminal failures.
- [x] Unit tests, Python compilation, release validation, and secret scanning pass.
- [x] The tagged `0.1.0-beta.1` private Git marketplace installs into the Codex plugin cache.
- [x] Install the local `0.1.0-beta.3` candidate and verify the installed cache matches its source.
- [x] Start a fresh Codex runtime and verify the installed beta.3 skill and bundled hook are loaded after removing the shadowing root manifest.
- [x] Requirements, security behavior, privacy behavior, and limitations are documented.
- [x] Explicit test state directories do not import real legacy user state.
- [x] Real user-level systemd accepts future one-time, daily, and weekly timers from a non-Git directory.
- [x] Cancelling those smoke-test tasks removes their active timer and service units.
- [x] Official session-queue delivery for both idle and busy panes, pane-loss fallback, and real writer-lock handling pass against Codex CLI 0.154.0.
- [x] Session-attached delivery rejects a shell with Codex-like screen text and a reused or replaced Codex process identity.
- [x] Attached delivery uses `codex queue` without terminal keystroke injection; a real disposable session accepted and executed queued prompts.
- [x] A generated runner delivers through `codex queue` from a real `systemd --user` service and automatically bypasses the TTY-dependent Codex HUD shim.
- [x] Cancelling an active runner is reported as a successful SIGTERM service exit and leaves no failed user unit.
- [x] Private Git upgrade from `0.1.0-beta.1` to the `0.1.0-beta.2` candidate preserves plugin data; uninstall removes the cache and retains documented data.
- [x] Real systemd next-run timestamps match plugin calculations for one-time, daily, and weekly schedules.
- [x] Next-run previews preserve the named system timezone across daylight-saving changes and skip nonexistent wall times.
- [x] A stopped persistent timer catches up immediately when reactivated after its deadline.
- [x] Install the final cache-busted `0.1.0-beta.3` candidate into an isolated Codex home; run manifest, skill, and all 34 automated tests against that cache copy.
- [x] The full Git history and staged release candidate are free of credential patterns and machine-specific paths.
- [x] An isolated Ubuntu 24.04 systemd lifecycle test delivered each task exactly once after a stopped non-lingering user manager was started again and after a lingering user manager restarted automatically following a full container userspace restart.
- [x] A real user-systemd regression test disabled a claimed one-time timer and suppressed a forced second service activation without a second Codex invocation; recurring runner coverage still permits later daily and weekly invocations.
- [x] A WSL distribution userspace restart was distinguished from a full WSL2 VM restart by PID 1 start time, kernel boot ID, journal boot ID, and Windows boot time; it was not counted as lifecycle-gate evidence.
- [x] A host-issued `wsl --shutdown` changed the WSL kernel boot ID and created a new journal boot; no beta.3 task was pending, so this proves the VM lifecycle step but not persistent-timer catch-up.
- [x] A confirmed one-time task missed its 13:05 deadline while WSL was shut down: the prior boot ended at 12:49:58, the next boot started at 13:06:34, and its persistent timer activated the service at 13:06:35. It completed once at 13:08:10 with `attempt_count=1`, service `Result=success`, `NRestarts=0`, a disabled timer, and a released task lock. The only remaining thread writer lock belongs to the manually resumed foreground Codex session.

## Remaining release gates, in order

### Before changing repository visibility

- [ ] Verify the latest commit passes every GitHub Actions matrix job.
- [x] Stop the full WSL virtual machine (or reboot Windows), allow a timer deadline to pass, start the distribution again, and verify exactly one catch-up delivery before treating the isolated systemd result as release-complete evidence.
- [ ] Update release wording, replace the changelog's `unreleased` marker with the release date, and commit the result.
- [ ] Create and push the annotated `v0.1.0-beta.3` tag from the reviewed commit.

### Publication boundary

- [ ] Change repository visibility to public. This is the final publication state change; do it only after every pre-public gate passes.

### Read-only public verification

- [ ] Confirm the repository, privacy policy, security policy, and release tag are anonymously readable; confirm the advisory URL reaches GitHub's expected sign-in boundary.
- [ ] Install `v0.1.0-beta.3` through the HTTPS Git marketplace source in a clean Linux environment without GitHub credentials.
- [ ] Run the release validator against an anonymous tag checkout; run the plugin and skill validators plus all 34 automated tests against the anonymously installed cache copy.
- [ ] Publish the final GitHub release notes only after the anonymous installation succeeds.
