"""
title: Openai Manifold Pipeline
author: 
date: 2024-08-18 (2024-09-30)
version: 1.0-jedwards1230
license: MIT
description: A pipeline for generating text and processing images using the OpenAI API.
requirements: requests, boto3, openai
url: https://github.com/open-webui/pipelines/blob/main/examples/pipelines/providers/openai_manifold_pipeline.py
environment_variables: OPENAI_API_KEY, OPENAI_API_BASE_URL
"""

import os
import requests

from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from pydantic import BaseModel, Field


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
        DEBUG: bool = Field(
            default=False,
            description="Enable debug mode.",
        )
        pass

    class UserValves(BaseModel):
        OPENAI_API_KEY: str = Field(
            default="",
            description="Required API key to retrieve the model list.",
        )
        pass

    def __init__(self):
        self.type = "manifold"
        self.name = "OpenAI: "

        self.valves = self.Valves(
            **{
                "OPENAI_API_KEY": os.getenv(
                    "OPENAI_API_KEY", "your-openai-api-key-here"
                ),
                "OPENAI_API_BASE_URL": os.getenv(
                    "OPENAI_API_BASE_URL", "https://api.openai.com/v1"
                ),
            }
        )

        self.pipelines = self.get_openai_models()
        pass

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        self.pipelines = self.get_openai_models()
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        # This function is called when the valves are updated.
        print(f"on_valves_updated:{__name__}")
        self.pipelines = self.get_openai_models()
        pass

    def get_openai_models(self):
        if self.valves.OPENAI_API_KEY:
            try:
                headers = {}
                headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
                headers["Content-Type"] = "application/json"

                r = requests.get(
                    f"{self.valves.OPENAI_API_BASE_URL}/models", headers=headers
                )

                models = r.json()
                return [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                    if "gpt" in model["id"]
                    or "o1" in model["id"]
                    or "o3" in model["id"]
                ]

            except Exception as e:
                print(f"Error: {e}")
                return [
                    {
                        "id": "error",
                        "name": "Error fetching OpenAI models: " + str(e),
                    },
                ]
        else:
            return []

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        print(f"pipe:{__name__}")

        headers = {}
        headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
        headers["Content-Type"] = "application/json"

        # https://platform.openai.com/docs/guides/reasoning/beta-limitations
        # Check if "o1" is in the model_id and re-assign system message to user message
        if "o1" in model_id or "o3" in model_id:
            if messages and messages[0].get("role") == "system":
                messages[0]["role"] = "developer"
        # chat_meta = {
        #     "id": body.get("id", None),
        #     "session_id": body.get("session_id", None),
        #     "tool_ids": body.get("tool_ids", []),
        #     "stream_options": body.get("stream_options", {"include_usage": False}),
        # }

        payload = {
            **body,
            "chat_id": body.get("chat_id", None),
            "model": model_id,
            "messages": messages,
            "stream": body.get("stream", False),
        }

        if "user" in payload:
            del payload["user"]
        if "chat_id" in payload:
            del payload["chat_id"]
        if "title" in payload:
            del payload["title"]
        if "max_tokens" in payload:
            payload["max_completion_tokens"] = payload["max_tokens"]
            del payload["max_tokens"]

        try:
            if self.valves.DEBUG:
                print(f"Payload: {payload}")
            r = requests.post(
                url=f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=body.get("stream", False),
            )

            r.raise_for_status()

            if body.get("stream", False):
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            print(
                f"Error: {e}\nHeaders: {headers}\nPayload: {payload}\nResponse: {r.text}"
            )
            return f"Error processing response: {e}"
