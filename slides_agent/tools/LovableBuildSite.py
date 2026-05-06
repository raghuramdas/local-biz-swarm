"""LovableBuildSite — drive lovable.dev with browser-use to ship a real preview.

Lovable.dev has no public API and no MCP, so we drive its UI directly. Pattern:

  1. browser-use Agent (LLM in the loop) handles the variable, account-specific
     parts: log in, click "New Project", paste the prompt, wait for the build to
     converge, and read the preview URL off the page.
  2. Once the preview URL is in hand, plain Playwright takes 5 deterministic
     scroll-position screenshots feedable to the Demo Video Agent.

This split keeps the browser-use cost low (the LLM only handles the squishy
parts) and the screenshots reproducible.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field


PROMPT_TEMPLATE = """Build a landing page for {business_name}, a {category} in {city}.

Audience: {audience}.
Brand feel: {brand_feel}.
Hero focus: {hero_focus}.

Sections in order:
1. Hero with primary CTA
2. Three core services
3. About with credibility positioning
4. Social proof / testimonials placeholder
5. Final CTA section

Design: {palette}, generous whitespace, mobile-first, subtle scroll
animations, no flashy effects.

Tone: {tone}.

Avoid: AI-looking gradients, generic stock photos, "Welcome to" headlines,
"Your trusted partner" copy.
"""


def _build_lovable_prompt(brief: dict) -> str:
    return PROMPT_TEMPLATE.format(
        business_name=brief.get("business_name") or "the business",
        category=brief.get("category") or "local service business",
        city=brief.get("city") or "(unknown city)",
        audience=brief.get("audience") or "local customers searching on mobile",
        brand_feel=brief.get("brand_feel") or "trustworthy, modern, local",
        hero_focus=brief.get("hero_focus") or "clear primary CTA above the fold",
        palette=brief.get("palette") or "specific 3-color palette (not 'modern')",
        tone=brief.get("tone") or "warm, direct, plain-English",
    )


PREVIEW_URL_RE = re.compile(r"https?://[a-z0-9\-]+(?:--[a-z0-9\-]+)?\.lovable\.app[^\s\"']*")


class LovableBuildSite(BaseTool):
    """
    Build a real, hosted landing-page preview on lovable.dev for a local
    business brief, then screenshot 5 sections of the rendered preview.

    Returns JSON with `preview_url` and `screenshots: [paths...]`.

    Requires:
      LOVABLE_EMAIL, LOVABLE_PASSWORD  — your lovable.dev login.
      OPENAI_API_KEY                   — used by browser-use to drive the UI.

    The LLM only drives the variable parts (login, prompt entry, wait-for-build).
    Screenshots are taken deterministically with Playwright off the preview URL.
    """

    business_name: str = Field(..., description="Business name as it should appear on the page.")
    category: Optional[str] = Field(default=None, description="Niche, e.g. 'roofer', 'cosmetic dentist'.")
    city: Optional[str] = Field(default=None, description="City or sub-area.")
    audience: Optional[str] = Field(default=None, description="One-line audience description.")
    brand_feel: Optional[str] = Field(default=None, description="3 specific adjectives.")
    hero_focus: Optional[str] = Field(default=None, description="Hero angle from the strategist's brief.")
    palette: Optional[str] = Field(default=None, description="Specific 3-color palette, not 'modern'.")
    tone: Optional[str] = Field(default=None, description="Industry-specific tone.")
    output_dir: Optional[str] = Field(
        default=None,
        description="Where to write screenshots. Defaults to slides_agent/files/lovable/<slug>/.",
    )
    headless: bool = Field(default=True, description="Run the browser headless. Set False to debug.")
    build_timeout_sec: int = Field(
        default=300,
        ge=60,
        le=900,
        description="Max seconds to wait for Lovable to finish the initial build.",
    )

    def run(self) -> str:
        load_dotenv(override=True)
        email = os.getenv("LOVABLE_EMAIL")
        password = os.getenv("LOVABLE_PASSWORD")
        if not email or not password:
            return json.dumps(
                {
                    "error": "LOVABLE_EMAIL or LOVABLE_PASSWORD not set",
                    "fix": "Add both to .env to use LovableBuildSite.",
                }
            )
        if not os.getenv("OPENAI_API_KEY"):
            return json.dumps(
                {
                    "error": "OPENAI_API_KEY required for browser-use",
                    "fix": "Add OPENAI_API_KEY to .env. browser-use needs an LLM to drive the UI.",
                }
            )

        try:
            from browser_use import Agent as BrowserAgent, Browser, ChatOpenAI
        except ImportError:
            return json.dumps(
                {
                    "error": "browser-use is not installed",
                    "fix": "pip install 'browser-use>=0.2.0'",
                }
            )

        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            return json.dumps(
                {
                    "error": "playwright is not installed",
                    "fix": "pip install playwright && playwright install chromium",
                }
            )

        slug = re.sub(r"[^a-z0-9]+", "-", self.business_name.lower()).strip("-")[:48] or "site"
        out_dir = Path(self.output_dir or f"slides_agent/files/lovable/{slug}-{int(time.time())}")
        out_dir.mkdir(parents=True, exist_ok=True)

        prompt = _build_lovable_prompt(self.dict())
        (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        # Step 1: drive Lovable with browser-use to build the site and surface the preview URL.
        try:
            preview_url = asyncio.run(
                _drive_lovable(
                    prompt=prompt,
                    email=email,
                    password=password,
                    headless=self.headless,
                    build_timeout_sec=self.build_timeout_sec,
                    BrowserAgent=BrowserAgent,
                    Browser=Browser,
                    ChatOpenAI=ChatOpenAI,
                )
            )
        except Exception as e:
            return json.dumps({"error": f"Lovable drive failed: {e}", "out_dir": str(out_dir)})

        if not preview_url:
            return json.dumps(
                {
                    "error": "Could not extract a preview URL from Lovable",
                    "fix": "Re-run with headless=false to watch the flow and check the project state.",
                    "out_dir": str(out_dir),
                }
            )

        (out_dir / "preview_url.txt").write_text(preview_url, encoding="utf-8")

        # Step 2: deterministic screenshots via Playwright.
        try:
            screenshots = _screenshot_sections(preview_url, out_dir)
        except Exception as e:
            return json.dumps(
                {
                    "preview_url": preview_url,
                    "error": f"Screenshot phase failed: {e}",
                    "out_dir": str(out_dir),
                }
            )

        return json.dumps(
            {
                "preview_url": preview_url,
                "screenshots": [str(p) for p in screenshots],
                "out_dir": str(out_dir),
            },
            indent=2,
        )


async def _drive_lovable(
    *,
    prompt: str,
    email: str,
    password: str,
    headless: bool,
    build_timeout_sec: int,
    BrowserAgent,
    Browser,
    ChatOpenAI,
) -> Optional[str]:
    """Use browser-use to log in, submit the prompt, and surface the preview URL."""

    browser = Browser(
        is_local=True,
        headless=headless,
        # Persist the lovable.dev session between runs so we don't re-auth every time.
        user_data_dir=str(Path.home() / ".cache" / "localbizswarm" / "lovable-profile"),
    )

    task = f"""You are operating a real browser to build a landing page on lovable.dev.

GOAL: Submit the BUILD PROMPT below to Lovable and wait until the live preview is fully rendered, then return the preview URL.

STEPS:
1. Navigate to https://lovable.dev. If you see "Log in" / "Sign in", click it and authenticate using the credentials in `sensitive_data` (lovable_email, lovable_password). Solve any "verify you're human" check if it appears.
2. Click "New project" / "Create" / equivalent. If a workspace selection appears, pick the default.
3. In the prompt input, paste the BUILD PROMPT verbatim. Submit it.
4. Wait for Lovable to finish the initial build. Signs of completion: the in-app preview shows a real rendered page with a Hero, Services, About, Social Proof, and CTA section; the build status shows "complete" / no spinner.
5. If Lovable surfaces a "publish" / "live preview" URL in the UI, copy it. Otherwise, look for the URL in the address bar of the embedded preview iframe — Lovable hosted previews look like `https://preview--<project>.lovable.app`.
6. Return the preview URL as your final answer. ONLY the URL, nothing else.

Hard rules:
- Do not click "Publish to production" or any paid action.
- If the build fails or stalls past {build_timeout_sec} seconds, return the literal string "BUILD_FAILED".
- Never log the password to chat.

BUILD PROMPT (paste this verbatim into Lovable's prompt box):
---
{prompt}
---
"""

    agent = BrowserAgent(
        task=task,
        llm=ChatOpenAI(model=os.getenv("BROWSER_USE_MODEL", "gpt-4o")),
        browser=browser,
        sensitive_data={
            "lovable_email": email,
            "lovable_password": password,
        },
        max_failures=3,
        step_timeout=120,
    )

    history = await agent.run()

    # Try to pull the URL out of the agent's final answer.
    final_text = ""
    try:
        final_text = history.final_result() or ""
    except Exception:
        pass

    # If the agent literally returned BUILD_FAILED, propagate.
    if "BUILD_FAILED" in final_text.upper():
        return None

    match = PREVIEW_URL_RE.search(final_text)
    if match:
        return match.group(0)

    # Fallback: scan the entire run history for any matching URL.
    try:
        all_text = json.dumps(history.model_dump() if hasattr(history, "model_dump") else {}, default=str)
        match = PREVIEW_URL_RE.search(all_text)
        if match:
            return match.group(0)
    except Exception:
        pass

    return None


def _screenshot_sections(preview_url: str, out_dir: Path) -> List[Path]:
    """Open the preview URL and capture 5 viewport screenshots at 0/25/50/75/100% scroll."""
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 9:16-friendly viewport. Each screenshot will feed the Demo Video Agent.
        context = browser.new_context(viewport={"width": 1080, "height": 1920})
        page = context.new_page()
        page.goto(preview_url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(2_000)  # let lazy images settle

        total_height = page.evaluate("document.documentElement.scrollHeight")
        viewport_h = 1920

        # Always 5 deterministic positions: hero, services, about, social proof, CTA.
        positions = [0.0, 0.22, 0.45, 0.7, 0.95]
        for i, frac in enumerate(positions, start=1):
            y = max(0, int(total_height * frac) - viewport_h // 2)
            y = min(y, max(0, total_height - viewport_h))
            page.evaluate(f"window.scrollTo({{top: {y}, behavior: 'instant'}})")
            page.wait_for_timeout(600)
            target = out_dir / f"section_{i:02d}.png"
            page.screenshot(path=str(target), full_page=False)
            paths.append(target)

        context.close()
        browser.close()

    return paths


if __name__ == "__main__":
    sample = LovableBuildSite(
        business_name="Bluebonnet Smile Studio",
        category="cosmetic dentist",
        city="West Austin, TX",
        audience="adults in West Austin researching elective cosmetic dentistry on mobile",
        brand_feel="warm, premium, trustworthy",
        hero_focus="clear booking CTA + price-transparency promise",
        palette="cream, deep teal, soft gold",
        tone="warm, plain-English, no clinical jargon",
        headless=False,  # easier to watch on first run
    )
    print(sample.run())
