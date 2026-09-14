import importlib.util
import json
import os
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "delay_execute.py"
SPEC = importlib.util.spec_from_file_location("delay_execute_integration", SCRIPT)
delay_execute = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(delay_execute)

REQUIRED_TOOLS = ("bash", "flock", "ps", "timeout", "tmux")


@unittest.skipUnless(
    all(shutil.which(tool) for tool in REQUIRED_TOOLS),
    "runner integration tests require bash, flock, ps, timeout, and tmux",
)
class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state_dir = self.root / "state"
        self.systemd_dir = self.root / "systemd"
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        self.pane_bin_dir = self.root / "pane-bin"
        self.pane_bin_dir.mkdir()
        self.pane_codex = self.pane_bin_dir / "codex"
        bash = shutil.which("bash")
        assert bash is not None
        shutil.copy2(bash, self.pane_codex)
        self.fake_codex_log = self.root / "fake-codex.jsonl"
        self.fake_systemctl_log = self.root / "fake-systemctl.jsonl"
        self.original_state_dir = delay_execute.STATE_DIR
        self.original_systemd_dir = delay_execute.SYSTEMD_DIR
        self.addCleanup(delay_execute.configure_state_dir, self.original_state_dir)
        self.addCleanup(setattr, delay_execute, "SYSTEMD_DIR", self.original_systemd_dir)
        delay_execute.configure_state_dir(self.state_dir)
        delay_execute.SYSTEMD_DIR = self.systemd_dir
        delay_execute.ensure_directories()
        self._write_fake_codex()
        self._write_fake_systemctl()
        self.tmux_labels = []
        self.addCleanup(self._stop_tmux_servers)

    def _write_fake_codex(self):
        fake_codex = self.bin_dir / "codex"
        fake_codex.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

log = Path(os.environ["DELAY_EXECUTE_FAKE_CODEX_LOG"])
with log.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
if (
    os.environ.get("DELAY_EXECUTE_FAKE_CODEX_MODE") == "queue_failure"
    and sys.argv[1:2] == ["queue"]
):
    print("queue unavailable", file=sys.stderr)
    raise SystemExit(2)
if os.environ.get("DELAY_EXECUTE_FAKE_CODEX_MODE") == "active_writer":
    print("conversation already has an active writer", file=sys.stderr)
    raise SystemExit(1)
""",
            encoding="utf-8",
        )
        fake_codex.chmod(0o700)

    def _write_fake_systemctl(self):
        fake_systemctl = self.bin_dir / "systemctl"
        fake_systemctl.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

log = Path(os.environ["DELAY_EXECUTE_FAKE_SYSTEMCTL_LOG"])
with log.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\\n")
if os.environ.get("DELAY_EXECUTE_FAKE_SYSTEMCTL_MODE") == "failure":
    raise SystemExit(7)
""",
            encoding="utf-8",
        )
        fake_systemctl.chmod(0o700)

    def _stop_tmux_servers(self):
        for label in self.tmux_labels:
            subprocess.run(
                ["tmux", "-L", label, "kill-server"],
                capture_output=True,
                check=False,
            )

    def _start_tmux_pane(self, *, busy: bool = False, codex_process: bool = True) -> dict:
        label = f"delay-execute-e2e-{uuid.uuid4().hex}"
        self.tmux_labels.append(label)
        shell = str(self.pane_codex) if codex_process else "bash"
        subprocess.run(
            [
                "tmux",
                "-L",
                label,
                "new-session",
                "-d",
                "-s",
                "e2e",
                shell,
                "--noprofile",
                "--norc",
                "-i",
            ],
            check=True,
            capture_output=True,
        )
        prompt = "Ask Codex to do anything"
        if busy:
            prompt += " Working ("
        command = f"export PS1={shlex.quote(prompt + ' ')}"
        subprocess.run(
            ["tmux", "-L", label, "send-keys", "-l", "-t", "e2e:0.0", command],
            check=True,
        )
        subprocess.run(
            ["tmux", "-L", label, "send-keys", "-t", "e2e:0.0", "Enter"],
            check=True,
        )
        server = subprocess.run(
            ["tmux", "-L", label, "display-message", "-p", "#{socket_path}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        pane = subprocess.run(
            ["tmux", "-L", label, "display-message", "-p", "-t", "e2e:0.0", "#{pane_id}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        pane_pid = subprocess.run(
            ["tmux", "-S", server, "display-message", "-p", "-t", pane, "#{pane_pid}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        pane_tty = subprocess.run(
            ["tmux", "-S", server, "display-message", "-p", "-t", pane, "#{pane_tty}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        codex_pid = pane_pid if codex_process else "0"
        codex_start_ticks = (
            delay_execute.process_start_ticks(codex_pid) if codex_process else "0"
        )
        for _ in range(50):
            snapshot = subprocess.run(
                ["tmux", "-S", server, "capture-pane", "-p", "-t", pane, "-S", "-8"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if prompt in snapshot:
                return {
                    "server": server,
                    "pane": pane,
                    "pane_pid": pane_pid,
                    "pane_tty": pane_tty,
                    "codex_pid": codex_pid,
                    "codex_start_ticks": codex_start_ticks,
                }
            time.sleep(0.05)
        self.fail("tmux pane did not render the expected prompt")

    def _create_runner(self, attachment, prompt="integration-test", schedule_type="once"):
        identifier = f"integration-{uuid.uuid4().hex}"
        record = {
            "id": identifier,
            "cwd": str(self.root),
            "session_id": "integration-session",
            "prompt": prompt,
            "schedule_type": schedule_type,
            "execution_mode": "non_git",
            "attachment": attachment,
            "status": "scheduled",
            "runtime_status": "queued",
        }
        delay_execute.write_json(delay_execute.TASK_DIR / f"{identifier}.json", record)
        delay_execute.install_runtime()
        environment = os.environ.copy()
        environment["PATH"] = f"{self.bin_dir}{os.pathsep}{environment['PATH']}"
        with patch.dict(os.environ, environment, clear=True), patch.object(
            delay_execute, "codex_command_prefix", side_effect=lambda codex: [codex]
        ):
            runner = delay_execute.write_runner(record)
        return identifier, runner, environment

    def _run_runner(
        self,
        runner,
        environment,
        *,
        mode="success",
        systemctl_mode="success",
        timeout=10,
    ):
        environment = environment.copy()
        environment["DELAY_EXECUTE_FAKE_CODEX_LOG"] = str(self.fake_codex_log)
        environment["DELAY_EXECUTE_FAKE_CODEX_MODE"] = mode
        environment["DELAY_EXECUTE_FAKE_SYSTEMCTL_LOG"] = str(self.fake_systemctl_log)
        environment["DELAY_EXECUTE_FAKE_SYSTEMCTL_MODE"] = systemctl_mode
        return subprocess.run(
            [str(runner)],
            text=True,
            capture_output=True,
            env=environment,
            timeout=timeout,
        )

    def _record(self, identifier):
        return delay_execute.read_json(delay_execute.TASK_DIR / f"{identifier}.json")

    def _history_events(self):
        if not delay_execute.HISTORY_FILE.exists():
            return []
        return [
            json.loads(line)
            for line in delay_execute.HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        ]

    def test_idle_tmux_pane_queues_without_terminal_input(self):
        attachment = self._start_tmux_pane()
        prompt = "queued-through-official-api"
        identifier, runner, environment = self._create_runner(attachment, prompt)

        result = self._run_runner(runner, environment)
        snapshot = subprocess.run(
            [
                "tmux",
                "-S",
                attachment["server"],
                "capture-pane",
                "-p",
                "-t",
                attachment["pane"],
                "-S",
                "-8",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(prompt, snapshot)
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            invocations,
            [["queue", "--thread", "integration-session", "--message", prompt]],
        )
        self.assertEqual(self._record(identifier)["runtime_status"], "queued_to_session")
        self.assertEqual(stat.S_IMODE(delay_execute.HISTORY_FILE.stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE((delay_execute.LOG_DIR / f"{identifier}.log").stat().st_mode),
            0o600,
        )

    def test_busy_tmux_pane_queues_without_starting_detached_writer(self):
        attachment = self._start_tmux_pane(busy=True)
        identifier, runner, environment = self._create_runner(attachment)

        result = self._run_runner(runner, environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(invocations[0][0], "queue")
        self.assertEqual(self._record(identifier)["runtime_status"], "queued_to_session")
        self.assertNotIn(
            "detached_running", [event["event"] for event in self._history_events()]
        )

    def test_one_time_runner_suppresses_a_second_invocation(self):
        identifier, runner, environment = self._create_runner(None)

        first = self._run_runner(runner, environment)
        second = self._run_runner(runner, environment)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(invocations), 1)
        self.assertEqual(self._record(identifier)["attempt_count"], 1)
        self.assertEqual(self._record(identifier)["status"], "attempted")
        systemctl_invocations = [
            json.loads(line)
            for line in self.fake_systemctl_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            systemctl_invocations,
            [
                [
                    "--user",
                    "disable",
                    "--now",
                    f"codex-delay-execute-{identifier}.timer",
                ]
            ],
        )
        self.assertIn(
            "duplicate_suppressed",
            [event["event"] for event in self._history_events()],
        )

    def test_recurring_runner_allows_later_invocations(self):
        identifier, runner, environment = self._create_runner(
            None, schedule_type="daily"
        )

        first = self._run_runner(runner, environment)
        second = self._run_runner(runner, environment)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(invocations), 2)
        self.assertEqual(self._record(identifier)["attempt_count"], 2)
        self.assertEqual(self._record(identifier)["status"], "scheduled")
        self.assertFalse(self.fake_systemctl_log.exists())
        self.assertNotIn(
            "duplicate_suppressed",
            [event["event"] for event in self._history_events()],
        )

    def test_timer_disarm_failure_preserves_the_real_exit_code(self):
        identifier, runner, environment = self._create_runner(None)

        result = self._run_runner(runner, environment, systemctl_mode="failure")

        self.assertEqual(result.returncode, 0, result.stderr)
        failures = [
            event
            for event in self._history_events()
            if event["event"] == "timer_disarm_failed"
        ]
        self.assertEqual(failures[0]["exit_code"], 7)
        self.assertEqual(self._record(identifier)["attempt_count"], 1)

    def test_missing_tmux_pane_runs_one_detached_attempt(self):
        attachment = self._start_tmux_pane()
        identifier, runner, environment = self._create_runner(attachment)
        subprocess.run(
            ["tmux", "-S", attachment["server"], "kill-server"],
            check=True,
            capture_output=True,
        )

        result = self._run_runner(runner, environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0][:2], ["exec", "resume"])
        self.assertEqual(self._record(identifier)["runtime_status"], "completed")

    def test_queue_failure_runs_one_detached_attempt(self):
        attachment = self._start_tmux_pane()
        identifier, runner, environment = self._create_runner(attachment)

        result = self._run_runner(runner, environment, mode="queue_failure")

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([invocation[0] for invocation in invocations], ["queue", "exec"])
        self.assertEqual(self._record(identifier)["runtime_status"], "completed")
        self.assertEqual(
            [event["event"] for event in self._history_events()].count("queue_failed"),
            1,
        )

    def test_shell_with_codex_prompt_is_never_injected(self):
        attachment = self._start_tmux_pane(codex_process=False)
        injected_marker = self.root / "unsafe-shell-injection"
        prompt = f"printf unsafe > {shlex.quote(str(injected_marker))}"
        identifier, runner, environment = self._create_runner(attachment, prompt)

        result = self._run_runner(runner, environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(injected_marker.exists())
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(invocations), 1)
        self.assertEqual(self._record(identifier)["runtime_status"], "completed")

    def test_replaced_codex_process_is_never_injected(self):
        attachment = self._start_tmux_pane()
        attachment["codex_start_ticks"] = "1"
        injected_marker = self.root / "replaced-process-injection"
        prompt = f"printf unsafe > {shlex.quote(str(injected_marker))}"
        identifier, runner, environment = self._create_runner(attachment, prompt)

        result = self._run_runner(runner, environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(injected_marker.exists())
        invocations = [
            json.loads(line)
            for line in self.fake_codex_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(invocations), 1)
        self.assertEqual(self._record(identifier)["runtime_status"], "completed")

    def test_active_writer_becomes_terminal_without_restart(self):
        identifier, runner, environment = self._create_runner(None)

        result = self._run_runner(runner, environment, mode="active_writer")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._record(identifier)["runtime_status"], "blocked_by_active_session")
        events = [event["event"] for event in self._history_events()]
        self.assertEqual(events.count("detached_running"), 1)
        self.assertEqual(events.count("blocked_by_active_session"), 1)


if __name__ == "__main__":
    unittest.main()
