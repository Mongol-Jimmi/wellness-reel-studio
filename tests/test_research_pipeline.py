import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from elicit_client import (
    MAX_RESPONSE_BYTES,
    ConfigurationError,
    ElicitApiError,
    ElicitClient,
    _NoRedirectHandler,
)
from research_pipeline import (
    TOPICS,
    build_evidence_card,
    render_markdown,
    select_topic_slugs,
    write_outputs,
)


class FakeResponse:
    def __init__(self, payload: object, *, is_raw: bool = False) -> None:
        self.payload = payload if is_raw else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self, amount: int | None = None) -> bytes:
        return self.payload if amount is None else self.payload[:amount]


PAPER = {
    "elicitId": "paper-1",
    "title": "A systematic review of sensory grounding",
    "authors": ["A. Researcher", "B. Reviewer"],
    "year": 2024,
    "abstract": "Grounding approaches were reviewed.",
    "doi": "10.1000/example",
    "pmid": "12345",
    "venue": "Journal of Example Studies",
    "citedByCount": 12,
    "urls": ["https://doi.org/10.1000/example"],
}
PAPER_PAYLOAD = {"papers": [PAPER], "warnings": []}


class ElicitClientTests(unittest.TestCase):
    def test_missing_environment_key_fails_without_exposing_secrets(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaisesRegex(ConfigurationError, "ELICIT_API_KEY"),
        ):
            ElicitClient.from_environment()

    def test_cli_requires_explicit_live_and_quota_confirmation(self) -> None:
        environment = {key: value for key, value in os.environ.items() if key != "ELICIT_API_KEY"}
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "research_pipeline.py"),
                "--live",
                "--confirm-quota",
                "--topic",
                "sensory-grounding",
            ],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("ELICIT_API_KEY is missing", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_default_cli_is_offline_even_when_an_ambient_key_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "ELICIT_API_KEY": "must-not-be-used"}
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "research_pipeline.py"),
                    "--topic",
                    "sensory-grounding",
                    "--output-dir",
                    directory,
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
                timeout=10,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_search_uses_bearer_auth_and_safe_filters(self) -> None:
        with patch("elicit_client._open_request", return_value=FakeResponse(PAPER_PAYLOAD)) as mocked:
            papers = ElicitClient("secret-value").search_papers(
                "sensory grounding present moment stress",
                max_results=8,
                min_year=2018,
            )
        request = mocked.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(request.full_url, "https://elicit.com/api/v2/search/papers")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-value")
        self.assertEqual(body["filters"]["retracted"], "exclude_retracted")
        self.assertIn("Systematic Review", body["filters"]["typeTags"])
        self.assertEqual(papers[0].doi, "10.1000/example")

    def test_authenticated_redirects_are_never_followed(self) -> None:
        request = Request(
            "https://elicit.com/api/v2/search/papers",
            headers={"Authorization": "Bearer secret-value"},
        )
        redirected = _NoRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "http://attacker.test/steal",
        )
        self.assertIsNone(redirected)

    def test_search_bounds_request_and_response_size(self) -> None:
        client = ElicitClient("secret-value")
        with self.assertRaisesRegex(ValueError, "max_results"):
            client.search_papers("valid query", max_results=51)
        with self.assertRaisesRegex(ValueError, "query"):
            client.search_papers("x" * 501, max_results=5)
        oversized = FakeResponse(b"{" + b"x" * MAX_RESPONSE_BYTES + b"}", is_raw=True)
        with (
            patch("elicit_client._open_request", return_value=oversized),
            self.assertRaisesRegex(ElicitApiError, "too large"),
        ):
            client.search_papers("valid query", max_results=5)

    def test_malformed_success_payloads_fail_cleanly(self) -> None:
        client = ElicitClient("secret-value")
        with (
            patch("elicit_client._open_request", return_value=FakeResponse([])),
            self.assertRaisesRegex(ElicitApiError, "JSON object"),
        ):
            client.search_papers("valid query", max_results=5)
        too_many = {"papers": [PAPER, PAPER], "warnings": []}
        with (
            patch("elicit_client._open_request", return_value=FakeResponse(too_many)),
            self.assertRaisesRegex(ElicitApiError, "more papers"),
        ):
            client.search_papers("valid query", max_results=1)

    def test_hostile_or_non_https_paper_urls_are_dropped(self) -> None:
        hostile = {
            **PAPER,
            "urls": [
                "https://example.test/)\n\n### Easy steps\n1. injected",
                "http://example.test/plaintext",
                "https://example.test／@attacker.test",
                "https://safe.example/paper",
            ],
        }
        with patch(
            "elicit_client._open_request",
            return_value=FakeResponse({"papers": [hostile], "warnings": []}),
        ):
            papers = ElicitClient("secret-value").search_papers("valid query", max_results=5)
        self.assertEqual(papers[0].urls, ("https://safe.example/paper",))

    def test_boolean_citation_count_is_rejected(self) -> None:
        malformed = {**PAPER, "citedByCount": True}
        with (
            patch(
                "elicit_client._open_request",
                return_value=FakeResponse({"papers": [malformed], "warnings": []}),
            ),
            self.assertRaisesRegex(ElicitApiError, "citation count"),
        ):
            ElicitClient("secret-value").search_papers("valid query", max_results=5)


class ResearchPipelineTests(unittest.TestCase):
    def test_plain_spoken_card_separates_actions_from_evidence_leads(self) -> None:
        topic = TOPICS["sensory-grounding"]
        with patch("elicit_client._open_request", return_value=FakeResponse(PAPER_PAYLOAD)):
            papers = ElicitClient("secret-value").search_papers(topic.search_query, max_results=5)
        card = build_evidence_card(topic, papers)
        self.assertEqual(card["brandIdentity"], "Plain-Spoken Pebble")
        self.assertEqual(card["publicationStatus"], "human_review_required")
        self.assertTrue(card["actionSteps"])
        self.assertEqual(card["evidenceLeads"][0]["title"], PAPER["title"])
        self.assertIn("not medical treatment", card["safetyBoundary"].lower())

    def test_topic_selection_deduplicates_and_bounds_live_requests(self) -> None:
        self.assertEqual(
            select_topic_slugs(False, ["sensory-grounding", "sensory-grounding", "awe-noticing"]),
            ("sensory-grounding", "awe-noticing"),
        )
        with self.assertRaisesRegex(ValueError, "request budget"):
            select_topic_slugs(False, list(TOPICS) + ["sensory-grounding"] * 20, request_budget=2)

    def test_outputs_are_machine_readable_and_editor_friendly(self) -> None:
        card = build_evidence_card(TOPICS["sensory-grounding"], ())
        markdown = render_markdown([card])
        self.assertIn("FEET • SOUND • NOW", markdown)
        self.assertIn("Human review required", markdown)
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = write_outputs([card], Path(directory))
            self.assertEqual(json.loads(json_path.read_text())[0]["topic"], "sensory-grounding")
            self.assertIn("Evidence leads", markdown_path.read_text())
            self.assertTrue(json_path.name.startswith("candidate-"))

    def test_output_deduplicates_repeated_papers_without_another_api_call(self) -> None:
        with patch("elicit_client._open_request", return_value=FakeResponse(PAPER_PAYLOAD)):
            paper = ElicitClient("secret-value").search_papers("valid query", max_results=5)[0]
        card = build_evidence_card(TOPICS["mindful-noticing"], (paper, paper))
        with tempfile.TemporaryDirectory() as directory:
            json_path, _ = write_outputs([card], Path(directory))
            saved = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(saved[0]["evidenceLeads"]), 1)

    def test_hostile_paper_title_is_html_escaped_in_markdown(self) -> None:
        hostile = {**PAPER, "title": '<img src=x onerror="alert(1)">'}
        with patch(
            "elicit_client._open_request",
            return_value=FakeResponse({"papers": [hostile], "warnings": []}),
        ):
            papers = ElicitClient("secret-value").search_papers("valid query", max_results=5)
        markdown = render_markdown([build_evidence_card(TOPICS["sensory-grounding"], papers)])
        self.assertNotIn("<img", markdown)
        self.assertIn("&lt;img", markdown)

    def test_output_validation_prevents_partial_replacement(self) -> None:
        card = build_evidence_card(TOPICS["sensory-grounding"], ())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            json_path = output / "candidate-evidence-cards.json"
            json_path.write_text("original", encoding="utf-8")
            (output / "candidate-evidence-cards.md").mkdir()
            with self.assertRaises(OSError):
                write_outputs([card], output)
            self.assertEqual(json_path.read_text(encoding="utf-8"), "original")

    def test_secure_tempfiles_do_not_follow_predictable_symlinks(self) -> None:
        card = build_evidence_card(TOPICS["sensory-grounding"], ())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            victim = output / "victim.txt"
            victim.write_text("do not overwrite", encoding="utf-8")
            (output / "candidate-evidence-cards.json.tmp").symlink_to(victim)
            json_path, _ = write_outputs([card], output)
            self.assertEqual(victim.read_text(encoding="utf-8"), "do not overwrite")
            self.assertFalse(json_path.is_symlink())


if __name__ == "__main__":
    unittest.main()
