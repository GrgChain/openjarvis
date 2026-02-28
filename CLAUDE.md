# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**nanobot** (package: `nanobot-ai`) is an ultra-lightweight personal AI assistant framework (~4,000 LOC core) that connects LLMs to 13 chat platforms via a plugin-based architecture for providers, channels, tools, and skills.

## Commands

### Install & Setup
```bash
# Install with uv (preferred)
uv pip install -e .
# With optional skill dependencies
uv pip install -e ".[skills,matrix]"
# Dev dependencies
uv pip install -e ".[dev]"
```

### Run
```bash
nanobot onboard          # Initial setup wizard
nanobot agent            # Interactive CLI chat
nanobot gateway          # Start multi-channel gateway (port 18790)
nanobot status           # Show configuration and channel status
nanobot provider login   # OAuth login (GitHub Copilot, OpenAI Codex)
nanobot cron add/list/remove  # Manage scheduled tasks
nanobot channels login/status # WhatsApp session management
```

### Test
```bash
pytest                              # Run all tests
pytest tests/test_commands.py       # Run specific test file
pytest tests/ -k "test_memory"      # Run tests matching pattern
```

### Lint
```bash
ruff check nanobot/      # Check for linting issues
ruff check --fix nanobot/ # Auto-fix linting issues
```

### Docker
```bash
docker build -t nanobot .
docker compose up        # Starts gateway service
```

## Architecture

### Message Flow
```
Chat Platform → Channel Adapter → MessageBus → Agent Loop → LLM Provider
                                                    ↓
                                             Tool Execution
                                                    ↓
                               Channel Adapter ← MessageBus ← Agent Response
```

### Core Components

**Agent Loop** (`nanobot/agent/loop.py`): Central processing engine. Receives `InboundMessage` from `MessageBus`, builds context via `context.py`, calls LLM, executes tools, publishes `OutboundMessage` back.

**Context Builder** (`nanobot/agent/context.py`): Assembles LLM prompts from identity files (AGENTS.md, SOUL.md, USER.md, TOOLS.md), memory (MEMORY.md, HISTORY.md), and active skills.

**Memory System** (`nanobot/agent/memory.py`): Append-only JSONL session storage for LLM cache efficiency. Supports consolidation/summarization.

**Provider Registry** (`nanobot/providers/registry.py`): Single source of truth for all LLM providers. Each `ProviderSpec` defines: env vars, model prefix, display name, OAuth support. Adding a new provider only requires adding a `ProviderSpec` here and a config field in `nanobot/config/schema.py`.

**Channel Manager** (`nanobot/channels/manager.py`): Loads and manages 13 channel adapters (Telegram, Discord, WhatsApp, Feishu, DingTalk, Slack, Matrix, Email, QQ, Mochat). Each channel inherits `BaseChannel` and publishes to `MessageBus`.

**Skills System** (`nanobot/agent/skills.py`, `nanobot/skills/`): Markdown-based skill definitions with YAML frontmatter. Bundled skills (18+) live in `nanobot/skills/`; workspace overrides in `~/.nanobot/workspace/skills/`.

**Built-in Tools** (`nanobot/agent/tools/`): `shell.py`, `filesystem.py`, `web.py`, `message.py`, `cron.py`, `spawn.py`, `mcp.py`. Registered via `ToolRegistry`.

### Configuration
- Config file: `~/.nanobot/config.json` (Pydantic schema in `nanobot/config/schema.py`)
- Workspace: `~/.nanobot/workspace/` — user identity files, memory, custom skills
- Sessions: `~/.nanobot/sessions/` — per-channel JSONL conversation history

### Extension Patterns

**Add a Provider**: Add `ProviderSpec` to `PROVIDERS` in `nanobot/providers/registry.py`, add config field to `ProvidersConfig` in `nanobot/config/schema.py`.

**Add a Channel**: Create `nanobot/channels/<name>.py` inheriting `BaseChannel`, implement `start()`/`stop()`, publish to `MessageBus`.

**Add a Tool**: Create `nanobot/agent/tools/<name>.py` inheriting `BaseTool`, register in `ToolRegistry`.

**Add a Skill**: Create `nanobot/skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`, `emoji`, `dependencies`). The markdown body teaches the agent how to use the skill.

## Key Technical Details

- Python 3.11+ required; uses `asyncio` throughout
- LLM abstraction via `litellm`; Pydantic v2 for config validation
- WhatsApp uses a Node.js 20 bridge (`bridge/`) via Baileys library, communicating over WebSocket on port 18790
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"` — all async tests auto-discovered
- Ruff configured with 100-char line length, targeting rules E, F, I, N, W (E501 ignored)
- Config and sensitive files default to 0600 permissions
