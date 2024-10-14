# https://github.com/open-webui/pipelines/blob/main/examples/pipelines/providers/openai_manifold_pipeline.py

from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
from pydantic import BaseModel, Field

import os
import requests


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
                )
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
                    if "gpt" in model["id"] or "o1" in model["id"]
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
        if "o1" in model_id:
            if messages and messages[0].get("role") == "system":
                messages[0]["role"] = "user"
                messages[0]["content"] = (
                    "The following is a general system message. Do not acknowledge this as part of the back and forth conversation, "
                    "but rather just general context.\n\n======Start=====\n"
                    + messages[0]["content"]
                    + "\n=====End====="
                )

        payload = {**body, "model": model_id, "messages": messages}

        if "user" in payload:
            del payload["user"]
        if "chat_id" in payload:
            del payload["chat_id"]
        if "title" in payload:
            del payload["title"]

        try:
            r = requests.post(
                url=f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=body.get("stream", True),
            )

            r.raise_for_status()

            if body.get("stream", False):
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
