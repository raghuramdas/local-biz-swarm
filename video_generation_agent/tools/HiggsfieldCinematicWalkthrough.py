"""HiggsfieldCinematicWalkthrough — Step 4 of the pipeline.

Takes 3-5 mockup screenshots from the Mockup Builder and renders a
~10-second 9:16 cinematic walkthrough on Higgsfield's official platform
(`platform.higgsfield.ai`) using the DoP image-to-video model.

Strategy:
  - For each adjacent pair of screenshots, submit ONE Higgsfield DoP job
    (start_image -> end_image, ~2.5s each) with a Higgsfield-style camera
    movement prompt (slow zoom, smooth pan, gentle ease, soft fade).
  - Poll all jobs in parallel via the official `higgsfield_client.subscribe`.
  - Concatenate the resulting clips with moviepy into the final ~10s video.

Auth:
  Set HF_KEY=KEY_ID:KEY_SECRET, or HF_API_KEY + HF_API_SECRET in .env.
  Get credentials from https://cloud.higgsfield.ai → API.

If you'd rather use the official Higgsfield MCP (https://mcp.higgsfield.ai/mcp)
instead of this tool, add it to your MCP-aware client (Claude Code, Cursor)
and the Demo Video Agent will see it as a regular tool. This BaseTool exists
so the swarm works fully self-contained without an external MCP client.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field


# Higgsfield's DoP model returns ~5s clips by default; pairing 4 screenshots
# (Hero->Services->About->Social Proof->CTA) gives 4 clips ~= 20s. We trim
# each to ~2.5s and concatenate into a 10s walkthrough.
DOP_APPLICATION = "/v1/image2video/dop"

DOP_PROMPT = (
    "Cinematic camera move from start frame to end frame: slow editorial "
    "drift forward with a soft hold, gentle parallax, premium grade, "
    "shallow depth of field, no flashy effects, no text overlays, "
    "9:16 vertical."
)


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "walkthrough"


def _file_to_data_uri(path: Path) -> str:
    """DoP accepts image_url; data: URIs work for local files."""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _submit_pair(client_module, start_path: Path, end_path: Path, model: str) -> dict:
    """Submit one image-to-video job; returns the result dict (waits for completion)."""
    arguments = {
        "model": model,
        "prompt": DOP_PROMPT,
        "input_images": [
            {"type": "image_url", "image_url": _file_to_data_uri(start_path)},
            {"type": "image_url", "image_url": _file_to_data_uri(end_path)},
        ],
    }
    return client_module.subscribe(DOP_APPLICATION, arguments)


def _download(url: str, dest: Path) -> Path:
    import httpx

    with httpx.stream("GET", url, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return dest


def _concat_to_target(clips: List[Path], target_seconds: float, out_path: Path) -> Path:
    """Concatenate clips, trimming each to (target_seconds / N) for an even pace."""
    from moviepy.editor import VideoFileClip, concatenate_videoclips

    n = len(clips)
    per_clip = max(0.8, target_seconds / max(n, 1))
    sub_clips = []
    try:
        for c in clips:
            v = VideoFileClip(str(c))
            sub = v.subclip(0, min(per_clip, v.duration))
            sub_clips.append(sub)
        final = concatenate_videoclips(sub_clips, method="compose")
        final.write_videofile(
            str(out_path),
            codec="libx264",
            audio=False,
            fps=30,
            verbose=False,
            logger=None,
        )
        return out_path
    finally:
        for c in sub_clips:
            try:
                c.close()
            except Exception:
                pass


class HiggsfieldCinematicWalkthrough(BaseTool):
    """
    Render a 10-second 9:16 cinematic walkthrough from 3-5 landing-page
    screenshots using Higgsfield DoP (image-to-video).

    Inputs:
      - `screenshots_dir`: folder holding the screenshots produced by the
        Mockup Builder (LovableBuildSite or SlideScreenshot). Files are
        consumed in lexicographic order; supply 3-5 PNGs.
      - `target_seconds`: total runtime; default 10.

    Returns JSON: {video_path, source_clips: [...], preview_seconds}.

    Requires `HF_KEY` (or `HF_API_KEY` + `HF_API_SECRET`) in .env.
    """

    screenshots_dir: str = Field(..., description="Folder holding 3-5 mockup screenshots.")
    business_name: Optional[str] = Field(default=None, description="Used in output filename.")
    target_seconds: float = Field(default=10.0, ge=4.0, le=20.0)
    model: str = Field(
        default="dop-turbo",
        description="Higgsfield DoP model variant: dop-lite, dop-turbo (default), or dop-preview.",
    )
    output_dir: Optional[str] = Field(
        default=None,
        description="Where to write the final MP4 + intermediate clips. Defaults to <screenshots_dir>/walkthrough/.",
    )

    def run(self) -> str:
        load_dotenv(override=True)

        try:
            import higgsfield_client as hf
        except ImportError:
            return json.dumps(
                {
                    "error": "higgsfield-client is not installed",
                    "fix": "pip install higgsfield-client",
                }
            )

        if not (os.getenv("HF_KEY") or (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET"))):
            return json.dumps(
                {
                    "error": "Higgsfield credentials not set",
                    "fix": (
                        "Set HF_KEY=KEY_ID:KEY_SECRET in .env (or HF_API_KEY + "
                        "HF_API_SECRET). Get yours at https://cloud.higgsfield.ai → API."
                    ),
                }
            )

        shots_dir = Path(self.screenshots_dir).expanduser()
        if not shots_dir.is_dir():
            return json.dumps({"error": f"screenshots_dir not found: {shots_dir}"})

        shots = sorted([p for p in shots_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")])
        if len(shots) < 2:
            return json.dumps(
                {
                    "error": f"need 2+ screenshots in {shots_dir}, found {len(shots)}",
                    "tip": "Use the Mockup Builder's SlideScreenshot or LovableBuildSite first.",
                }
            )

        out_dir = Path(self.output_dir or (shots_dir / "walkthrough"))
        out_dir.mkdir(parents=True, exist_ok=True)
        clips_dir = out_dir / "clips"
        clips_dir.mkdir(exist_ok=True)

        pairs = list(zip(shots[:-1], shots[1:]))

        # Submit pairs in parallel — the SDK's subscribe() blocks per call,
        # so a small thread pool gives us concurrent polling.
        results: List[dict] = [None] * len(pairs)  # type: ignore[list-item]
        errors: List[str] = []

        def _runner(idx, pair):
            try:
                results[idx] = _submit_pair(hf, pair[0], pair[1], self.model)
            except Exception as e:
                errors.append(f"pair {idx}: {e}")

        with ThreadPoolExecutor(max_workers=min(len(pairs), 4)) as pool:
            list(pool.map(lambda i_p: _runner(*i_p), enumerate(pairs)))

        if errors:
            return json.dumps({"error": "Some Higgsfield jobs failed", "details": errors})

        # Pull video URLs and download.
        clip_paths: List[Path] = []
        for i, res in enumerate(results):
            if not res:
                continue
            video = res.get("video") or {}
            url = video.get("url") or (res.get("videos") or [{}])[0].get("url")
            if not url:
                errors.append(f"pair {i}: no video url in response")
                continue
            dest = clips_dir / f"clip_{i:02d}.mp4"
            try:
                _download(url, dest)
                clip_paths.append(dest)
            except Exception as e:
                errors.append(f"download pair {i}: {e}")

        if errors:
            return json.dumps({"error": "Higgsfield clip download failed", "details": errors})

        slug = _slugify(self.business_name or shots_dir.name)
        final_path = out_dir / f"{slug}-walkthrough-{int(time.time())}.mp4"
        try:
            _concat_to_target(clip_paths, self.target_seconds, final_path)
        except Exception as e:
            return json.dumps({"error": f"Concatenation failed: {e}", "clips": [str(p) for p in clip_paths]})

        return json.dumps(
            {
                "video_path": str(final_path),
                "source_clips": [str(p) for p in clip_paths],
                "preview_seconds": self.target_seconds,
                "model": self.model,
            },
            indent=2,
        )


if __name__ == "__main__":
    sample = HiggsfieldCinematicWalkthrough(
        screenshots_dir="slides_agent/files/lovable/example/",
        business_name="Bluebonnet Smile Studio",
    )
    print(sample.run())
