"""
title: Plex API
author: jedwards1230
author_url: https://github.com/jedwards1230/pipelines
funding_url: https://github.com/jedwards1230/pipelines
description: These tools can call the Plex API to query the Plex server for metadata about authors and audiobooks.
version: 0.2.0
"""

import asyncio
import inspect
import os
import sys
import typing
import requests
import urllib.parse
from datetime import datetime

from pydantic import BaseModel, Field
from typing import Callable, Awaitable
import requests
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


BASE_URL = ""
TOKEN = ""


def init_plex_client(base_url: str, token: str) -> None:
    global BASE_URL, TOKEN
    BASE_URL = base_url
    TOKEN = token


def fetcher(url: str, opts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {"Accept": "application/json"}
    if opts and "headers" in opts:
        headers.update(opts["headers"])

    response = requests.get(f"{BASE_URL}{url}/?X-Plex-Token={TOKEN}", headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} {response.text}")
    return response.json()


def get_libraries() -> Dict[str, Any]:
    return fetcher("/library/sections")


def get_library_items(section_id: str, tag: str = "all") -> Dict[str, Any]:
    return fetcher(f"/library/sections/{section_id}/{tag}")


def get_library_item_metadata(rating_key: str) -> Dict[str, Any]:
    return fetcher(f"/library/metadata/{rating_key}")


def get_library_item_children_metadata(rating_key: str) -> Dict[str, Any]:
    return fetcher(f"/library/metadata/{rating_key}/children")


@dataclass
class TagData:
    id: int
    filter: str
    tag: str


@dataclass
class AuthorMetadata:
    title: str
    ratingKey: str
    key: str
    guid: str
    type: str
    summary: str
    thumb: str = ""
    index: Optional[int] = None
    viewCount: Optional[int] = None
    lastViewedAt: Optional[int] = None
    addedAt: Optional[int] = None
    updatedAt: int = 0
    Country: Optional[Any] = None
    Location: List[Dict[str, str]] = field(default_factory=list)
    Genre: Optional[List[TagData]] = None
    Similar: Optional[List[TagData]] = None
    titleSort: Optional[str] = None
    Image: Optional[Any] = None
    UltraBlurColors: Optional[Any] = None
    skipCount: Optional[int] = None
    art: Optional[str] = None


@dataclass
class ExpandedAuthorMetadata(AuthorMetadata):
    librarySectionTitle: str = ""
    librarySectionID: str = ""
    librarySectionKey: str = ""


@dataclass
class AuthorChildrenMetadata:
    ratingKey: str
    key: str
    parentRatingKey: str
    guid: str
    parentGuid: str
    type: str
    title: str
    parentKey: str
    parentTitle: str
    summary: str
    index: int
    year: int
    thumb: str = ""
    originallyAvailableAt: str = ""
    addedAt: int = 0
    updatedAt: int = 0
    loudnessAnalysisVersion: int = 0
    musicAnalysisVersion: int = 0
    Genre: List[TagData] = field(default_factory=list)


@dataclass
class AudiobookMetadata(AuthorChildrenMetadata):
    leafCount: int = 0
    allowSync: bool = True
    librarySectionID: int = 0
    librarySectionTitle: str = ""
    librarySectionUUID: str = ""
    lastViewedAt: int = 0
    Media: Optional[List[Any]] = None
    studio: Optional[str] = None
    rating: Optional[str] = None
    viewCount: Optional[int] = None
    parentThumb: Optional[str] = None
    Image: Optional[str] = None
    UltraBlurColors: Optional[Any] = None
    skipCount: Optional[int] = None
    art: Optional[str] = None
    titleSort: Optional[str] = None


@dataclass
class CompiledData:
    title: str
    author: str
    ratingKey: str
    authorRatingKey: str
    year: int
    lastViewedAt: Optional[str]
    viewCount: Optional[int]
    genres: Optional[str]


class PlexClient:
    """Plex Client to interact with Audiobook Library"""

    debug = False

    @staticmethod
    async def get_audiobook_library_metadata(
        event_emitter: typing.Callable[[dict], typing.Any] = None
    ) -> Dict[str, Any]:
        emitter = EventEmitter(event_emitter, debug=PlexClient.debug)
        await emitter.status("Getting Audiobook Library Metadata...")
        try:
            libraries = get_libraries()
            lib = next(
                (
                    d
                    for d in libraries["MediaContainer"]["Directory"]
                    if d["title"] == "Audiobooks"
                ),
                None,
            )
            if not lib:
                raise Exception("No audiobook library found")
            # await emitter.citation(json.dumps(lib), {"type": "library"}, "plex")
            await emitter.clear_status()
            return lib
        except Exception as e:
            await emitter.fail(f"Error fetching audiobook library: {str(e)}")
            raise

    @staticmethod
    async def get_all_author_metadata(
        __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> List[AuthorMetadata]:
        library = await PlexClient.get_audiobook_library_metadata(
            event_emitter=__event_emitter__
        )
        metadata = get_library_items(library["key"])["MediaContainer"].get(
            "Metadata", []
        )
        if not metadata:
            raise Exception("No metadata found")
        return [AuthorMetadata(**item) for item in metadata]

    @staticmethod
    async def get_all_books_metadata(
        __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> List[AudiobookMetadata]:
        library = await PlexClient.get_audiobook_library_metadata(
            event_emitter=__event_emitter__
        )
        metadata = get_library_items(library["key"], "albums")["MediaContainer"].get(
            "Metadata", []
        )
        if not metadata:
            raise Exception("No metadata found for books")
        return [AudiobookMetadata(**item) for item in metadata]

    @staticmethod
    async def get_all_metadata(
        __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> List[CompiledData]:
        authors = await PlexClient.get_all_author_metadata(__event_emitter__)
        books = await PlexClient.get_all_books_metadata(__event_emitter__)
        compiled_data = []
        for book in books:
            author = next(
                (a for a in authors if a.ratingKey == book.parentRatingKey), None
            )
            if author:
                compiled_data.append(
                    CompiledData(
                        title=book.title,
                        author=author.title,
                        ratingKey=book.ratingKey,
                        authorRatingKey=author.ratingKey,
                        year=book.year,
                        lastViewedAt=convert_timestamp(book.lastViewedAt),
                        viewCount=book.viewCount,
                        genres=book.Genre,
                    )
                )

        # Sort the compiled data
        def sort_key(item):
            if item.viewCount is None or item.viewCount == 0:
                return (-1, item.title.lower())
            return (item.viewCount, item.title.lower())

        compiled_data.sort(key=sort_key, reverse=True)
        return compiled_data


async def main():
    try:
        # Fetch all authors metadata
        authors = await PlexClient.get_all_author_metadata()
        print(json.dumps([author.__dict__ for author in authors], indent=2))

        # Fetch all books metadata
        books = await PlexClient.get_all_books_metadata()
        print(json.dumps([book.__dict__ for book in books], indent=2))
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()


def filter_metadata(data: dict) -> dict:
    """Remove unnecessary keys from metadata dictionary."""
    keys_to_remove = {
        "key",
        "guid",
        "addedAt",
        "thumb",
        "index",
        "country",
        "location",
        "image",
        "ultrablurcolors",
        "skipcount",
        "art",
        "Country",
        "Location",
        "Image",
        "UltraBlurColors",
    }
    return {k: v for k, v in data.items() if k.lower() not in keys_to_remove}


class EventEmitter:
    """
    Helper wrapper for OpenWebUI event emissions.
    """

    def __init__(
        self,
        event_emitter: typing.Callable[[dict], typing.Any] = None,
        debug: bool = True,
    ):
        self.event_emitter = event_emitter
        self._debug = debug
        self._status_prefix = None
        self._emitted_status = False

    def set_status_prefix(self, status_prefix):
        self._status_prefix = status_prefix

    async def _emit(self, typ, data, twice):
        if self._debug:
            print(f"Emitting {typ} event: {data}", file=sys.stderr)
        if not self.event_emitter:
            return None
        result = None
        for i in range(2 if twice else 1):
            maybe_future = self.event_emitter(
                {
                    "type": typ,
                    "data": data,
                }
            )
            if asyncio.isfuture(maybe_future) or inspect.isawaitable(maybe_future):
                result = await maybe_future
        return result

    async def status(
        self, description="Unknown state", status="in_progress", done=False
    ):
        self._emitted_status = True
        if self._status_prefix is not None:
            description = f"{self._status_prefix}{description}"
        await self._emit(
            "status",
            {
                "status": status,
                "description": description,
                "done": done,
            },
            twice=not done and len(description) <= 1024,
        )

    async def fail(self, description="Unknown error"):
        await self.status(description=description, status="error", done=True)

    async def clear_status(self):
        if not self._emitted_status:
            return
        self._emitted_status = False
        await self._emit(
            "status",
            {
                "status": "complete",
                "description": "",
                "done": True,
            },
            twice=True,
        )

    async def message(self, content):
        await self._emit(
            "message",
            {
                "content": content,
            },
            twice=False,
        )

    async def citation(self, document, metadata, source):
        await self._emit(
            "citation",
            {
                "document": document,
                "metadata": metadata,
                "source": source,
            },
            twice=False,
        )


class Tools:
    class Valves(BaseModel):
        PLEX_BASE_URL: str = Field(
            default=os.getenv("PLEX_BASE_URL", "http://host.docker.internal:32400"),
            description="The base URL of the Plex server",
        )
        PLEX_TOKEN: str = Field(
            default=os.getenv("PLEX_TOKEN", "your_api_here"),
            description="The token to authenticate with the Plex server",
        )

    def __init__(self):
        self.valves = self.Valves()
        init_plex_client(self.valves.PLEX_BASE_URL, self.valves.PLEX_TOKEN)

    async def fetch_authors(
        self, __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> str:
        """Fetches metadata for all authors from the Plex server."""
        try:
            authors = await PlexClient.get_all_author_metadata(__event_emitter__)
            authors_data = [filter_metadata(author.__dict__) for author in authors]
            return json.dumps(authors_data, indent=2)
        except Exception as e:
            raise Exception(f"Error fetching authors: {str(e)}")

    async def fetch_books(
        self, __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> str:
        """Fetches metadata for all audiobooks from the Plex server."""
        try:
            compiled_data = await PlexClient.get_all_metadata(__event_emitter__)
            return json.dumps([book.__dict__ for book in compiled_data], indent=2)
        except Exception as e:
            raise Exception(f"Error fetching books: {str(e)}")

    async def fetch_all_data(
        self, __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> str:
        """Fetches metadata for all authors and audiobooks from the Plex server."""
        try:
            compiled_data = await PlexClient.get_all_metadata(__event_emitter__)
            compiled_data = [data.__dict__ for data in compiled_data]
            return json.dumps(compiled_data, indent=2)
        except Exception as e:
            raise Exception(f"Error fetching all data: {str(e)}")

    async def fetch_recent_books(
        self, n: int = 20, __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> str:
        """Fetches metadata for the n most recently viewed audiobooks from the Plex server.

        Args:
            n: Number of recent books to return (default: 20)
            __event_emitter__: Optional event emitter for status updates

        Returns:
            JSON string containing an array of CompiledData objects, sorted by viewCount,
            including only books that have been completed at least once.
        """
        try:
            all_data = await PlexClient.get_all_metadata(__event_emitter__)
            # Sort by viewCount descending and take top n
            recent_books = sorted(
                [book for book in all_data if book.viewCount and book.viewCount > 0],
                key=lambda x: x.viewCount,
                reverse=True,
            )[:n]
            return json.dumps([book.__dict__ for book in recent_books], indent=2)
        except Exception as e:
            raise Exception(f"Error fetching recent books: {str(e)}")

    async def fetch_unread_books(
        self, __event_emitter__: typing.Callable[[dict], typing.Any] = None
    ) -> str:
        """Fetches metadata for all unread audiobooks from the Plex server.

        Args:
            __event_emitter__: Optional event emitter for status updates

        Returns:
            JSON string containing an array of CompiledData objects for unread books,
            sorted alphabetically by title.
        """
        try:
            all_data = await PlexClient.get_all_metadata(__event_emitter__)
            # Filter for unread books only
            unread_books = [
                book
                for book in all_data
                if book.viewCount is None or book.viewCount == 0
            ]
            # Sort alphabetically by title
            unread_books.sort(key=lambda x: x.title.lower())
            return json.dumps([book.__dict__ for book in unread_books], indent=2)
        except Exception as e:
            raise Exception(f"Error fetching unread books: {str(e)}")


def convert_view_count(view_count: Optional[int]) -> Optional[str]:
    """Convert view count to a readable status."""
    if view_count is None or view_count == 0:
        return "Unread"
    return f"Completed {view_count} times"


def convert_timestamp(unix_timestamp: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to local time string."""
    if unix_timestamp is None:
        return None
    try:
        local_time = datetime.fromtimestamp(unix_timestamp)
        return local_time.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None
