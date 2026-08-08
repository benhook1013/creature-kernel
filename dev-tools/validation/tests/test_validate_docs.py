import importlib.util
import tempfile
import unittest
from pathlib import Path


VALIDATOR_PATH = Path(__file__).parents[2] / "validation" / "validate_docs.py"
SPEC = importlib.util.spec_from_file_location("validate_docs_under_test", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ValidatorFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.decisions = self.root / "docs" / "decisions"
        self.reviews = self.decisions / "reviews"
        self.reviews.mkdir(parents=True)
        (self.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        self.original_paths = (validator.ROOT, validator.DECISIONS, validator.REVIEWS)
        validator.ROOT = self.root
        validator.DECISIONS = self.decisions
        validator.REVIEWS = self.reviews

    def tearDown(self) -> None:
        validator.ROOT, validator.DECISIONS, validator.REVIEWS = self.original_paths
        self.tempdir.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def dr_text(
        self,
        *,
        status: str = "Proposed",
        review_status: str = "Pending",
        response_status: str = "Pending",
        response_block: str = "",
        review_link: str = "",
    ) -> str:
        approval = "Approved by Ben" if status == "Accepted" else "Pending"
        decided = "2026-08-08" if status == "Accepted" else "—"
        response = review_link + ("\n\n" + response_block if response_block else "")
        return f"""# DR-0001: Fixture decision

ID: DR-0001
Scope: Governance
Status: {status}
Revision: 1
Decision owner: Ben
Owner approval: {approval}
Review status: {review_status}
Response status: {response_status}
Date proposed: 2026-08-08
Date decided: {decided}
Supersedes: —
Superseded by: —

## Context

Fixture context.

## Decision

Fixture decision.

## Consequences

Fixture consequences.

## Alternatives Considered

Fixture alternative.

## Adversarial Review Response

{response}

## Implementation and Proof Obligations

Fixture proof.

## Canonical Design Links

[Fixture README](../../README.md)

## Reversibility and Revisit Triggers

Fixture revisit trigger.
"""

    def review_text(
        self,
        *,
        bundle: str = "[Target DR](../DR-0001-fixture.md)",
        sources: str = "[Target DR](../DR-0001-fixture.md)",
        include_bundle: bool = True,
        include_sources: bool = True,
        review_status: str = "Complete",
    ) -> str:
        headings = [
            "## Executive Assessment",
            "## Strongest Case Against",
            "## Hidden Assumptions",
            "## Failure Modes and Edge Cases",
            "## Alternatives and Steelman",
            "## Performance and Scalability",
            "## Portability, Lock-in, and Reversibility",
            "## Licensing, Security, and Supply Chain",
            "## Evidence Gaps",
            "## Blocking Objections",
            "## Non-blocking Risks",
            "## Conditions for Acceptance",
            "## Review Limitations",
        ]
        body = "\n\n".join(f"{heading}\n\nFixture review." for heading in headings)
        evidence = []
        if include_bundle:
            evidence.append(f"## Canonical Review Bundle\n\n{bundle}")
        if include_sources:
            evidence.append(f"## Sources Actually Read\n\n{sources}")
        evidence_text = "\n\n".join(evidence)
        return f"""# Adversarial review: DR-0001 revision 1

Target DR: DR-0001
Target revision: 1
Review status: {review_status}
Reviewer: Fixture reviewer
Recommendation: Revise

{body}

{evidence_text}
"""

    def prepare_dr_and_review(self, dr: str, review: str) -> None:
        self.write("docs/decisions/DR-0001-fixture.md", dr)
        values = validator.metadata(dr)
        self.write("docs/decisions/registry.md", """# Registry

| DR | Title | Scope | Status | Revision | Review | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| [DR-0001](DR-0001-fixture.md) | Fixture decision | Governance | """ + values["Status"] + """ | """ + values["Revision"] + """ | """ + values["Review status"] + """ | Ben |
""")
        self.write("docs/decisions/reviews/DR-0001-rev-01-review-01.md", review)

    def review_errors(self) -> list[str]:
        errors: list[str] = []
        validator.validate_reviews(errors)
        return errors

    def decision_errors(self) -> list[str]:
        errors: list[str] = []
        validator.validate_decision_records(errors)
        return errors

    def test_complete_review_rejects_missing_bundle(self) -> None:
        self.write("docs/decisions/DR-0001-fixture.md", "ID: DR-0001\n")
        self.write(
            "docs/decisions/reviews/DR-0001-rev-01-review-01.md",
            self.review_text(include_bundle=False),
        )
        errors = self.review_errors()
        self.assertTrue(any("Canonical Review Bundle" in error for error in errors))

    def test_complete_review_rejects_missing_sources(self) -> None:
        self.write("docs/decisions/DR-0001-fixture.md", "ID: DR-0001\n")
        self.write(
            "docs/decisions/reviews/DR-0001-rev-01-review-01.md",
            self.review_text(include_sources=False),
        )
        errors = self.review_errors()
        self.assertTrue(any("Sources Actually Read" in error for error in errors))

    def test_bundle_without_target_dr_link_rejects(self) -> None:
        self.write("docs/decisions/DR-0001-fixture.md", "ID: DR-0001\n")
        self.write("docs/decisions/other.md", "# Other\n")
        self.write(
            "docs/decisions/reviews/DR-0001-rev-01-review-01.md",
            self.review_text(bundle="[Other](../other.md)"),
        )
        errors = self.review_errors()
        self.assertTrue(any("Canonical Review Bundle" in error and "target DR" in error for error in errors))

    def test_accepted_dr_rejects_missing_response_record(self) -> None:
        review_link = "[Current review](reviews/DR-0001-rev-01-review-01.md)"
        dr = self.dr_text(
            status="Accepted",
            review_status="Complete",
            response_status="Complete",
            review_link=review_link,
        )
        self.prepare_dr_and_review(dr, self.review_text())
        errors = self.decision_errors()
        self.assertTrue(any("objection response block" in error for error in errors))

    def test_accepted_dr_rejects_placeholder_response(self) -> None:
        review_link = "[Current review](reviews/DR-0001-rev-01-review-01.md)"
        block = """### Objection response 1

Objection: None identified
Response: —
Disposition: Accepted risk
"""
        dr = self.dr_text(
            status="Accepted",
            review_status="Complete",
            response_status="Complete",
            response_block=block,
            review_link=review_link,
        )
        self.prepare_dr_and_review(dr, self.review_text())
        errors = self.decision_errors()
        self.assertTrue(any("non-placeholder 'Response'" in error for error in errors))

    def test_accepted_dr_requires_fullmatch_current_review_filename(self) -> None:
        review_link = "[Current review](reviews/DR-0001-rev-01-review-01-extra.md)"
        block = """### Objection response 1

Objection: None identified
Response: No unresolved objection is recorded.
Disposition: Addressed
"""
        dr = self.dr_text(
            status="Accepted",
            review_status="Complete",
            response_status="Complete",
            response_block=block,
            review_link=review_link,
        )
        self.write("docs/decisions/DR-0001-fixture.md", dr)
        self.write("docs/decisions/registry.md", """# Registry

| DR | Title | Scope | Status | Revision | Review | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| [DR-0001](DR-0001-fixture.md) | Fixture decision | Governance | Accepted | 1 | Complete | Ben |
""")
        self.write(
            "docs/decisions/reviews/DR-0001-rev-01-review-01-extra.md",
            self.review_text(),
        )
        errors = self.decision_errors()
        self.assertTrue(any("lacks review for revision 1" in error for error in errors))

    def test_valid_bundle_and_structured_response_passes(self) -> None:
        review_link = "[Current review](reviews/DR-0001-rev-01-review-01.md)"
        block = """### Objection response 1

Objection: None identified
Response: The current proposal records no unresolved objection.
Disposition: Addressed
"""
        dr = self.dr_text(
            status="Accepted",
            review_status="Complete",
            response_status="Complete",
            response_block=block,
            review_link=review_link,
        )
        review = self.review_text()
        self.prepare_dr_and_review(dr, review)
        self.assertEqual([], self.review_errors())
        self.assertEqual([], self.decision_errors())

    def test_metadata_after_heading_and_fenced_heading_do_not_spoof_contract(self) -> None:
        text = self.review_text().replace(
            "## Canonical Review Bundle\n\n[Target DR](../DR-0001-fixture.md)",
            "```markdown\n## Canonical Review Bundle\n[Target DR](../DR-0001-fixture.md)\n```",
        )
        text = text.replace("## Executive Assessment\n\nFixture review.", "## Executive Assessment\n\nReview status: Pending\nFixture review.")
        self.write("docs/decisions/DR-0001-fixture.md", "ID: DR-0001\n")
        self.write("docs/decisions/reviews/DR-0001-rev-01-review-01.md", text)
        errors = self.review_errors()
        self.assertTrue(any("Canonical Review Bundle" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
