from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import IPythonInterpreter, PersistentShellTool, LoadFileAttachment, WebSearchTool
from datetime import datetime, timezone
from openai.types.shared import Reasoning
from pathlib import Path
from virtual_assistant.tools.ReadFile import ReadFile
from shared_tools.CopyFile import CopyFile

from config import get_default_model, is_openai_provider

# Import slide tools (re-used here to author landing-page sections)
from .tools import (
    InsertNewSlides,
    ModifySlide,
    ManageTheme,
    DeleteSlide,
    SlideScreenshot,
    ReadSlide,
    BuildPptxFromHtmlSlides,
    RestoreSnapshot,
    CreatePptxThumbnailGrid,
    CheckSlideCanvasOverflow,
    CheckSlide,
    DownloadImage,
    EnsureRasterImage,
    ImageSearch,
    GenerateImage,
)

_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"


def _list_existing_projects() -> str:
    from .tools.slide_file_utils import get_mnt_dir
    base = get_mnt_dir()
    if not base.exists():
        return "(none)"
    dirs = sorted(d.name for d in base.iterdir() if d.is_dir())
    return "\n".join(f"  - {d}" for d in dirs) if dirs else "(none)"


def _build_instructions() -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    projects_block = _list_existing_projects()
    return (
        f"{body}\n\n"
        f"Current date/time (UTC): {now_utc}\n\n"
        f"Existing project folders (do NOT reuse these names for a new mockup):\n{projects_block}"
    )


def create_slides_agent() -> Agent:
    """Mockup Builder — Step 3 of the website-selling pipeline.

    Folder is named `slides_agent` for upstream-import compatibility. The agent
    is rebranded to "Mockup Builder" and tuned to produce a single-page
    landing-page mockup as a sequence of full-bleed HTML "slides" (Hero,
    3 Core Services, About, Social Proof, Final CTA), then export per-section
    screenshots that the Demo Video Agent will turn into a 9:16 walkthrough.
    """
    return Agent(
        name="Mockup Builder",
        description=(
            "Builds a single-page landing-page mockup for a local business. "
            "Each section is authored as a full-bleed HTML 'slide' (Hero, Services, About, "
            "Social Proof, Final CTA). Exports the live preview HTML, a PDF/PPTX-equivalent, "
            "and 5 section screenshots feedable to the Demo Video Agent."
        ),
        instructions=_build_instructions(),
        tools=[
            InsertNewSlides,
            ModifySlide,
            ManageTheme,
            DeleteSlide,
            SlideScreenshot,
            ReadSlide,
            BuildPptxFromHtmlSlides,
            RestoreSnapshot,
            CreatePptxThumbnailGrid,
            CheckSlideCanvasOverflow,
            CheckSlide,
            DownloadImage,
            EnsureRasterImage,
            GenerateImage,
            ImageSearch,
            IPythonInterpreter,
            PersistentShellTool,
            LoadFileAttachment,
            CopyFile,
            ReadFile,
            WebSearchTool(search_context_size="high"),
        ],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="high", summary="auto") if is_openai_provider() else None,
            verbosity="medium" if is_openai_provider() else None,
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Build a mockup for [business name] from this site brief.",
            "Top 5 leads from the CSV — build mockups for all of them in parallel.",
            "Polish the hero on the existing mockup; the headline still feels generic.",
            "Export 5 section screenshots from the latest mockup for the Demo Video Agent.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_slides_agent()).terminal_demo(reload=False)
