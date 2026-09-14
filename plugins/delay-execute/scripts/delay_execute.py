#!/usr/bin/env python3
"""Create and operate confirmed, resumable Codex tasks through systemd user timers."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
from pathlib import Path


APP = "codex-delay-execute"
SYSTEMD_DIR = Path.home() / ".config" / "systemd" / "user"
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
IDLE_POLL_SECONDS = 15
IDLE_WAIT_SECONDS = 60 * 60
TMUX_SUBMIT_SETTLE_SECONDS = 2


def default_state_dir(environ: dict[str, str] | None = None) -> Path:
    environ = os.environ if environ is None else environ
    plugin_data = environ.get("PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data).expanduser().resolve()
    codex_home = Path(environ.get("CODEX_HOME", Path.home() / ".codex"))
    return (codex_home.expanduser().resolve() / "plugin-data" / "delay-execute")


def configure_state_dir(path: Path | str) -> None:
    global STATE_DIR, TASK_DIR, PENDING_DIR, LOG_DIR, HISTORY_FILE
    STATE_DIR = Path(path).expanduser().resolve()
    TASK_DIR = STATE_DIR / "tasks"
    PENDING_DIR = STATE_DIR / "pending"
    LOG_DIR = STATE_DIR / "logs"
    HISTORY_FILE = STATE_DIR / "history.jsonl"


configure_state_dir(default_state_dir())


def fail(message: str) -> None:
    raise SystemExit(message)


def ensure_directories() -> None:
    for directory in (TASK_DIR, PENDING_DIR, LOG_DIR):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
    SYSTEMD_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def runtime_script_path() -> Path:
    return TASK_DIR / "delay_execute_runtime.py"


def install_runtime() -> Path:
    destination = runtime_script_path()
    source = Path(__file__).resolve()
    if source != destination.resolve():
        shutil.copy2(source, destination)
    os.chmod(destination, 0o700)
    return destination


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def migrate_legacy_state(legacy: Path | None = None) -> int:
    legacy = (
        Path.home() / ".local" / "state" / APP
        if legacy is None
        else Path(legacy).expanduser().resolve()
    )
    marker = STATE_DIR / ".legacy-state-imported.json"
    if legacy == STATE_DIR or marker.exists() or not legacy.is_dir():
        return 0

    imported = 0
    patterns = (
        (legacy / "tasks", TASK_DIR, "*.json"),
        (legacy / "pending", PENDING_DIR, "*.json"),
        (legacy / "logs", LOG_DIR, "*.log"),
    )
    for source_dir, destination_dir, pattern in patterns:
        if not source_dir.is_dir():
            continue
        for source in source_dir.glob(pattern):
            destination = destination_dir / source.name
            if not destination.exists():
                shutil.copy2(source, destination)
                os.chmod(destination, 0o600)
                imported += 1

    legacy_history = legacy / "history.jsonl"
    if legacy_history.is_file() and not HISTORY_FILE.exists():
        shutil.copy2(legacy_history, HISTORY_FILE)
        os.chmod(HISTORY_FILE, 0o600)
        imported += 1

    write_json(
        marker,
        {
            "source": str(legacy),
            "imported_files": imported,
            "imported_at": dt.datetime.now().astimezone().isoformat(),
        },
    )
    return imported


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"无法读取任务记录 {path}: {error}")


def task_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)


def parse_clock(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", value)
    if not match:
        fail("时间必须是本机时区的 HH:MM，例如 02:15")
    return int(match.group(1)), int(match.group(2))


def next_at(hour: int, minute: int, weekday: int | None = None) -> dt.datetime:
    now = dt.datetime.now().astimezone()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if weekday is None:
        if target <= now:
            target += dt.timedelta(days=1)
        return target
    target += dt.timedelta(days=(weekday - target.weekday()) % 7)
    if target <= now:
        target += dt.timedelta(days=7)
    return target


def schedule_from_args(args: argparse.Namespace) -> tuple[str, str, dt.datetime]:
    if args.at:
        hour, minute = parse_clock(args.at)
        target = next_at(hour, minute)
        return "once", target.strftime("%Y-%m-%d %H:%M:%S"), target
    if args.daily_at:
        hour, minute = parse_clock(args.daily_at)
        target = next_at(hour, minute)
        return "daily", f"*-*-* {hour:02d}:{minute:02d}:00", target
    hour, minute = parse_clock(args.weekly_at)
    weekday = WEEKDAYS[args.weekday.lower()]
    target = next_at(hour, minute, weekday)
    return "weekly", f"{args.weekday.title()} *-*-* {hour:02d}:{minute:02d}:00", target


def systemctl(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["systemctl", "--user", *arguments], text=True, capture_output=True)
    if check and result.returncode:
        fail((result.stderr or result.stdout).strip() or f"systemctl {' '.join(arguments)} 失败")
    return result


def unit_name(identifier: str) -> str:
    return f"{APP}-{identifier}"


def systemd_quote_argument(value: str | Path) -> str:
    text = str(value)
    if "\n" in text or "\0" in text:
        fail("systemd 路径不能包含换行或 NUL 字符")
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("%", "%%").replace("$", "$$")
    return f'"{escaped}"'


def tmux_attachment(environ: dict[str, str] | None = None) -> dict[str, str] | None:
    environ = os.environ if environ is None else environ
    tmux = environ.get("TMUX", "")
    pane = environ.get("TMUX_PANE", "")
    if not tmux or not re.fullmatch(r"%\d+", pane):
        return None
    server = tmux.split(",", 1)[0]
    if not server.startswith("/"):
        return None
    return {"server": server, "pane": pane}


def transition_task(identifier: str, status: str) -> None:
    allowed = {
        "queued",
        "waiting_for_idle",
        "injected",
        "detached_running",
        "completed",
        "blocked_by_active_session",
        "failed",
    }
    if status not in allowed:
        fail(f"不支持的任务状态: {status}")
    path = TASK_DIR / f"{identifier}.json"
    if not path.exists():
        fail(f"未找到已安装任务: {identifier}")
    record = read_json(path)
    record["runtime_status"] = status
    record["updated_at"] = dt.datetime.now().astimezone().isoformat()
    write_json(path, record)


def is_git_repository(cwd: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--is-inside-work-tree"],
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def execution_mode(cwd: Path) -> str:
    if is_git_repository(cwd):
        return "git"
    return "non_git"


def resume_command_parts(codex: str, record: dict, mode: str) -> list[str]:
    command_parts = [codex, "exec", "resume"]
    if mode in {"non_git", "trusted_non_git"}:
        command_parts.append("--skip-git-repo-check")
    elif mode != "git":
        fail(f"不支持的执行模式: {mode}")
    command_parts.extend((record["session_id"], record["prompt"]))
    return command_parts


def command_stage(args: argparse.Namespace) -> None:
    ensure_directories()
    schedule_type, calendar, next_run = schedule_from_args(args)
    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        fail(f"工作目录不存在: {cwd}")
    if not args.session_id.strip() or not args.prompt.strip():
        fail("session ID 和任务提示词不能为空")
    mode = execution_mode(cwd)
    attachment = tmux_attachment()
    identifier = task_id()
    record = {
        "id": identifier,
        "session_id": args.session_id,
        "cwd": str(cwd),
        "prompt": args.prompt,
        "schedule_type": schedule_type,
        "calendar": calendar,
        "next_run": next_run.isoformat(),
        "idle_wait_minutes": IDLE_WAIT_SECONDS // 60,
        "retry_policy": "none",
        "execution_mode": mode,
        "attachment": attachment,
        "delivery_mode": "session_attached" if attachment else "detached",
        "state_dir": str(STATE_DIR),
        "created_at": dt.datetime.now().astimezone().isoformat(),
        "status": "pending_confirmation",
    }
    write_json(PENDING_DIR / f"{identifier}.json", record)
    print(json.dumps(record, ensure_ascii=False))


def write_runner(record: dict) -> Path:
    ensure_directories()
    codex = shutil.which("codex")
    if not codex:
        fail("找不到 codex 命令；请确认 systemd 用户环境中可用的 PATH")
    identifier = record["id"]
    runner = TASK_DIR / f"run-{identifier}.sh"
    log_file = LOG_DIR / f"{identifier}.log"
    lock_file = TASK_DIR / f"{identifier}.lock"
    current_mode = execution_mode(Path(record["cwd"]).resolve())
    mode = record.get("execution_mode") or current_mode
    if mode == "trusted_non_git" and current_mode == "non_git":
        mode = current_mode
    elif mode != current_mode:
        fail("工作目录的 Git 状态已改变；请重新暂存并确认任务")
    command_parts = resume_command_parts(codex, record, mode)
    command = " ".join(shlex.quote(part) for part in command_parts)
    script = shlex.quote(str(runtime_script_path()))
    state_dir = shlex.quote(str(STATE_DIR))
    attachment = record.get("attachment") or {}
    server = attachment.get("server") if isinstance(attachment, dict) else None
    pane = attachment.get("pane") if isinstance(attachment, dict) else None
    tmux_server = shlex.quote(server) if isinstance(server, str) else ""
    tmux_pane = shlex.quote(pane) if isinstance(pane, str) else ""
    content = f"""#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p {shlex.quote(str(LOG_DIR))}
exec 9>{shlex.quote(str(lock_file))}
flock -n 9 || exit 0
record_event() {{
  printf '{{"at":"%s","task_id":"%s","event":"%s","exit_code":%s}}\\n' \\
    "$(date --iso-8601=seconds)" {shlex.quote(identifier)} "$1" "$2" >> {shlex.quote(str(HISTORY_FILE))}
}}
transition() {{
  python3 {script} --state-dir {state_dir} transition --task-id {shlex.quote(identifier)} --status "$1" >> {shlex.quote(str(log_file))} 2>&1
}}
finish() {{
  status=$?
  record_event finished "$status"
  printf '%s finished: %s (exit=%s)\\n' "$(date --iso-8601=seconds)" {shlex.quote(identifier)} "$status" >> {shlex.quote(str(log_file))}
  trap - EXIT
  exit "$status"
}}
trap finish EXIT
cd {shlex.quote(record['cwd'])}
record_event queued 0
transition queued
run_detached() {{
  transition detached_running
  record_event detached_running 0
  set +e
  timeout --foreground 4h {command} >> {shlex.quote(str(log_file))} 2>&1
  status=$?
  set -e
  if [ "$status" -eq 0 ]; then
    transition completed
    record_event completed 0
    return 0
  fi
  if tail -n 40 {shlex.quote(str(log_file))} | grep -q 'already has an active writer'; then
    transition blocked_by_active_session
    record_event blocked_by_active_session "$status"
    return 0
  fi
  transition failed
  record_event failed "$status"
  return "$status"
}}
if [ -n {shlex.quote(tmux_server)} ] && [ -n {shlex.quote(tmux_pane)} ]; then
  transition waiting_for_idle
  record_event waiting_for_idle 0
  deadline=$(( $(date +%s) + {IDLE_WAIT_SECONDS} ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if ! tmux -S {tmux_server} has-session >/dev/null 2>&1; then
      record_event attachment_unavailable 0
      run_detached
      exit $?
    fi
    if ! pane_snapshot=$(tmux -S {tmux_server} capture-pane -p -t {tmux_pane} -S -8 2>/dev/null); then
      record_event attachment_unavailable 0
      run_detached
      exit $?
    fi
    if printf '%s\n' "$pane_snapshot" | tail -n 8 | grep -q 'Ask Codex to do anything' && \
       ! printf '%s\n' "$pane_snapshot" | tail -n 8 | grep -q 'Working ('; then
      tmux -S {tmux_server} set-buffer -- {shlex.quote(record['prompt'])}
      tmux -S {tmux_server} paste-buffer -d -t {tmux_pane}
      sleep {TMUX_SUBMIT_SETTLE_SECONDS}
      tmux -S {tmux_server} send-keys -t {tmux_pane} Enter
      transition injected
      record_event injected 0
      exit 0
    fi
    sleep {IDLE_POLL_SECONDS}
  done
  transition blocked_by_active_session
  record_event blocked_by_active_session 0
  exit 0
fi
run_detached
"""
    runner.write_text(content, encoding="utf-8")
    os.chmod(runner, 0o700)
    return runner


def command_install(args: argparse.Namespace) -> None:
    ensure_directories()
    pending = PENDING_DIR / f"{args.task_id}.json"
    if not pending.exists():
        fail(f"未找到待确认任务: {args.task_id}")
    record = read_json(pending)
    install_runtime()
    runner = write_runner(record)
    name = unit_name(record["id"])
    service = SYSTEMD_DIR / f"{name}.service"
    timer = SYSTEMD_DIR / f"{name}.timer"
    service.write_text(
        "[Unit]\nDescription=Deliver a confirmed Codex delayed task\n"
        "\n"
        "[Service]\nType=oneshot\n"
        "SuccessExitStatus=SIGTERM\n"
        f"ExecStart={systemd_quote_argument(runner)}\n",
        encoding="utf-8",
    )
    timer.write_text(
        "[Unit]\nDescription=Run a confirmed Codex delayed task\n\n"
        "[Timer]\n"
        f"OnCalendar={record['calendar']}\nPersistent=true\nAccuracySec=1s\n\n"
        "[Install]\nWantedBy=timers.target\n",
        encoding="utf-8",
    )
    os.chmod(service, 0o600)
    os.chmod(timer, 0o600)
    record["status"] = "scheduled"
    record["runtime_status"] = "queued"
    record["runner"] = str(runner)
    record["timer"] = f"{name}.timer"
    record["history"] = str(HISTORY_FILE)
    record["state_dir"] = str(STATE_DIR)
    write_json(TASK_DIR / f"{record['id']}.json", record)
    systemctl("daemon-reload")
    systemctl("enable", "--now", f"{name}.timer")
    pending.unlink()
    print(json.dumps(record, ensure_ascii=False))


def command_list(_: argparse.Namespace) -> None:
    ensure_directories()
    records = []
    for path in sorted(TASK_DIR.glob("*.json")):
        record = read_json(path)
        timer = record.get("timer")
        if record.get("status") == "scheduled" and timer:
            record["timer_state"] = systemctl("is-active", timer, check=False).stdout.strip() or "unknown"
        records.append(record)
    print(json.dumps(records, ensure_ascii=False))


def command_cancel(args: argparse.Namespace) -> None:
    ensure_directories()
    record_path = TASK_DIR / f"{args.task_id}.json"
    if not record_path.exists():
        fail(f"未找到已安装任务: {args.task_id}")
    name = unit_name(args.task_id)
    systemctl("disable", "--now", f"{name}.timer", check=False)
    systemctl("stop", f"{name}.service", check=False)
    for suffix in ("service", "timer"):
        (SYSTEMD_DIR / f"{name}.{suffix}").unlink(missing_ok=True)
    systemctl("daemon-reload")
    record = read_json(record_path)
    record["status"] = "cancelled"
    write_json(record_path, record)
    print(json.dumps(record, ensure_ascii=False))


def command_transition(args: argparse.Namespace) -> None:
    ensure_directories()
    transition_task(args.task_id, args.status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--import-legacy-state", action="store_true", help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage")
    stage.add_argument("--session-id", required=True)
    stage.add_argument("--cwd", required=True)
    timing = stage.add_mutually_exclusive_group(required=True)
    timing.add_argument("--at")
    timing.add_argument("--daily-at")
    timing.add_argument("--weekly-at")
    stage.add_argument("--weekday", choices=sorted(WEEKDAYS))
    stage.add_argument("--prompt", required=True)
    stage.set_defaults(handler=command_stage)
    install = commands.add_parser("install")
    install.add_argument("--task-id", required=True)
    install.set_defaults(handler=command_install)
    commands.add_parser("list").set_defaults(handler=command_list)
    cancel = commands.add_parser("cancel")
    cancel.add_argument("--task-id", required=True)
    cancel.set_defaults(handler=command_cancel)
    transition = commands.add_parser("transition")
    transition.add_argument("--task-id", required=True)
    transition.add_argument("--status", required=True)
    transition.set_defaults(handler=command_transition)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.state_dir is not None:
        configure_state_dir(args.state_dir)
    ensure_directories()
    if args.import_legacy_state:
        migrate_legacy_state()
    if args.command == "stage" and args.weekly_at and not args.weekday:
        fail("--weekly-at 必须与 --weekday（mon 至 sun）一起使用")
    if args.command == "stage" and args.weekday and not args.weekly_at:
        fail("--weekday 只能与 --weekly-at 一起使用")
    args.handler(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
