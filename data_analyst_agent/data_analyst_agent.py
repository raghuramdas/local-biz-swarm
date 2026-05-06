import os
from agency_swarm import Agent, ModelSettings
from openai.types.shared.reasoning import Reasoning
from agency_swarm.tools import (
    WebSearchTool,
    PersistentShellTool,
    IPythonInterpreter,
    LoadFileAttachment,
)
from shared_tools import CopyFile, ExecuteTool, FindTools, ManageConnections, SearchTools

from config import get_default_model, is_openai_provider

current_dir = os.path.dirname(os.path.abspath(__file__))
instructions_path = os.path.join(current_dir, "instructions.md")


def create_data_analyst() -> Agent:
    """Pipeline Analyst — funnel reporting for the website-selling swarm.

    Folder is named `data_analyst_agent` for upstream-import compatibility.
    Tracks the article's funnel: leads found → contacted → reply rate →
    positive replies → close rate → MRR forecast. Reads the Outreach
    Sender's schedule ledger and the Outreach Strategist's CSV.
    """
    return Agent(
        name="Pipeline Analyst",
        description=(
            "Funnel analytics for the website-selling pipeline. Reads outreach_schedule.json "
            "and outreach_pack.csv, computes reply / positive-reply / close rates, projects MRR "
            "from the article's math (10-15% reply, 30-50% close), and renders charts."
        ),
        instructions=instructions_path,
        tools_folder=os.path.join(current_dir, "tools"),
        model=get_default_model(),
        tools=[
            WebSearchTool(),
            PersistentShellTool,
            IPythonInterpreter,
            LoadFileAttachment,
            CopyFile,
            ExecuteTool,
            FindTools,
            ManageConnections,
            SearchTools,
        ],
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="medium", summary="auto") if is_openai_provider() else None,
            truncation="auto",
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        conversation_starters=[
            "What's my funnel this week — leads → replies → positives → closes?",
            "Forecast MRR if I keep this pace for 6 months.",
            "Which niche has the best reply rate so far? Show a chart.",
            "Compare email vs SMS reply rates across the trades batch.",
        ],
    )
