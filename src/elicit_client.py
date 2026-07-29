import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_URL = "https://elicit.com/api/v2/search/papers"
DEFAULT_STUDY_TYPES = ("Systematic Review", "Meta-Analysis", "RCT", "Longitudinal")
MAX_RESPONSE_BYTES = 5_000_000
MAX_PAPERS = 50


class ConfigurationError(RuntimeError):
    pass


class ElicitApiError(RuntimeError):
    pass


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _open_request(request: Request, timeout_seconds: int):
    return build_opener(_NoRedirectHandler()).open(request, timeout=timeout_seconds)


@dataclass(frozen=True)
class Paper:
    elicit_id: str | None
    title: str
    authors: tuple[str, ...]
    year: int | None
    abstract: str | None
    doi: str | None
    pmid: str | None
    venue: str | None
    cited_by_count: int | None
    urls: tuple[str, ...]


class ElicitClient:
    def __init__(self, api_key: str, timeout_seconds: int = 30) -> None:
        if not api_key.strip():
            raise ConfigurationError("ELICIT_API_KEY is empty")
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "ElicitClient":
        api_key = os.environ.get("ELICIT_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "ELICIT_API_KEY is missing; set it in the environment and never commit it"
            )
        return cls(api_key)

    def search_papers(
        self,
        query: str,
        *,
        max_results: int = 8,
        min_year: int = 2018,
        study_types: tuple[str, ...] = DEFAULT_STUDY_TYPES,
    ) -> tuple[Paper, ...]:
        normalized_query = " ".join(query.split())
        if not 3 <= len(normalized_query) <= 500:
            raise ValueError("query must contain 3-500 characters")
        if not 1 <= max_results <= MAX_PAPERS:
            raise ValueError(f"max_results must be between 1 and {MAX_PAPERS}")
        if not 1900 <= min_year <= 2100:
            raise ValueError("min_year is outside the supported range")

        body = {
            "query": normalized_query,
            "searchMode": "semantic",
            "corpus": "elicit",
            "maxResults": max_results,
            "filters": {
                "minYear": min_year,
                "typeTags": list(study_types),
                "retracted": "exclude_retracted",
            },
        }
        request = Request(
            API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "plain-spoken-pebble-research/1.0",
            },
            method="POST",
        )
        payload = self._request_json(request)
        if not isinstance(payload, dict):
            raise ElicitApiError("Elicit response must be a JSON object")
        raw_papers = payload.get("papers")
        if not isinstance(raw_papers, list):
            raise ElicitApiError("Elicit response is missing the papers collection")
        if len(raw_papers) > max_results:
            raise ElicitApiError("Elicit returned more papers than requested")

        papers = []
        for item in raw_papers:
            if not isinstance(item, dict):
                raise ElicitApiError("Elicit returned a malformed paper record")
            papers.append(_parse_paper(item))
        return tuple(papers)

    def _request_json(self, request: Request) -> object:
        try:
            with _open_request(request, self._timeout_seconds) as response:
                raw_response = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            if 300 <= error.code < 400:
                message = "Elicit returned an unexpected redirect; request stopped to protect the API key"
            else:
                messages = {
                    400: "Elicit rejected the search request",
                    401: "Elicit authentication failed; check ELICIT_API_KEY",
                    402: "Elicit quota is insufficient for this request",
                    403: "Elicit API access requires an eligible plan",
                    429: "Elicit rate limit reached; wait before retrying",
                }
                message = messages.get(error.code, f"Elicit returned HTTP {error.code}")
            raise ElicitApiError(message) from None
        except URLError as error:
            raise ElicitApiError(f"Elicit could not be reached: {error.reason}") from None

        if len(raw_response) > MAX_RESPONSE_BYTES:
            raise ElicitApiError("Elicit response is too large")
        try:
            return json.loads(raw_response)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ElicitApiError("Elicit returned an invalid JSON response") from None


def _parse_paper(item: dict) -> Paper:
    authors_value = item.get("authors")
    urls_value = item.get("urls")
    if not isinstance(authors_value, list) or len(authors_value) > 100:
        raise ElicitApiError("Elicit returned an invalid authors collection")
    if not isinstance(urls_value, list) or len(urls_value) > 20:
        raise ElicitApiError("Elicit returned an invalid URLs collection")

    authors = tuple(_required_string(author, "author", 300) for author in authors_value)
    urls = tuple(url for value in urls_value if (url := _safe_paper_url(value)) is not None)
    year = item.get("year")
    if year is not None and (type(year) is not int or not 1800 <= year <= 2100):
        raise ElicitApiError("Elicit returned an invalid publication year")
    cited_by_count = item.get("citedByCount")
    if cited_by_count is not None and (
        type(cited_by_count) is not int or not 0 <= cited_by_count <= 1_000_000_000
    ):
        raise ElicitApiError("Elicit returned an invalid citation count")

    return Paper(
        elicit_id=_optional_string(item.get("elicitId"), "elicitId", 300),
        title=_required_string(item.get("title"), "title", 1_000),
        authors=authors,
        year=year,
        abstract=_optional_string(item.get("abstract"), "abstract", 100_000),
        doi=_optional_string(item.get("doi"), "doi", 500),
        pmid=_optional_string(item.get("pmid"), "pmid", 100),
        venue=_optional_string(item.get("venue"), "venue", 1_000),
        cited_by_count=cited_by_count,
        urls=urls,
    )


def _safe_paper_url(value: object) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 2_048:
        return None
    if any(character.isspace() or ord(character) < 32 for character in value):
        return None
    if any(character in value for character in "()[]<>\"'"):
        return None
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
    except (UnicodeError, ValueError):
        return None
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        return None
    return value


def _required_string(value: object, field: str, maximum_length: int) -> str:
    parsed = _optional_string(value, field, maximum_length)
    if parsed is None:
        raise ElicitApiError(f"Elicit returned an invalid {field}")
    return parsed


def _optional_string(value: object, field: str, maximum_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ElicitApiError(f"Elicit returned an invalid {field}")
    parsed = " ".join(value.split())
    if not parsed or len(parsed) > maximum_length:
        raise ElicitApiError(f"Elicit returned an invalid {field}")
    return parsed
