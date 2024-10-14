"""
title: OpenAI Swarm Agent Test Pipeline
author: jedwards1230
date: 2024-10-13
version: 0.0.1
license: MIT
description: A pipeline for testing the OpenAI Swarm Agent functionality.
requirements: git+https://github.com/openai/swarm.git
"""

from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
import os

from pydantic import BaseModel, Field
from swarm import Swarm, Agent


def transfer_to_agent_b():
    return agent_b


agent_a = Agent(
    name="Agent A",
    instructions="You are a helpful agent.",
    functions=[transfer_to_agent_b],
)

agent_b = Agent(
    name="Agent B",
    instructions="Only speak in Haikus.",
)


class Pipeline:
    class Valves(BaseModel):
        OPENAI_API_BASE_URL: str = Field(
            default="https://api.openai.com/v1",
            description="The base URL for OpenAI API endpoints.",
        )
        OPENAI_API_KEY: str = Field(
            default="",
            description="Required API key to retrieve the model list.",
        )

    def __init__(self):
        self.valves = self.Valves(
            **{
                "OPENAI_API_KEY": os.getenv(
                    "OPENAI_API_KEY", "your-openai-api-key-here"
                )
            }
        )
        self.client = Swarm()

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        response = self.client.run(
            agent=agent_a, messages=messages, stream=body["stream"]
        )

        return response.messages[-1]["content"]
