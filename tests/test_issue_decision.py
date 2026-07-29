import json
import unittest
from pathlib import Path

from scripts.create_topic_issues import issue_body, validate
from scripts.issue_decision import event_outputs, parse_decision


class DecisionTests(unittest.TestCase):
    def test_approve_only_is_valid(self) -> None:
        body = "- [x] Approve for research\n- [ ] Reject"
        self.assertEqual(parse_decision(body), "approve")

    def test_reject_only_is_valid(self) -> None:
        body = "- [ ] Approve for research\n- [X] Reject"
        self.assertEqual(parse_decision(body), "reject")

    def test_empty_and_conflicting_decisions_are_invalid(self) -> None:
        self.assertEqual(parse_decision("- [ ] Approve for research\n- [ ] Reject"), "invalid")
        self.assertEqual(parse_decision("- [x] Approve for research\n- [x] Reject"), "invalid")

    def test_duplicate_or_missing_controls_are_invalid(self) -> None:
        self.assertEqual(parse_decision("- [x] Approve for research"), "invalid")
        duplicated = "- [x] Approve for research\n- [ ] Approve for research\n- [ ] Reject"
        self.assertEqual(parse_decision(duplicated), "invalid")

    def test_unrelated_edit_does_not_repeat_an_approval_transition(self) -> None:
        previous = "Old hook\n- [x] Approve for research\n- [ ] Reject"
        current = "Better hook\n- [x] Approve for research\n- [ ] Reject"
        event = {
            "issue": {"number": 4, "body": current, "labels": [{"name": "topic-proposal"}]},
            "changes": {"body": {"from": previous}},
        }
        output = event_outputs(event)
        self.assertEqual(output["decision"], "approve")
        self.assertEqual(output["decision_changed"], "false")

    def test_title_only_edit_does_not_repeat_a_decision(self) -> None:
        event = {
            "issue": {
                "number": 4,
                "body": "- [x] Approve for research\n- [ ] Reject",
                "labels": [{"name": "topic-proposal"}],
            },
            "changes": {"title": {"from": "Old title"}},
        }
        self.assertEqual(event_outputs(event)["decision_changed"], "false")

    def test_changed_decision_is_processed(self) -> None:
        event = {
            "issue": {
                "number": 4,
                "body": "- [ ] Approve for research\n- [x] Reject",
                "labels": [{"name": "topic-proposal"}],
            },
            "changes": {"body": {"from": "- [x] Approve for research\n- [ ] Reject"}},
        }
        self.assertEqual(event_outputs(event)["decision_changed"], "true")


class WorkflowBoundaryTests(unittest.TestCase):
    def test_untrusted_issue_event_only_dispatches_trusted_transition(self) -> None:
        validator = Path(".github/workflows/issue-decision.yml").read_text(encoding="utf-8")
        applier = Path(".github/workflows/apply-decision.yml").read_text(encoding="utf-8")
        self.assertIn("gh workflow run apply-decision.yml", validator)
        self.assertNotIn("gh issue edit", validator)
        self.assertNotIn("topic-lifecycle-", validator)
        self.assertIn("group: topic-lifecycle-${{ inputs.issue_number }}", applier)
        self.assertIn("scripts.issue_decision import parse_decision", applier)


class ProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proposals = json.loads(Path("ideas/proposals.json").read_text(encoding="utf-8"))

    def test_proposal_catalog_is_valid(self) -> None:
        validate(self.proposals)

    def test_issue_body_contains_exactly_two_unchecked_decisions(self) -> None:
        body = issue_body(self.proposals[0])
        self.assertEqual(body.count("- [ ] Approve for research"), 1)
        self.assertEqual(body.count("- [ ] Reject"), 1)
        self.assertNotIn("—", body)
        self.assertIn("human reviews the full text", body)


if __name__ == "__main__":
    unittest.main()
