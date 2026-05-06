"""GenerateOutreachPack — produces the article's three-piece pack per lead.

Per lead, returns:
  1. Diagnosis        (~50 words)
  2. Site Brief       (~100 words)
  3. Cold Message     (<70 words)

Fed by a CSV produced by Lead Hunter (or any structured row of leads). The
strategist agent calls this once per lead, or batches via IPythonInterpreter.

This tool is intentionally a thin wrapper that calls the underlying LLM
through the agency_swarm runtime. It enforces the article's exact prompt
recipe so the output stays on-pattern.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field


# The article's exact prompt, parameterized by the lead's facts.
PROMPT_TEMPLATE = """You are a senior local marketing strategist. For ONE business below, generate three deliverables.

Constraints (non-negotiable):
- No buzzwords, no corporate language, no AI mentions, no "your trusted partner".
- Sound like a real person who opened their Google Maps listing.
- Numbers in word counts are firm; do not exceed.

Business facts:
- Name: {name}
- Category: {category}
- City / Address: {address}
- Phone: {phone}
- Google rating: {rating} ({review_count} reviews)
- Current website: {website}
- Website gap signal: {website_gap}
- Specific hook (something I noticed): {hook}

Produce, in this exact order, with these exact labels:

DIAGNOSIS (~50 words):
What is wrong with their current online presence and what revenue is leaking
because of it. Concrete only — name the symptom and the dollar/customer
consequence.

SITE_BRIEF (~100 words):
Hero angle, the 3 services to highlight, tone that fits the industry, the call
to action that will convert, one design choice that sets them apart from local
competitors.

COLD_MESSAGE (<70 words):
Open with one specific observation about THIS business; reference their actual
service or location; end with a soft ask to see a mockup. No corporate
language. No AI mention.

Return as a JSON object with keys: "diagnosis", "site_brief", "cold_message".
"""


class GenerateOutreachPack(BaseTool):
    """
    Generate the per-lead 3-piece pack: diagnosis, site brief, cold message.

    Pass either a single lead via the structured fields, or pass `lead_json`
    as a JSON string to avoid type-coercion issues in chained tool calls.
    """

    name: Optional[str] = Field(default=None, description="Business name")
    category: Optional[str] = Field(default=None, description="e.g. 'Plumber', 'Cosmetic dentist'")
    address: Optional[str] = Field(default=None, description="Full address or city/neighborhood")
    phone: Optional[str] = Field(default=None, description="Best contact phone")
    rating: Optional[float] = Field(default=None, description="Google rating, e.g. 4.7")
    review_count: Optional[int] = Field(default=None, description="Google review count")
    website: Optional[str] = Field(default=None, description="Current website URL or null")
    website_gap: Optional[bool] = Field(
        default=None, description="True if Lead Hunter flagged a website gap"
    )
    hook: Optional[str] = Field(
        default=None,
        description="Specific human-observed detail (e.g. 'Top review praises 24-hour weekend response').",
    )
    lead_json: Optional[str] = Field(
        default=None,
        description="Optional JSON-serialized single lead. Used as a fallback when the structured fields are inconvenient to pass.",
    )

    def _coalesce_lead(self) -> dict:
        if self.lead_json:
            try:
                data = json.loads(self.lead_json)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {
            "name": self.name,
            "category": self.category,
            "address": self.address,
            "phone": self.phone,
            "rating": self.rating,
            "review_count": self.review_count,
            "website": self.website,
            "website_gap": self.website_gap,
            "hook": self.hook,
        }

    def run(self) -> str:
        load_dotenv(override=True)
        lead = self._coalesce_lead()

        if not lead.get("name"):
            return json.dumps({"error": "Lead is missing required field: name"})

        prompt = PROMPT_TEMPLATE.format(
            name=lead.get("name") or "(unknown)",
            category=lead.get("category") or "(unknown)",
            address=lead.get("address") or "(unknown)",
            phone=lead.get("phone") or "(unknown)",
            rating=lead.get("rating") if lead.get("rating") is not None else "n/a",
            review_count=lead.get("review_count")
            if lead.get("review_count") is not None
            else "n/a",
            website=lead.get("website") or "(none on Google profile)",
            website_gap=lead.get("website_gap") if lead.get("website_gap") is not None else "unknown",
            hook=lead.get("hook") or "(none provided — invent nothing; ask Lead Hunter for one)",
        )

        # Prefer the OpenAI-compatible API the rest of the swarm uses.
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return json.dumps(
                {
                    "error": "No LLM API key set",
                    "fix": "Add OPENAI_API_KEY or ANTHROPIC_API_KEY to .env to use GenerateOutreachPack.",
                    "prompt": prompt,
                }
            )

        try:
            if os.getenv("OPENAI_API_KEY"):
                from openai import OpenAI

                client = OpenAI()
                resp = client.chat.completions.create(
                    model=os.getenv("OUTREACH_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.6,
                )
                content = resp.choices[0].message.content or "{}"
            else:
                import anthropic

                client = anthropic.Anthropic()
                resp = client.messages.create(
                    model=os.getenv("OUTREACH_MODEL", "claude-sonnet-4-5"),
                    max_tokens=900,
                    messages=[{"role": "user", "content": prompt}],
                )
                # Pull text and try to parse JSON out of it.
                content = "".join(b.text for b in resp.content if hasattr(b, "text"))

            try:
                pack = json.loads(content)
            except json.JSONDecodeError:
                pack = {"raw": content}

            return json.dumps(
                {
                    "lead_name": lead.get("name"),
                    "pack": pack,
                },
                indent=2,
            )
        except Exception as e:
            return json.dumps({"error": f"LLM call failed: {e}"})


if __name__ == "__main__":
    sample = GenerateOutreachPack(
        name="Bluebonnet Smile Studio",
        category="Cosmetic dentist",
        address="3401 W 6th St, Austin, TX",
        phone="+1 512 555 0144",
        rating=4.9,
        review_count=37,
        website=None,
        website_gap=True,
        hook="Top review: 'finally a dentist who explains the price before drilling'.",
    )
    print(sample.run())
