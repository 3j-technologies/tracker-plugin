#!/usr/bin/env python3
"""Deterministic public-readiness validation for the tracker-plugin repository.

Checks, independent of any host CLI:
  - every *.json file in the repo parses as valid JSON
  - the exact production MCP URL (https://mcp-tracker.3jtech.app/mcp) appears
    wherever a host manifest declares the Tracker MCP server
  - no forbidden strings (TRACKER_MCP_URL, non-prod hosts, auth/token fields,
    known private paths) appear anywhere in the tracked tree
  - the shared SKILL.md has valid Agent Skills frontmatter (name, description)
  - host manifests exist at their required paths and are internally consistent
  - the shared SKILL.md encodes the required ticket-content and
    acceptance-criteria-derived native test guidance
  - the plugin manifest version stays in parity across hosts and the
    marketplace entry

Run with --selftest to prove the content and version-parity checks actually
catch mutated/regressed input, not just pass trivially on already-correct
content.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROD_MCP_URL = "https://mcp-tracker.3jtech.app/mcp"

FORBIDDEN_STRINGS = [
    "TRACKER_MCP_URL",
    "staging.3jtech",
    "stage.3jtech",
    "dev.3jtech",
    "test.3jtech",
    "localhost",
    "127.0.0.1",
    "/Users/",
    "/home/",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "bearer ",
    "Authorization",
    "authorization_header",
    "api_key",
    "apiKey",
    "access_token",
    "refresh_token",
    "client_secret",
]

# Substring allow-list: forbidden-string hits inside these exact relative
# paths are ignored (e.g. this validator script's own source, which must
# name the forbidden strings to check for them).
SELF_EXEMPT = {"scripts/validate_plugin.py"}

REQUIRED_JSON_FILES = [
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".mcp.json",
    "plugin.json",
    "mcp_config.json",
]

# Command substrings the README must use (verified against the installed
# host CLIs) and must never regress away from.
REQUIRED_README_COMMANDS = [
    "codex plugin add tracker@tracker-plugin",
    "claude plugin install tracker@tracker-plugin",
    "agy plugin install ./tracker-plugin",
    "agy plugin uninstall tracker",
]

# Command substrings that look plausible but name subcommands/shorthand the
# host CLI does not actually support (verified locally: `agy plugin --help`
# only has list/install/enable/disable/uninstall; `codex plugin add` and
# `claude plugin install` both require a `name@marketplace` selector).
FORBIDDEN_README_COMMANDS = [
    "agy plugin add",
    "agy plugin remove",
    "agy plugin update",
    "codex plugin add tracker\n",
    "codex plugin add tracker ",
    "/plugin install tracker\n",
    "/plugin install tracker ",
]

REQUIRED_SKILL_FILE = "skills/tracker-workflows/SKILL.md"

# Short, natural substrings of the actual SKILL.md prose (not paraphrases) so
# the required ticket-content and acceptance-criteria-derived native test
# guidance stays encoded, not just the file's existence/frontmatter. Keep
# these in sync by hand if the corresponding SKILL.md wording changes.
REQUIRED_TICKET_CONTENT_PHRASES = [
    "Who benefits and why",
    "Out of scope",
    "Given/When/Then",
    "Steps to reproduce",
    "Actual behavior",
    "Environment/version",
    "regression test",
    "verify relevant edge cases",
]

REQUIRED_TEST_DERIVATION_PHRASES = [
    "Deriving native test cases from acceptance criteria",
    "Consolidate criteria that exercise the same behavior",
    "only when the ticket's own content justifies them",
    "flag it back on the ticket",
    "link that plan to the ticket",
    "Test Case or Test Plan as a substitute",
    "not a request to run them",
    "explicit proportionality decision",
    "traceable path to how it gets verified",
]

errors: list[str] = []
warnings: list[str] = []


def iter_tracked_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ROOT).parts
        if ".git" in rel_parts:
            continue
        yield path


def check_json_validity():
    for path in iter_tracked_files():
        if path.suffix != ".json":
            continue
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {exc}")


def check_required_files():
    for rel in REQUIRED_JSON_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")
    if not (ROOT / REQUIRED_SKILL_FILE).exists():
        errors.append(f"missing required file: {REQUIRED_SKILL_FILE}")


def check_prod_url():
    # Every host's companion MCP config must declare the server, and every
    # declaration must use the exact production URL. A file missing here
    # entirely is caught separately by check_required_files().
    mcp_files = [
        ".mcp.json",  # Claude Code + Codex companion, plugin root
        "mcp_config.json",  # Antigravity companion, plugin root
    ]
    found_any = False
    for rel in mcp_files:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text()
        if PROD_MCP_URL not in text:
            errors.append(f"{rel} does not contain the exact production MCP URL {PROD_MCP_URL}")
        else:
            found_any = True
    if not found_any:
        errors.append("no MCP config file contained the production MCP URL")


def check_forbidden_strings():
    for path in iter_tracked_files():
        rel = str(path.relative_to(ROOT))
        if rel in SELF_EXEMPT:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, PermissionError):
            continue
        for needle in FORBIDDEN_STRINGS:
            if needle.lower() in text.lower():
                errors.append(f"forbidden string '{needle}' found in {rel}")


def check_skill_frontmatter():
    path = ROOT / REQUIRED_SKILL_FILE
    if not path.exists():
        return
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        errors.append(f"{REQUIRED_SKILL_FILE}: missing YAML frontmatter block")
        return
    frontmatter = match.group(1)
    if not re.search(r"^name:\s*\S+", frontmatter, re.MULTILINE):
        errors.append(f"{REQUIRED_SKILL_FILE}: frontmatter missing 'name'")
    if not re.search(r"^description:\s*\S+", frontmatter, re.MULTILINE):
        errors.append(f"{REQUIRED_SKILL_FILE}: frontmatter missing 'description'")


def find_missing_skill_phrases(text: str) -> list[str]:
    """Pure so --selftest can exercise it against mutated text."""
    return [
        phrase
        for phrase in REQUIRED_TICKET_CONTENT_PHRASES + REQUIRED_TEST_DERIVATION_PHRASES
        if phrase not in text
    ]


def check_skill_content_guidance():
    path = ROOT / REQUIRED_SKILL_FILE
    if not path.exists():
        return
    for phrase in find_missing_skill_phrases(path.read_text()):
        errors.append(f"{REQUIRED_SKILL_FILE}: missing required guidance phrase {phrase!r}")


def check_codex_manifest_contract():
    # Mirrors the shape rules from openai/codex's own ingestion validator
    # (codex-rs/skills/src/assets/samples/plugin-creator/scripts/validate_plugin.py):
    # `skills` and `mcpServers`, when given as strings, must normalize to
    # exactly "skills" and ".mcp.json" relative to the plugin root (the
    # directory containing .codex-plugin/, i.e. this repo's root) — not a
    # path nested inside .codex-plugin/.
    path = ROOT / ".codex-plugin/plugin.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return

    skills = data.get("skills")
    if skills is not None:
        normalized = Path(skills).as_posix().rstrip("/") if isinstance(skills, str) else None
        if normalized != "skills":
            errors.append(
                f".codex-plugin/plugin.json field 'skills' must resolve to 'skills', got {skills!r}"
            )

    mcp_servers = data.get("mcpServers")
    if isinstance(mcp_servers, str):
        normalized = Path(mcp_servers).as_posix().rstrip("/")
        if normalized != ".mcp.json":
            errors.append(
                f".codex-plugin/plugin.json field 'mcpServers' must resolve to '.mcp.json', got {mcp_servers!r}"
            )
        if not (ROOT / ".mcp.json").exists():
            errors.append(".codex-plugin/plugin.json references .mcp.json but it is missing")
    elif mcp_servers is not None and not isinstance(mcp_servers, dict):
        errors.append(".codex-plugin/plugin.json field 'mcpServers' must be a string path or object")

    interface = data.get("interface")
    if not isinstance(interface, dict):
        errors.append(".codex-plugin/plugin.json is missing the required 'interface' object")
        return
    for field in ("displayName", "shortDescription", "longDescription", "developerName", "category"):
        value = interface.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f".codex-plugin/plugin.json interface.{field} must be a non-empty string")
    capabilities = interface.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        isinstance(v, str) and v.strip() for v in capabilities
    ):
        errors.append(".codex-plugin/plugin.json interface.capabilities must be an array of strings")
    if "defaultPrompt" not in interface and "default_prompt" not in interface:
        errors.append(
            ".codex-plugin/plugin.json interface must set 'defaultPrompt' or 'default_prompt'"
        )


def check_claude_marketplace_wiring():
    # Required for `claude plugin marketplace add <this repo>` /
    # `claude plugin install tracker@tracker-plugin` to work at all —
    # verified locally against a disposable marketplace source.
    plugin_path = ROOT / ".claude-plugin/plugin.json"
    marketplace_path = ROOT / ".claude-plugin/marketplace.json"
    if not plugin_path.exists() or not marketplace_path.exists():
        return
    try:
        plugin_name = json.loads(plugin_path.read_text()).get("name")
        marketplace = json.loads(marketplace_path.read_text())
    except json.JSONDecodeError:
        return
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not any(
        isinstance(p, dict) and p.get("name") == plugin_name and p.get("source") == "."
        for p in plugins
    ):
        errors.append(
            ".claude-plugin/marketplace.json must list a plugin entry with "
            f"name={plugin_name!r} and source='.'"
        )


def check_readme_commands():
    path = ROOT / "README.md"
    if not path.exists():
        return
    text = path.read_text()
    for needle in REQUIRED_README_COMMANDS:
        if needle not in text:
            errors.append(f"README.md is missing the verified command: {needle!r}")
    for needle in FORBIDDEN_README_COMMANDS:
        if needle in text:
            errors.append(f"README.md contains an unsupported/unverified command: {needle!r}")


def versions_mismatched(versions: dict) -> bool:
    """Pure so --selftest can exercise it directly."""
    return len(set(versions.values())) > 1


def _collect_manifest_versions() -> dict:
    codex_path = ROOT / ".codex-plugin/plugin.json"
    claude_path = ROOT / ".claude-plugin/plugin.json"
    antigravity_path = ROOT / "plugin.json"
    marketplace_path = ROOT / ".claude-plugin/marketplace.json"
    versions = {}
    for label, path in (
        ("codex", codex_path),
        ("claude", claude_path),
        ("antigravity", antigravity_path),
    ):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if "version" in data:
            versions[label] = data["version"]
        if "name" in data and data["name"] != "tracker":
            warnings.append(f"{label} manifest name is '{data['name']}', expected 'tracker'")
    if marketplace_path.exists():
        try:
            marketplace = json.loads(marketplace_path.read_text())
        except json.JSONDecodeError:
            marketplace = None
        if isinstance(marketplace, dict):
            for entry in marketplace.get("plugins", []):
                if (
                    isinstance(entry, dict)
                    and entry.get("name") == "tracker"
                    and "version" in entry
                ):
                    versions["marketplace"] = entry["version"]
    return versions


def check_manifest_version_parity():
    versions = _collect_manifest_versions()
    if versions_mismatched(versions):
        errors.append(f"manifest version mismatch across hosts: {versions}")


def selftest() -> int:
    """Realistic behavioral check: prove the new content and version-parity
    checks actually catch a regression, instead of only ever passing on
    already-correct content. Mutates data in memory; never touches disk.
    """
    failures: list[str] = []

    skill_text = (ROOT / REQUIRED_SKILL_FILE).read_text()
    already_missing = find_missing_skill_phrases(skill_text)
    if already_missing:
        failures.append(
            f"selftest precondition failed: the real SKILL.md is already missing {already_missing}"
        )

    for group, phrase in (
        ("ticket content standards", "Given/When/Then"),
        ("native test derivation", "explicit proportionality decision"),
    ):
        if phrase not in skill_text:
            failures.append(f"selftest setup failed: {phrase!r} ({group}) not found in real SKILL.md")
            continue
        mutated = skill_text.replace(phrase, "", 1)
        if phrase not in find_missing_skill_phrases(mutated):
            failures.append(
                f"selftest FAILED: deleting {phrase!r} ({group}) went undetected by "
                "check_skill_content_guidance"
            )

    if versions_mismatched({"codex": "1.0.1", "claude": "1.0.1", "marketplace": "1.0.1"}):
        failures.append("selftest FAILED: matching versions were reported as a mismatch")
    if not versions_mismatched({"codex": "1.0.1", "claude": "1.0.2", "marketplace": "1.0.1"}):
        failures.append("selftest FAILED: a real version mismatch went undetected")

    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}")
        print(f"\n{len(failures)} selftest failure(s).")
        return 1
    print("Selftest passed: content and version-parity checks catch realistic regressions.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()

    check_json_validity()
    check_required_files()
    check_prod_url()
    check_forbidden_strings()
    check_skill_frontmatter()
    check_skill_content_guidance()
    check_codex_manifest_contract()
    check_claude_marketplace_wiring()
    check_readme_commands()
    check_manifest_version_parity()

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        print(f"\n{len(errors)} error(s).")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
