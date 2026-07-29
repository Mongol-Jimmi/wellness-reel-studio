import unittest

from scripts.research_issue import NoRedirectHandler, extract_query, markdown_text


class ResearchIssueTests(unittest.TestCase):
    def test_openalex_redirects_are_not_followed(self) -> None:
        redirected = NoRedirectHandler().redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://attacker.test/collect",
        )
        self.assertIsNone(redirected)

    def test_external_markdown_is_flattened_and_escaped(self) -> None:
        value = "Paper title\n\n## Injected [link](https://attacker.test)"
        rendered = markdown_text(value)
        self.assertNotIn("\n", rendered)
        self.assertIn(r"\[link\]", rendered)
        self.assertNotIn("[link](", rendered)

    def test_extracts_encoded_query_metadata(self) -> None:
        body = "<!-- research-query: choice overload &amp; cognitive load -->"
        self.assertEqual(extract_query(body), "choice overload & cognitive load")

    def test_extracts_filled_issue_template_section(self) -> None:
        body = """## Evidence question

What evidence links microbreaks with perceived fatigue?

## Visual direction

A small timer.
"""
        self.assertEqual(
            extract_query(body),
            "What evidence links microbreaks with perceived fatigue?",
        )

    def test_rejects_missing_placeholder_or_tiny_query(self) -> None:
        with self.assertRaises(ValueError):
            extract_query("no metadata")
        with self.assertRaises(ValueError):
            extract_query("<!-- research-query: tiny -->")
        template = """## Evidence question

<!-- A sourceable research question, not a publication claim. -->

## Visual direction
"""
        with self.assertRaises(ValueError):
            extract_query(template)


if __name__ == "__main__":
    unittest.main()
