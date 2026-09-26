from app.atlas_agents import ATLAS_AGENT_INSTRUCTIONS, build_atlas_agent


def test_openai_agents_sdk_builds_atlas_agent_without_api_call():
    agent = build_atlas_agent()

    assert agent.name == "ATLAS Intelligence"
    assert agent.instructions == ATLAS_AGENT_INSTRUCTIONS
    assert "Do not place, submit, or modify broker orders." in ATLAS_AGENT_INSTRUCTIONS
