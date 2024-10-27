from swarm import Agent

from .plex import fetch_audiobook_and_author_data


def transfer_to_homelab_agent():
    return agent_b


primary_agent = Agent(
    name="Agent A",
    instructions="You are a helpful agent.",
    functions=[transfer_to_homelab_agent],
)

agent_b = Agent(
    name="Agent B",
    instructions="Format all your responses in a 4 tick markdown block, include the `json` header. Do not add anything else.",
    functions=[fetch_audiobook_and_author_data],
)
