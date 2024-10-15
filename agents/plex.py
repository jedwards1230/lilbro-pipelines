import requests
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


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
    thumb: str
    index: Optional[int]
    guid: str
    type: str
    summary: str
    viewCount: Optional[int]
    lastViewedAt: Optional[int]
    addedAt: Optional[int]
    updatedAt: int
    Country: Optional[Any]
    Location: List[Dict[str, str]]
    Genre: Optional[List[TagData]]
    Similar: Optional[List[TagData]]


@dataclass
class ExpandedAuthorMetadata(AuthorMetadata):
    librarySectionTitle: str
    librarySectionID: str
    librarySectionKey: str


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
    thumb: str
    originallyAvailableAt: str
    addedAt: int
    updatedAt: int
    loudnessAnalysisVersion: int
    musicAnalysisVersion: int
    Genre: List[TagData]


@dataclass
class AudiobookMetadata(AuthorChildrenMetadata):
    leafCount: int
    allowSync: bool
    librarySectionID: int
    librarySectionTitle: str
    librarySectionUUID: str
    lastViewedAt: int
    Media: Optional[List[Any]]


@dataclass
class CompiledData:
    title: str
    author: str
    ratingKey: str
    authorRatingKey: str
    year: int
    lastViewedAt: Optional[str]
    genres: Optional[str]


class PlexClient:
    """Plex Client to interact with Audiobook Library"""

    @staticmethod
    def get_audiobook_library_metadata() -> Dict[str, Any]:
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
        return lib

    @staticmethod
    def get_all_author_metadata() -> List[AuthorMetadata]:
        library = PlexClient.get_audiobook_library_metadata()
        metadata = get_library_items(library["key"])["MediaContainer"].get(
            "Metadata", []
        )
        if not metadata:
            raise Exception("No metadata found")
        return [AuthorMetadata(**item) for item in metadata]

    @staticmethod
    def get_all_books_metadata() -> List[AudiobookMetadata]:
        library = PlexClient.get_audiobook_library_metadata()
        metadata = get_library_items(library["key"], "albums")["MediaContainer"].get(
            "Metadata", []
        )
        if not metadata:
            raise Exception("No metadata found for books")
        return [AudiobookMetadata(**item) for item in metadata]


def main():
    try:
        # Fetch all authors metadata
        authors = PlexClient.get_all_author_metadata()
        print(json.dumps([author.__dict__ for author in authors], indent=2))

        # Fetch all books metadata
        books = PlexClient.get_all_books_metadata()
        print(json.dumps([book.__dict__ for book in books], indent=2))
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()


def fetch_audiobook_and_author_data() -> str:
    """Fetches metadata for all authors and audiobooks from the Plex server.

    Returns:
        str: JSON string with combined metadata or an error message.
    """
    try:
        # Fetch all authors metadata
        authors = PlexClient.get_all_author_metadata()
        authors_data = [author.__dict__ for author in authors]

        # Fetch all books metadata
        books = PlexClient.get_all_books_metadata()
        books_data = [book.__dict__ for book in books]

        # Combine data
        combined_data = {"authors": authors_data, "books": books_data}

        return json.dumps(combined_data, indent=2)
    except Exception as e:
        return f"An error occurred: {e}"
