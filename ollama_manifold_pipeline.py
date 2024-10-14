from typing import List, Union, Generator, Iterator
from schemas import OpenAIChatMessage
import os

from pydantic import BaseModel, Field
import requests


class Pipeline:

    class Valves(BaseModel):
        OLLAMA_BASE_URL: str = Field(
            default="",
            description="The base URL for Ollama API endpoints.",
        )
        pass

    def __init__(self):
        self.type = "manifold"
        self.name = "Ollama: "

        self.valves = self.Valves(
            **{
                "OLLAMA_BASE_URL": os.getenv(
                    "OLLAMA_BASE_URL", "http://localhost:11435"
                ),
            }
        )
        self.pipelines = []
        pass

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        self.pipelines = self.get_ollama_models()
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        # This function is called when the valves are updated.
        print(f"on_valves_updated:{__name__}")
        self.pipelines = self.get_ollama_models()
        pass

    def get_ollama_models(self):
        if self.valves.OLLAMA_BASE_URL:
            try:
                r = requests.get(f"{self.valves.OLLAMA_BASE_URL}/api/tags")
                models = r.json()
                return [
                    {"id": model["model"], "name": model["name"]}
                    for model in models["models"]
                ]
            except Exception as e:
                print(f"Error: {e}")
                return [
                    {
                        "id": "error",
                        "name": "Could not fetch models from Ollama, please update the URL in the valves.",
                    },
                ]
        else:
            return []

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        if "user" in body:
            print("######################################")
            print(f'# User: {body["user"]["name"]} ({body["user"]["id"]})')
            print(f"# Message: {user_message}")
            print("######################################")

        try:
            r = requests.post(
                url=f"{self.valves.OLLAMA_BASE_URL}/v1/chat/completions",
                json={**body, "model": model_id},
                stream=body.get("stream", False),
            )

            r.raise_for_status()

            if body.get("stream", False):
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
