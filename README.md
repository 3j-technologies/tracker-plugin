# Tracker Plugin

The official agent plugin for [3J Tracker](https://3jtech.app), an AI-native issue and roadmap tracker. It connects Codex, Claude Code, and Google Antigravity to Tracker's MCP server and adds a shared skill that teaches the agent how to use Tracker safely (identity-first reads, duplicate-safe creation, native test management, exact-head merge gates).

This plugin only ever talks to Tracker's production MCP endpoint:

```
https://mcp-tracker.3jtech.app/mcp
```

There is no configuration flag or environment variable to point it elsewhere, and it carries no embedded credentials. Every host authenticates with its own native MCP OAuth flow — you sign in through your browser the first time you use a Tracker tool, and the host manages your session from then on.

## Supported hosts

| Host | Manifest | MCP config |
|---|---|---|
| [Codex CLI](https://developers.openai.com/codex) | `.codex-plugin/plugin.json` | `.codex-plugin/.mcp.json` |
| [Claude Code](https://code.claude.com) | `.claude-plugin/plugin.json` | `.mcp.json` |
| [Google Antigravity](https://antigravity.google) | `plugin.json` | `mcp_config.json` |

All three hosts also load the shared skill at `skills/tracker-workflows/SKILL.md`, written to the open [Agent Skills](https://agentskills.io) standard.

## Installation

### Codex CLI

```
codex plugin marketplace add 3j-technologies/tracker-plugin
codex plugin add tracker
```

### Claude Code

```
/plugin marketplace add 3j-technologies/tracker-plugin
/plugin install tracker
```

Or, without a marketplace, point Claude Code directly at this repository from `/plugin install` when prompted for a source.

### Google Antigravity

```
agy plugin add 3j-technologies/tracker-plugin
```

Or clone this repository into your Antigravity plugins directory and restart the agent so it picks up `plugin.json`.

## Authentication

The first time you use a Tracker tool, your host will open a browser window for you to sign in to your 3J Tracker workspace. This is the host's own native MCP OAuth flow — the plugin does not ask for, store, or transmit any API key, session credential, or password, and there is no plugin setting for a custom server address. If your host ever asks you to paste a credential instead of opening a browser, stop and check that you're installing from this repository.

## Usage

Once installed and signed in, just ask your agent to work with Tracker in natural language, for example:

- "What's the status of TRK-2416?"
- "Create a roadmap for the Q3 onboarding rework."
- "Run the test plan for the attachments feature and record the results."

The bundled skill (`skills/tracker-workflows/SKILL.md`) guides the agent to resolve your identity and workspace vocabulary first, avoid creating duplicate tickets, use Tracker's native test management instead of ad-hoc ticket types, and treat destructive actions (deletes, bulk mutations, irreversible transitions) as requiring your explicit confirmation.

## Updating

- **Codex CLI**: `codex plugin marketplace update 3j-technologies/tracker-plugin` (or re-run `codex plugin add tracker` to pull the latest version).
- **Claude Code**: `/plugin update tracker`.
- **Antigravity**: `agy plugin update 3j-technologies/tracker-plugin`, or `git pull` if you installed by cloning.

## Uninstalling

- **Codex CLI**: `codex plugin remove tracker`.
- **Claude Code**: `/plugin uninstall tracker`.
- **Antigravity**: `agy plugin remove 3j-technologies/tracker-plugin`, or remove the cloned directory from your plugins folder.

Uninstalling removes the plugin's manifests and skill from your host; it does not affect your Tracker workspace or any data in it. To revoke the OAuth grant itself, do so from your 3J Tracker account's connected-apps settings.

## Validation

`scripts/validate_plugin.py` is a deterministic, dependency-free check that every JSON file in this repository parses, that every host's MCP config points at the exact production URL above, that no forbidden strings (non-production hosts, local paths, auth headers, tokens, API keys) appear anywhere in the tree, and that the shared skill has valid frontmatter:

```
python3 scripts/validate_plugin.py
```

## License

MIT — see [LICENSE](LICENSE).
