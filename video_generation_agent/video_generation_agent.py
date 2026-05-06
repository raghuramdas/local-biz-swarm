from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import LoadFileAttachment
from openai.types.shared.reasoning import Reasoning
from shared_tools import CopyFile

from config import get_default_model, is_openai_provider


def create_video_generation_agent() -> Agent:
    """Demo Video Agent — Step 4 of the website-selling pipeline.

    Folder is named `video_generation_agent` for upstream-import compatibility.
    The agent is rebranded to "Demo Video Agent" and tuned for the article's
    Higgsfield-style preset: a 10-second 9:16 vertical cinematic walkthrough
    of a landing-page mockup, given 3-5 section screenshots.
    """
    return Agent(
        name="Demo Video Agent",
        description=(
            "Turns 3-5 mockup screenshots into a 10-second 9:16 cinematic walkthrough "
            "for cold outreach (Higgsfield-style). Vertical because prospects open "
            "messages on their phone — vertical plays inline like content."
        ),
        instructions="instructions.md",
        tools_folder="./tools",
        tools=[LoadFileAttachment, CopyFile],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(summary="auto", effort="medium") if is_openai_provider() else None,
            truncation="auto",
        ),
        conversation_starters=[
            "Make me a 10-second cinematic walkthrough from these 5 mockup screenshots.",
            "Same video but slower zoom on the hero, hold the testimonials longer.",
            "Render the walkthrough in 9:16 vertical, premium editorial feel.",
            "Batch-render walkthroughs for the top 5 mockups in the project folder.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_video_generation_agent()).terminal_demo()
