#!/usr/bin/env python3
"""Make the active session identity available to the delay-execute skill."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


APP = "delay-execute"


def runtime_paths(environ: dict[str, str] | None = None) -> tuple[Path, Path]:
    environ = os.environ if environ is None else environ
    plugin_root = Path(environ.get("PLUGIN_ROOT", Path(__file__).resolve().parents[1])).resolve()
    codex_home = Path(environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    plugin_data = Path(
        environ.get("PLUGIN_DATA", codex_home / "plugin-data" / APP)
    ).expanduser().resolve()
    return plugin_root / "scripts" / "delay_execute.py", plugin_data


def safe_identifier(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")
    return normalized[:128] or "unknown"


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    prompt = event.get("prompt", "")
    normalized_prompt = prompt.lower()
    if "$delay-execute" not in normalized_prompt and "/delay-execute" not in normalized_prompt:
        return 0

    session_id = event.get("session_id")
    cwd = event.get("cwd")
    if not isinstance(session_id, str) or not isinstance(cwd, str):
        return 0

    helper_path, state_dir = runtime_paths()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    context_id = safe_identifier(event.get("turn_id", session_id))
    context_path = state_dir / f"context-{context_id}.json"
    context = {
        "session_id": session_id,
        "cwd": cwd,
        "helper_path": str(helper_path),
        "state_dir": str(state_dir),
    }
    context_path.write_text(
        json.dumps(context, ensure_ascii=False),
        encoding="utf-8",
    )
    os.chmod(context_path, 0o600)
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        "Delay Execute active-session context: "
                        f"{json.dumps(context, ensure_ascii=False)}. Use these exact values "
                        "when running the helper for this invocation; pass state_dir with "
                        "--state-dir and do not infer paths or a session ID from transcripts."
                    ),
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
