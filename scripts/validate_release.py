#!/usr/bin/env python3

import json
import re
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "delay-execute"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
ABSOLUTE_USER_HOME = re.compile(r"/(?:home|Users)/[^/\s]+(?:/|\b)")


def fail(message: str) -> None:
    raise ValueError(message)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read valid JSON from {path.relative_to(ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def require_relative_file(base: Path, raw_path: object, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.startswith("./"):
        fail(f"{label} must be a ./-prefixed relative path")
    candidate = (base / raw_path).resolve()
    if not candidate.is_relative_to(base.resolve()) or not candidate.is_file():
        fail(f"{label} does not resolve to a file inside the plugin")
    return candidate


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / name.decode() for name in result.stdout.split(b"\0") if name]


def validate() -> None:
    marketplace = read_json(ROOT / ".agents/plugins/marketplace.json")
    portable = read_json(PLUGIN / "plugin.json")
    compatibility = read_json(PLUGIN / ".codex-plugin/plugin.json")
    hooks = read_json(PLUGIN / "hooks/hooks.json")

    if marketplace.get("name") != "delay-execute-marketplace":
        fail("unexpected marketplace name")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or len(entries) != 1:
        fail("marketplace must contain exactly one plugin entry")
    entry = entries[0]
    if not isinstance(entry, dict):
        fail("marketplace plugin entry must be an object")

    names = {entry.get("name"), portable.get("name"), compatibility.get("name")}
    if names != {"delay-execute"} or PLUGIN.name not in names:
        fail("plugin names and directory name must match")
    if entry.get("source") != {
        "source": "local",
        "path": "./plugins/delay-execute",
    }:
        fail("marketplace source must point to ./plugins/delay-execute")
    if entry.get("policy") != {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }:
        fail("marketplace policy is incomplete or unexpected")
    if entry.get("category") != "Productivity":
        fail("marketplace category must be Productivity")

    version = portable.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        fail("portable plugin version is not strict semantic versioning")
    if compatibility.get("version") != version:
        fail("portable and compatibility manifest versions differ")
    if portable.get("license") != "MIT" or compatibility.get("license") != "MIT":
        fail("both manifests must declare the MIT license")

    extension = portable.get("extensions", {}).get("com.openai", {})
    require_relative_file(PLUGIN, extension.get("hooks"), "OpenAI hook path")
    prompts = extension.get("interface", {}).get("defaultPrompt")
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        fail("portable manifest must provide one to three starter prompts")
    if any(not isinstance(prompt, str) or len(prompt) > 128 for prompt in prompts):
        fail("starter prompts must be strings of at most 128 characters")

    submit_hooks = hooks.get("hooks", {}).get("UserPromptSubmit")
    if not isinstance(submit_hooks, list) or len(submit_hooks) != 1:
        fail("exactly one UserPromptSubmit hook group is required")
    command = submit_hooks[0].get("hooks", [{}])[0].get("command")
    if command != 'python3 "$PLUGIN_ROOT/scripts/capture_context.py"':
        fail("hook command must resolve capture_context.py through PLUGIN_ROOT")

    for script_name in ("capture_context.py", "delay_execute.py"):
        mode = (PLUGIN / "scripts" / script_name).stat().st_mode
        if not mode & stat.S_IXUSR:
            fail(f"scripts/{script_name} must be executable by the owner")

    required_repository_files = (
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "PRIVACY.md",
        "CHANGELOG.md",
        "RELEASE_CHECKLIST.md",
        "docs/TESTING.md",
        "docs/EVALS.md",
    )
    for relative in required_repository_files:
        if not (ROOT / relative).is_file():
            fail(f"missing repository file: {relative}")

    for path in tracked_files():
        relative = path.relative_to(ROOT)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            fail(f"generated Python artifact is tracked: {relative}")
        if path.suffix.lower() in {".md", ".json", ".py", ".yml", ".yaml"}:
            text = path.read_text(encoding="utf-8")
            if "[" + "TODO:" in text:
                fail(f"placeholder remains in {relative}")
            if path.is_relative_to(PLUGIN) and ABSOLUTE_USER_HOME.search(text):
                fail(f"machine-specific home path remains in {relative}")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"release validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print("release validation passed")
