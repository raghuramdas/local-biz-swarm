<div align="center">

# LocalBizSwarm

**A multi-agent system that sells websites to local businesses, end-to-end.**

</div>

A fork of [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm) reshaped into a single-purpose pipeline that implements [the Google-Maps + Claude + Lovable + Higgsfield workflow](https://x.com/timbidefi/status/2051219084092506144): find local businesses with weak websites, write per-lead diagnoses + briefs + cold messages, build branded landing-page mockups, render 10-second cinematic walkthrough videos, and dispatch the outreach with scheduled follow-ups. Then track the funnel.

```
Lead Hunter ─► Outreach Strategist ─► Mockup Builder ─► Demo Video Agent ─► Outreach Sender
                                                                                  │
                                                                                  ▼
                                                                          Pipeline Analyst
```

Built on [Agency Swarm](https://github.com/VRSEN/agency-swarm).

---

## What you can ask the swarm

Drop one of these into the terminal once you've got the env set up:

- *"Find 30 cosmetic dentists in West Austin with weak websites and run the full outreach pipeline."*
- *"Build mockups + 10-second walkthrough videos for my top 5 leads in the Phoenix roofers list."*
- *"Draft per-lead diagnosis, site brief, and cold message for these 25 plumbers."*
- *"Send the latest outreach batch via Gmail; attach each lead's walkthrough video."*
- *"What's my funnel this week — leads → replies → positives → closes? Forecast 6-month MRR."*

The Pipeline Orchestrator routes; specialists do the work.

---

## The roster

| Agent | Stage | What it does |
|---|---|---|
| **Pipeline Orchestrator** | — | Routes every user request to the right specialist(s). Never executes. |
| **Lead Hunter** | 1 — Discovery | Google Maps Places search, skips dominant top results, filters to the article's "sweet spot" (low reviews, decent rating, weak/no website). Emits a CSV with personalized hooks. |
| **Outreach Strategist** | 2 — Copy | Per-lead 3-piece pack: 50-word diagnosis, 100-word site brief, <70-word cold message. Exports CSV / Markdown / PDF. |
| **Mockup Builder** | 3 — Landing page | Authors a 5-section single-page mockup (Hero, Services, About, Social Proof, Final CTA), generates per-section screenshots. |
| **Mockup Imagery Agent** | 3 (support) | Niche-appropriate hero / services imagery via Gemini, OpenAI image, fal.ai. |
| **Demo Video Agent** | 4 — Walkthrough | 10-second 9:16 cinematic walkthrough from screenshots (Higgsfield-style preset). |
| **Outreach Sender** | 5 — Delivery | Email default (Gmail/Outlook), SMS for trades (Twilio), DMs for visual businesses (Instagram), LinkedIn for B2B. Schedules 4-day and 7-day follow-ups. |
| **Pipeline Analyst** | Reporting | Funnel metrics, reply rate, close rate, and MRR forecast based on the article's math (10–15% reply, 30–50% close). |

---

## Quickstart

```bash
git clone https://github.com/raghuramdas/local-biz-swarm.git
cd local-biz-swarm
cp .env.example .env       # then fill in keys
python swarm.py            # opens the TUI
```

**Required (choose one):**
- `OPENAI_API_KEY` — for GPT-4o copy + Sora video, or
- `ANTHROPIC_API_KEY` — for Claude

**Required for Lead Hunter:**
- `GOOGLE_PLACES_API_KEY` — Places API (New). Without it, Lead Hunter falls back to web search and lead metadata is incomplete.

**Required for Outreach Sender (any subset):**
- `COMPOSIO_API_KEY` + `COMPOSIO_USER_ID` — connect any of `GMAIL`, `OUTLOOK`, `TWILIO`, `INSTAGRAM`, `LINKEDIN`, `SLACK` toolkits at https://composio.dev.

**Optional superpowers:**
- `GOOGLE_API_KEY` — Gemini image gen + Veo video
- `FAL_KEY` — Seedance / advanced video edits
- `OUTREACH_MODEL` — override the model used by `GenerateOutreachPack` (e.g., `gpt-4o-mini`, `claude-sonnet-4-5`)

Tools gracefully degrade when keys are missing — you'll get a clear hint on what to add.

---

## Math, the article version

> Send 30 personalized sequences this weekend. 10–15% reply rate. 3–4 positive replies. 30–50% close rate.
> 1–2 deals per weekend. Two weekends a month = $2,000–$4,000 new MRR. Six months = $12,000–$24,000 monthly recurring.

Pipeline Analyst forecasts both the high and low cases against your real ledger.

---

## Hacking on the swarm

See `AGENTS.md` for the folder ⇄ agent map and the conventions you need before touching `swarm.py` or any agent module. Two new tools were added in this fork:

- `deep_research/tools/GoogleMapsSearch.py`
- `docs_agent/tools/GenerateOutreachPack.py`

Everything else is upstream OpenSwarm, just rebranded for the pipeline. To pull upstream improvements:

```bash
git fetch upstream
git merge upstream/main
```

---

## Credit

Pipeline workflow from [@timbidefi's article](https://x.com/timbidefi/status/2051219084092506144). Multi-agent base from [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm). MIT licensed.
