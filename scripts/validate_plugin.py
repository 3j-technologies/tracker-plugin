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
    ".codex-plugin/.mcp.json",
    ".claude-plugin/plugin.json",
    ".mcp.json",
    "plugin.json",
    "mcp_config.json",
]

REQUIRED_SKILL_FILE = "skills/tracker-workflows/SKILL.md"

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
        ".mcp.json",  # Claude Code companion, plugin root
        ".codex-plugin/.mcp.json",  # Codex companion, inside .codex-plugin/
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


def check_manifest_version_parity():
    codex_path = ROOT / ".codex-plugin/plugin.json"
    claude_path = ROOT / ".claude-plugin/plugin.json"
    antigravity_path = ROOT / "plugin.json"
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
    distinct = set(versions.values())
    if len(distinct) > 1:
        errors.append(f"manifest version mismatch across hosts: {versions}")


def main() -> int:
    check_json_validity()
    check_required_files()
    check_prod_url()
    check_forbidden_strings()
    check_skill_frontmatter()
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
