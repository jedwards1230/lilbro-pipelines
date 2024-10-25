"""
title: OpenAI Swarm Agent Test Pipeline
author: jedwards1230
date: 2024-10-13
version: 0.0.1
license: MIT
description: A pipeline for testing the OpenAI Swarm Agent functionality.
requirements: git+https://github.com/openai/swarm.git, git+https://github.com/jedwards1230/lilbro-pipelines.git
"""

from typing import List, Union, Generator, Iterator
import os
from swarm import Swarm

from pydantic import BaseModel, Field

from pipelines.lilbro_utils import primary_agent
from pipelines.lilbro_utils.plex import init_plex_client


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
        PLEX_BASE_URL: str = Field(
            default="http://localhost:32400",
            description="The base URL for Plex API endpoints.",
        )
        PLEX_TOKEN: str = Field(
            default="",
            description="Required API key to retrieve the model list.",
        )
        pass

    class UserValves(BaseModel):
        OPENAI_API_KEY: str = Field(
            default="",
            description="Required API key to retrieve the model list.",
        )
        PLEX_BASE_URL: str = Field(
            default="",
            description="The base URL for Plex API endpoints.",
        )
        PLEX_TOKEN: str = Field(
            default="",
            description="Required API key to retrieve the model list.",
        )
        pass

    def __init__(self):
        self.valves = self.Valves(
            **{
                "OPENAI_API_KEY": os.getenv(
                    "OPENAI_API_KEY", "your-openai-api-key-here"
                ),
                "PLEX_BASE_URL": os.getenv("PLEX_BASE_URL", "http://localhost:32400"),
                "PLEX_TOKEN": os.getenv("PLEX_TOKEN", "your-plex-token-here"),
            }
        )
        self.client = Swarm()
        init_plex_client(self.valves.PLEX_BASE_URL, self.valves.PLEX_TOKEN)

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
            agent=primary_agent, messages=messages, stream=body.get("stream", False)
        )

        return response.messages[-1]["content"]
