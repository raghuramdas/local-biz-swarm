from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import WebSearchTool, IPythonInterpreter
from openai.types.shared import Reasoning

from config import get_default_model, is_openai_provider
from .tools.GoogleMapsSearch import GoogleMapsSearch


def create_deep_research() -> Agent:
    """Lead Hunter — local-business prospect discovery on Google Maps.

    Folder is named `deep_research` for upstream-import compatibility, but the
    agent is rebranded to "Lead Hunter" and tuned for the article workflow:
    narrow niche+city queries, skip the top 3-4 dominant results, surface
    established businesses with weak online presence, and emit a structured
    lead list with personalized hooks.
    """
    return Agent(
        name="Lead Hunter",
        description=(
            "Finds local businesses with weak or missing websites that are still earning offline. "
            "Searches Google Maps by narrow niche+city queries, filters for the article's sweet spot "
            "(5+ years, <50 reviews, no website or outdated site), and produces a personalized lead list."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools=[GoogleMapsSearch, WebSearchTool(), IPythonInterpreter],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="high", summary="auto") if is_openai_provider() else None,
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Find 30 cosmetic dentists in West Austin with weak websites.",
            "Hunt 25 roofers in Phoenix who have <50 reviews but solid ratings.",
            "Surface plumbers in Denver where the Google profile has no website link.",
            "Build me a lead list of fence installers in Tampa, sorted by website-gap severity.",
        ],
    )
