from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import LoadFileAttachment
from openai.types.shared.reasoning import Reasoning
from shared_tools import CopyFile

from config import get_default_model, is_openai_provider


def create_image_generation_agent() -> Agent:
    """Mockup Imagery Agent — supports the Mockup Builder.

    Generates hero images, services tiles, before/after composites, and any
    branded imagery the Mockup Builder needs. Avoids generic AI-looking
    gradients per the article's design rules.
    """
    return Agent(
        name="Mockup Imagery Agent",
        description=(
            "Generates niche-appropriate hero, services, and about-section imagery for "
            "landing-page mockups. Strict ban on generic AI gradients, stock 'happy team' "
            "shots, and 'Welcome to' aesthetics."
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
            "Generate a hero image for a roofers landing page in Phoenix.",
            "Make 3 services-tile illustrations for a cosmetic dentist (whitening, veneers, implants).",
            "Edit this exterior photo of a fence install to look editorial.",
            "Combine these 4 shots into a single before/after social-proof asset.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_image_generation_agent()).terminal_demo()
