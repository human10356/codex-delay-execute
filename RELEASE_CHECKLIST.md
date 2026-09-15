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
- [x] Final WSL catch-up audit on 2026-09-15: a confirmed one-time task missed its 13:05 deadline while WSL was shut down. The prior boot ended at 12:49:58, the next boot started at 13:06:34, and the persistent timer activated the service at 13:06:35. The task completed at 13:08:10; its durable state remains `attempted/completed` with `attempt_count=1`, history has exactly one event at each delivery stage, and the service journal has one start. The service remains inactive with `Result=success` and `NRestarts=0`; the timer is disabled/inactive, the task lock is free, and the only remaining thread writer lock belongs to the manually resumed foreground Codex session.
- [x] The annotated `v0.1.0-beta.3` tag was pushed from reviewed commit `3cbaf59dd9d9789be687bcf60dcc2d5ebd77d9dc`; the remote tag peels to that commit.
- [x] On a separate Ubuntu 24.04.5 WSL distribution, a credential-free local beta.3 snapshot installed and passed all 34 tests. An independent repository-scoped SSH deploy key then read the private tag and installed the pinned Git Marketplace into an isolated Codex home. Release validation, Python compilation, all 34 tests, and installed skill/hook discovery passed. The fresh isolated hook remained untrusted, as expected; no timer or detached writer was left behind.

## Publication gates

### Before changing repository visibility

- [x] GitHub Actions run `34963548192` for `main` commit `c0db82ce205850a719e0bf1285473e6fb0803d2f` completed successfully; its Python 3.10, 3.12, and 3.14 jobs each concluded `success`.
- [x] Keep the changelog's candidate-validation date distinct from the publication date, which cannot be recorded until the repository becomes public.
- [x] Create and push the annotated `v0.1.0-beta.3` tag from the reviewed commit. Later audit-only documentation commits on `main` do not move this immutable tag.

### Publication boundary

- [x] The repository became public on 2026-09-15 after the pre-public gates passed. Anonymous GitHub API access returned HTTP 200, and credential-disabled HTTPS Git access read the annotated beta.3 tag and its peeled commit.

### Read-only public verification

- [x] The repository, `PRIVACY.md`, `SECURITY.md`, and beta.3 tag page returned HTTP 200 anonymously; the private security-advisory creation URL redirected to GitHub's sign-in page.
- [x] A separate Ubuntu 24.04.5 WSL distribution installed `v0.1.0-beta.3` from the HTTPS Git Marketplace with a fresh Codex home, disabled credential helpers, and no GitHub credentials. Codex listed the installed plugin as enabled.
- [x] The anonymous tag checkout matched commit `3cbaf59dd9d9789be687bcf60dcc2d5ebd77d9dc` and passed release validation, Python compilation, and all 34 tests. The installed cache passed plugin and skill validation, compilation, and all 34 tests; its source files matched the tag checkout.
- [x] Record the actual 2026-09-15 publication date in the changelog, checklist, and testing record; commit the documentation without moving the beta.3 tag.
- [ ] Publish the final GitHub release notes only after the anonymous installation succeeds.
