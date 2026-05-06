from datetime import datetime, timezone
from pathlib import Path

from agency_swarm import Agent, ModelSettings, Agency
from agency_swarm.tools import IPythonInterpreter, WebSearchTool
from openai.types.shared import Reasoning
from shared_tools import CopyFile

from config import get_default_model, is_openai_provider

_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"


def _list_existing_projects() -> str:
    from .tools.utils.doc_file_utils import get_mnt_dir
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
        f"Existing project folders (do NOT reuse these names for a new outreach run):\n{projects_block}"
    )


def create_docs_agent() -> Agent:
    """Outreach Strategist — Step 2 of the website-selling pipeline.

    Folder is named `docs_agent` for upstream-import compatibility. The agent
    is rebranded to "Outreach Strategist" and produces the article's exact
    three-piece pack per lead (50-word diagnosis, 100-word site brief,
    <70-word cold message), then exports the deliverables as CSV/MD/PDF.
    """
    return Agent(
        name="Outreach Strategist",
        description=(
            "Generates the per-lead 3-piece outreach pack (diagnosis, site brief, cold message). "
            "Reads the Lead Hunter CSV, runs `GenerateOutreachPack` per row, and exports "
            "deliverables as CSV/Markdown/PDF for the Outreach Sender."
        ),
        instructions=_build_instructions(),
        files_folder="./files",
        tools_folder="./tools",
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="medium", summary="auto") if is_openai_provider() else None,
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        tools=[WebSearchTool(), IPythonInterpreter, CopyFile],
        conversation_starters=[
            "Run the 3-piece outreach pack for every lead in this CSV.",
            "Draft me a single cold message for [business name] in [city].",
            "Audit my last batch of cold messages — flag any that sound AI-generated.",
            "Export the diagnosis + site brief deck as a single PDF I can read on my phone.",
        ],
    )


if __name__ == "__main__":
    import contextlib
    import os

    with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
        Agency(create_docs_agent()).terminal_demo()
