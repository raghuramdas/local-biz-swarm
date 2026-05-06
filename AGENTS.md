# LocalBizSwarm — Customization Guide

This file is for coding agents (Cursor, Claude Code, Codex, etc.) hacking on this fork. Read it before making any structural change.

---

## What is LocalBizSwarm?

LocalBizSwarm is a fork of [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm) reshaped into a single-purpose pipeline: **selling websites to local businesses**. It implements the workflow described in [the article](https://x.com/timbidefi/status/2051219084092506144):

```
Lead Hunter ─► Outreach Strategist ─► Mockup Builder ─► Demo Video Agent ─► Outreach Sender
                                                                                  │
                                                                                  ▼
                                                                          Pipeline Analyst
```

Each stage corresponds to one Agency Swarm specialist. The Pipeline Orchestrator never executes work — it only routes.

---

## Folder ⇄ Agent map

The folder names are kept from upstream OpenSwarm so all upstream imports keep working. The agent name (and its instructions/tools) is what changed.

| Folder | Agent name | Stage | Article tool it replaces |
|---|---|---|---|
| `orchestrator/` | Pipeline Orchestrator | — | (router only) |
| `deep_research/` | **Lead Hunter** | 1 — Discovery | Google Maps |
| `docs_agent/` | **Outreach Strategist** | 2 — Copy | Claude prompt batch |
| `slides_agent/` | **Mockup Builder** | 3 — Landing page | Lovable |
| `image_generation_agent/` | **Mockup Imagery Agent** | 3 (support) | Image gen |
| `video_generation_agent/` | **Demo Video Agent** | 4 — Walkthrough | Higgsfield |
| `virtual_assistant/` | **Outreach Sender** | 5 — Send + follow up | Gmail / SMS / DMs (Composio) |
| `data_analyst_agent/` | **Pipeline Analyst** | Reporting | (funnel math) |

Communication topology in `swarm.py` is **orchestrator-to-all** + **handoffs between any two specialists**.

---

## New tools added in this fork

Two focused tools were added (everything else is inherited from upstream OpenSwarm):

- `deep_research/tools/GoogleMapsSearch.py` — calls Google Places API (New) Text Search, skips the dominant top results, and filters to the article's "sweet spot" pattern (low reviews, decent rating, missing or weak website). Requires `GOOGLE_PLACES_API_KEY`.
- `docs_agent/tools/GenerateOutreachPack.py` — produces the article's exact 3-piece pack per lead (50-word diagnosis, 100-word site brief, <70-word cold message). Uses `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (`OUTREACH_MODEL` to override).

Everything else (HTML→DOCX/PDF for the strategist, slide-authoring for the mockup, Veo/Sora/Seedance for video, Composio Gmail/Twilio/etc. for sending) is the upstream toolset, just rebranded for the pipeline.

---

## How to customize further

You can keep extending or pivoting this fork. The two most common moves:

1. **Swap a stage to a real first-party API.** For example, integrate Lovable's API in `slides_agent/tools/` to host a real preview URL instead of a local PPTX export. Drop the new tool into the agent's `tools/` folder — it's auto-loaded.
2. **Add a CRM stage.** Drop in a `pipeline_crm/` folder with a tool that writes leads to HubSpot/Pipedrive via Composio, then add the agent to `swarm.py` and `shared_instructions.md`.

If you want to revert to the generic OpenSwarm base, the upstream remote is `git@github.com:VRSEN/OpenSwarm.git`. Cherry-pick from `main` of that repo.

---

## Key conventions

- Each agent folder has one `<name>.py` factory and one `instructions.md` (the system prompt).
- Tools live in `tools/` and are auto-loaded by the agent's `tools_folder=...` definition.
- `shared_tools/` contains Composio-powered integrations (Gmail, Slack, GitHub, etc.) available to all agents.
- Models are configured via `DEFAULT_MODEL` in `.env` — never hardcoded. The Outreach Strategist's pack-generation can be overridden via `OUTREACH_MODEL`.
- Never reference Claude / Lovable / Higgsfield / "AI" in any visible mockup or outreach copy.

Before structural changes, please read:

- `.cursor/rules/agency-swarm-workflow.mdc` — primary guide for agents and agencies
- `.cursor/commands/add-mcp.md` — adding MCP servers
- `.cursor/commands/write-instructions.md` — how to write effective instructions for AI agents
