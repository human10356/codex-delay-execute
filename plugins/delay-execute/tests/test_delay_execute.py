import argparse
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "delay_execute.py"
SPEC = importlib.util.spec_from_file_location("delay_execute", SCRIPT)
delay_execute = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(delay_execute)

CAPTURE_SCRIPT = Path(__file__).parents[1] / "scripts" / "capture_context.py"


class ExecutionModeTests(unittest.TestCase):
    def test_default_state_directory_follows_codex_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            codex_home = Path(temporary) / "portable-codex-home"
            state = delay_execute.default_state_dir({"CODEX_HOME": str(codex_home)})
        self.assertEqual(state, codex_home / "plugin-data" / "delay-execute")

    def test_plugin_data_takes_priority_for_state_directory(self):
        state = delay_execute.default_state_dir(
            {"PLUGIN_DATA": "/tmp/delay data", "CODEX_HOME": "/tmp/codex"}
        )
        self.assertEqual(state, Path("/tmp/delay data"))

    def test_legacy_task_metadata_is_imported_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy"
            target = root / "plugin-data"
            (legacy / "tasks").mkdir(parents=True)
            (legacy / "pending").mkdir()
            (legacy / "logs").mkdir()
            (legacy / "tasks" / "old.json").write_text('{"id":"old"}\n', encoding="utf-8")
            (legacy / "tasks" / "run-old.sh").write_text("legacy runner\n", encoding="utf-8")
            (legacy / "logs" / "old.log").write_text("old log\n", encoding="utf-8")
            (legacy / "history.jsonl").write_text('{"event":"old"}\n', encoding="utf-8")
            with patch.object(delay_execute, "STATE_DIR", target), patch.object(
                delay_execute, "TASK_DIR", target / "tasks"
            ), patch.object(delay_execute, "PENDING_DIR", target / "pending"), patch.object(
                delay_execute, "LOG_DIR", target / "logs"
            ), patch.object(delay_execute, "HISTORY_FILE", target / "history.jsonl"):
                delay_execute.ensure_directories()
                imported = delay_execute.migrate_legacy_state(legacy)
                imported_again = delay_execute.migrate_legacy_state(legacy)
                task = (target / "tasks" / "old.json").read_text(encoding="utf-8")
                history = (target / "history.jsonl").read_text(encoding="utf-8")
                task_mode = stat.S_IMODE((target / "tasks" / "old.json").stat().st_mode)
                log_mode = stat.S_IMODE((target / "logs" / "old.log").stat().st_mode)
                history_mode = stat.S_IMODE((target / "history.jsonl").stat().st_mode)
                runner_exists = (target / "tasks" / "run-old.sh").exists()
        self.assertEqual(imported, 3)
        self.assertEqual(imported_again, 0)
        self.assertIn('"id":"old"', task)
        self.assertIn('"event":"old"', history)
        self.assertEqual(task_mode, 0o600)
        self.assertEqual(log_mode, 0o600)
        self.assertEqual(history_mode, 0o600)
        self.assertFalse(runner_exists)

    def test_legacy_state_is_not_imported_without_explicit_opt_in(self):
        original_state_dir = delay_execute.STATE_DIR
        try:
            with tempfile.TemporaryDirectory() as temporary, patch.object(
                sys, "argv", [str(SCRIPT), "--state-dir", temporary, "list"]
            ), patch.object(delay_execute, "ensure_directories"), patch.object(
                delay_execute, "migrate_legacy_state"
            ) as migrate, patch.object(delay_execute, "command_list") as command_list:
                result = delay_execute.main()
        finally:
            delay_execute.configure_state_dir(original_state_dir)

        self.assertEqual(result, 0)
        migrate.assert_not_called()
        command_list.assert_called_once()

    def test_legacy_state_import_can_be_explicitly_requested(self):
        original_state_dir = delay_execute.STATE_DIR
        try:
            with tempfile.TemporaryDirectory() as temporary, patch.object(
                sys,
                "argv",
                [
                    str(SCRIPT),
                    "--state-dir",
                    temporary,
                    "--import-legacy-state",
                    "list",
                ],
            ), patch.object(delay_execute, "ensure_directories"), patch.object(
                delay_execute, "migrate_legacy_state"
            ) as migrate, patch.object(delay_execute, "command_list") as command_list:
                result = delay_execute.main()
        finally:
            delay_execute.configure_state_dir(original_state_dir)

        self.assertEqual(result, 0)
        migrate.assert_called_once_with()
        command_list.assert_called_once()

    def test_hook_uses_the_installed_plugin_root(self):
        hook = json.loads(
            (Path(__file__).parents[1] / "hooks" / "hooks.json").read_text(encoding="utf-8")
        )
        command = hook["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn('$PLUGIN_ROOT/scripts/capture_context.py', command)
        self.assertNotIn("/home/", command)

    def test_capture_context_reports_portable_runtime_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "installed plugin"
            data = Path(temporary) / "plugin data"
            (root / "scripts").mkdir(parents=True)
            helper = root / "scripts" / "delay_execute.py"
            helper.touch()
            event = {
                "prompt": "$delay-execute 02:15 continue",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "cwd": "/tmp/project",
            }
            environment = os.environ.copy()
            environment.update({"PLUGIN_ROOT": str(root), "PLUGIN_DATA": str(data)})
            result = subprocess.run(
                ["python3", str(CAPTURE_SCRIPT)],
                input=json.dumps(event),
                text=True,
                capture_output=True,
                env=environment,
            )
            output = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn(str(helper), context)
        self.assertIn(str(data), context)

    def test_non_git_directory_is_allowed_after_task_confirmation(self):
        with tempfile.TemporaryDirectory() as temporary:
            cwd = Path(temporary) / "notes"
            cwd.mkdir()
            with patch.object(delay_execute, "is_git_repository", return_value=False):
                self.assertEqual(delay_execute.execution_mode(cwd.resolve()), "non_git")

    def test_missing_git_command_is_treated_as_non_git(self):
        with patch.object(delay_execute.subprocess, "run", side_effect=FileNotFoundError):
            self.assertFalse(delay_execute.is_git_repository(Path("/tmp")))

    def test_non_git_runner_explicitly_skips_git_check(self):
        record = {"session_id": "session", "prompt": "continue"}
        self.assertEqual(
            delay_execute.resume_command_parts("codex", record, "non_git"),
            [
                "codex",
                "exec",
                "resume",
                "--skip-git-repo-check",
                "session",
                "continue",
            ],
        )

    def test_tty_attachment_uses_the_current_tmux_pane(self):
        self.assertEqual(
            delay_execute.tmux_attachment(
                {"TMUX": "/tmp/tmux.sock,123,0", "TMUX_PANE": "%9"}
            ),
            {"server": "/tmp/tmux.sock", "pane": "%9"},
        )

    def test_runner_waits_for_idle_and_does_not_configure_systemd_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = {
                "id": "test-task",
                "cwd": str(root),
                "session_id": "session",
                "prompt": "continue",
                "execution_mode": "non_git",
                "attachment": {"server": "/tmp/tmux.sock", "pane": "%9"},
            }
            with patch.object(delay_execute, "STATE_DIR", root), patch.object(
                delay_execute, "TASK_DIR", root / "tasks"
            ), patch.object(
                delay_execute, "PENDING_DIR", root / "pending"
            ), patch.object(delay_execute, "LOG_DIR", root / "logs"), patch.object(
                delay_execute, "HISTORY_FILE", root / "history.jsonl"
            ), patch.object(delay_execute, "SYSTEMD_DIR", root / "systemd"), patch.object(
                delay_execute.shutil, "which", return_value="/usr/bin/codex"
            ), patch.object(delay_execute, "execution_mode", return_value="non_git"):
                runner = delay_execute.write_runner(record)
                content = runner.read_text(encoding="utf-8")
                syntax = subprocess.run(["bash", "-n", str(runner)], capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr.decode())
        self.assertIn("paste-buffer -d -t %9", content)
        self.assertIn("umask 077", content)
        paste = content.index("paste-buffer -d -t %9")
        settle = content.index("sleep 2", paste)
        submit = content.index("send-keys -t %9 Enter", paste)
        self.assertLess(paste, settle)
        self.assertLess(settle, submit)
        self.assertIn("already has an active writer", content)
        self.assertIn(str(root / "tasks" / "delay_execute_runtime.py"), content)
        self.assertIn(f"--state-dir {root} transition", content)
        self.assertIn("grep -q 'Working ('", content)

    def test_install_creates_a_non_restarting_service(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = {
                "id": "test-task",
                "cwd": str(root),
                "session_id": "session",
                "prompt": "continue",
                "execution_mode": "non_git",
                "attachment": None,
                "calendar": "2026-09-14 04:00:00",
                "schedule_type": "once",
            }
            with patch.object(delay_execute, "STATE_DIR", root), patch.object(
                delay_execute, "TASK_DIR", root / "tasks"
            ), patch.object(
                delay_execute, "PENDING_DIR", root / "pending"
            ), patch.object(delay_execute, "LOG_DIR", root / "logs"), patch.object(
                delay_execute, "HISTORY_FILE", root / "history.jsonl"
            ), patch.object(delay_execute, "SYSTEMD_DIR", root / "systemd"), patch.object(
                delay_execute.shutil, "which", return_value="/usr/bin/codex"
            ), patch.object(delay_execute, "execution_mode", return_value="non_git"), patch.object(
                delay_execute, "systemctl"
            ):
                delay_execute.ensure_directories()
                delay_execute.write_json(delay_execute.PENDING_DIR / "test-task.json", record)
                delay_execute.command_install(argparse.Namespace(task_id="test-task"))
                service = (root / "systemd" / "codex-delay-execute-test-task.service").read_text(
                    encoding="utf-8"
                )
                timer = (root / "systemd" / "codex-delay-execute-test-task.timer").read_text(
                    encoding="utf-8"
                )
                runtime = root / "tasks" / "delay_execute_runtime.py"
                runtime_exists = runtime.is_file()
        self.assertNotIn("Restart=", service)
        self.assertIn("SuccessExitStatus=SIGTERM", service)
        self.assertIn("Persistent=true", timer)
        self.assertIn("AccuracySec=1s", timer)
        self.assertTrue(runtime_exists)

    def test_systemd_exec_start_quotes_a_state_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "plugin data"
            root.mkdir()
            record = {
                "id": "test-task",
                "cwd": str(root),
                "session_id": "session",
                "prompt": "continue",
                "execution_mode": "non_git",
                "attachment": None,
                "calendar": "2026-09-14 04:00:00",
                "schedule_type": "once",
            }
            with patch.object(delay_execute, "STATE_DIR", root), patch.object(
                delay_execute, "TASK_DIR", root / "tasks"
            ), patch.object(delay_execute, "PENDING_DIR", root / "pending"), patch.object(
                delay_execute, "LOG_DIR", root / "logs"
            ), patch.object(delay_execute, "HISTORY_FILE", root / "history.jsonl"), patch.object(
                delay_execute, "SYSTEMD_DIR", root / "systemd"
            ), patch.object(delay_execute.shutil, "which", return_value="/usr/bin/codex"), patch.object(
                delay_execute, "execution_mode", return_value="non_git"
            ), patch.object(delay_execute, "systemctl"):
                delay_execute.ensure_directories()
                delay_execute.write_json(delay_execute.PENDING_DIR / "test-task.json", record)
                delay_execute.command_install(argparse.Namespace(task_id="test-task"))
                service = (root / "systemd" / "codex-delay-execute-test-task.service").read_text(
                    encoding="utf-8"
                )
        self.assertIn(f'ExecStart="{root}/tasks/run-test-task.sh"', service)


if __name__ == "__main__":
    unittest.main()
