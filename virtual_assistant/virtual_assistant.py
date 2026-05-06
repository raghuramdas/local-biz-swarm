from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import (
    WebSearchTool,
    PersistentShellTool,
    IPythonInterpreter,
)
from openai.types.shared import Reasoning
from dotenv import load_dotenv

from config import get_default_model, is_openai_provider
from shared_tools import CopyFile, ExecuteTool, FindTools, ManageConnections, SearchTools

load_dotenv()

# Class-level rename — idempotent, safe to run once at import time.
IPythonInterpreter.__name__ = "ProgrammaticToolCalling"


def create_virtual_assistant() -> Agent:
    """Outreach Sender — Step 5 of the website-selling pipeline.

    Folder is named `virtual_assistant` for upstream-import compatibility.
    The agent is rebranded to "Outreach Sender" and tuned to dispatch the
    Outreach Strategist's pack via Composio (Gmail/Outlook for email,
    Twilio for SMS, Instagram/LinkedIn DMs, Slack for internal handoff)
    with article-grade subject lines and follow-up scheduling.
    """
    return Agent(
        name="Outreach Sender",
        description=(
            "Sends the cold outreach pack (cold message + mockup link + walkthrough video) "
            "via the right channel per niche: email default, SMS for trades, Instagram for "
            "visual businesses, LinkedIn for B2B, phone for older demographics. Schedules "
            "two follow-ups per the article (4-day, then 7-day from a different angle)."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools_folder="./tools",
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="medium", summary="auto") if is_openai_provider() else None,
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        tools=[
            WebSearchTool(),
            PersistentShellTool,
            IPythonInterpreter,
            CopyFile,
            ExecuteTool,
            FindTools,
            ManageConnections,
            SearchTools,
        ],
        conversation_starters=[
            "Send the latest outreach batch via Gmail; attach each lead's walkthrough video.",
            "Schedule a 4-day follow-up for everyone in this batch who hasn't replied.",
            "Switch the channel for the trades leads from email to SMS.",
            "Show me which connected systems I can use to send (Composio).",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_virtual_assistant()).terminal_demo()
