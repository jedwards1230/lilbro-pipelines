"""
title: Lilbro Book Search
author: jedwards1230
author_url: https://github.com/jedwards1230
funding_url: https://github.com/jedwards1230
description: RAG for lilbro books.
version: 0.1.0
"""

import json
import requests
import typing
import urllib.parse

from pydantic import BaseModel, Field
from typing import Callable, Awaitable


async def query(
    query_string: str,
    base_url: str,
    __event_emitter__: typing.Callable[[dict], typing.Any] = None,
) -> str:
    try:
        params = {"q": query_string, "p": "0", "k": "5"}
        result_url = f"{base_url}/search?{urllib.parse.urlencode(params)}"
        print(f"Querying: {result_url}")

        res = requests.get(result_url, timeout=10)
        res.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)

        res_json = res.json()

        if "results" in res_json:
            for idx, result in enumerate(res_json["results"], 1):
                chunk = json.dumps(result, indent=2)
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {"content": chunk},
                        }
                    )

        # return json.dumps(res_json)

    except requests.exceptions.Timeout:
        raise Exception("Request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making request: {e}")
    except ValueError as e:
        raise Exception(f"Error parsing JSON response: {e}")


class Tools:
    class Valves(BaseModel):
        LIL_WHISPER_ENDPOINT: str = Field(
            default="http://lilbro.local:8480",
            description="The base URL for the lil-whisper API endpoint.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def perform_query(
        self,
        query_string: str,
        __event_emitter__: typing.Callable[[dict], typing.Any] = None,
    ) -> str:
        """
        Query Lilbro for book snippets.
        :param query_string: The query string to search for
        :return: A JSON string containing book citations and quotes
        """
        print(f"Querying Lilbro for: {query_string}")

        await query(query_string, self.valves.LIL_WHISPER_ENDPOINT, __event_emitter__)

        # print(f"Response: {res}")

        # return res


# test
async def main():
    try:
        tools = Tools()
        await tools.perform_query("The Great Gatsby")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
