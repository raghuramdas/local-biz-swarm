from agency_swarm import Agent, ModelSettings
from openai.types.shared import Reasoning
from dotenv import load_dotenv

from config import get_default_model, is_openai_provider

load_dotenv()


def create_orchestrator() -> Agent:
    return Agent(
        name="Pipeline Orchestrator",
        description=(
            "Routes the local-business website-selling pipeline. Coordinates Lead Hunter, Outreach Strategist, "
            "Mockup Builder, Demo Video Agent, Outreach Sender, and Pipeline Analyst. Never executes work itself."
        ),
        instructions="./instructions.md",
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="medium", summary="auto") if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Find 30 cosmetic dentists in West Austin with weak websites and run the full outreach pipeline.",
            "Build mockups + 10s walkthrough videos for my top 5 leads in the roofers/Phoenix list.",
            "Draft per-lead diagnosis, site brief, and cold message for these 25 plumbers.",
            "Show me the funnel: leads contacted, reply rate, mockups built, deals closed, MRR forecast.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_orchestrator()).terminal_demo()
