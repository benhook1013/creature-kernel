#!/usr/bin/env python3
"""Validate Creature Kernel's foundational documentation contracts."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "architecture" / "decisions"
REVIEWS = DECISIONS / "reviews"

REQUIRED_PATHS = (
    "AGENTS.md",
    "README.md",
    "docs/README.md",
    "docs/FOUNDATION.md",
    "docs/product/README.md",
    "docs/product/vision-and-scope.md",
    "docs/product/requirements.md",
    "docs/product/users-and-workflows.md",
    "docs/architecture/README.md",
    "docs/architecture/system-overview.md",
    "docs/architecture/execution-model.md",
    "docs/architecture/component-responsibilities.md",
    "docs/architecture/repository-structure.md",
    "docs/architecture/decisions/README.md",
    "docs/architecture/decisions/registry.md",
    "docs/architecture/decisions/adr-template.md",
    "docs/architecture/decisions/reviews/README.md",
    "docs/architecture/decisions/reviews/adversarial-review-template.md",
    "docs/architecture/decisions/reviews/fresh-reread-preamble.md",
    "docs/developer-workflows/README.md",
    "docs/developer-workflows/ai-delegation-and-review.md",
    "docs/research/README.md",
    "docs/research/open-questions.md",
    "docs/research/references.md",
    "docs/project/README.md",
    "docs/project/kickoff-plan.md",
    "docs/project/status.md",
    "docs/project/roadmap.md",
    "docs/project/repository-evolution.md",
    "spec/README.md",
    "experiments/README.md",
    "experiments/experiment-template.md",
    "fixtures/README.md",
    "benchmarks/README.md",
)

ADR_FILENAME = re.compile(r"^(ADR-(\d{4}))-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
REVIEW_FILENAME = re.compile(
    r"^(ADR-(\d{4}))-rev-(\d{2})-review-(\d{2})\.md$"
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
METADATA_LINE = re.compile(r"^([A-Za-z][A-Za-z ]+):\s*(.+?)\s*$", re.MULTILINE)

ADR_STATUSES = {
    "Candidate",
    "Proposed",
    "Under Review",
    "Accepted",
    "Rejected",
    "Superseded",
    "Withdrawn",
}
REVIEW_STATUSES = {"Pending", "In Progress", "Complete", "Waived", "Stale"}
ADR_HEADINGS = (
    "## Context",
    "## Decision",
    "## Consequences",
    "## Alternatives Considered",
    "## Adversarial Review Response",
    "## Implementation and Proof Obligations",
    "## Canonical Design Links",
    "## Reversibility and Revisit Triggers",
)
REVIEW_HEADINGS = (
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
)
REGISTRY_LINK = re.compile(
    r"^\[(?P<id>ADR-\d{4})\]\((?P<filename>[^)]+)\)$"
)
REGISTRY_ADR_ID = re.compile(r"\bADR-\d{4}\b")
ADR_TITLE = re.compile(r"^# (?P<id>ADR-\d{4}): (?P<title>[^\n]+)$", re.MULTILINE)
PLACEHOLDER_VALUES = {"", "—", "-", "Pending"}


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def metadata(text: str) -> dict[str, str]:
    return {key: value for key, value in METADATA_LINE.findall(text)}


def section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    remainder = text[start + len(heading) :]
    next_heading = re.search(r"^## ", remainder, re.MULTILINE)
    return remainder[: next_heading.start()] if next_heading else remainder


def validate_required_paths(errors: list[str]) -> None:
    for name in REQUIRED_PATHS:
        if not (ROOT / name).is_file():
            errors.append(f"missing required file: {name}")


def validate_whitespace(errors: list[str]) -> None:
    checked_suffixes = {".md", ".py", ".yml", ".yaml"}
    for path in sorted(ROOT.rglob("*")):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix not in checked_suffixes and path.name not in {
            "AGENTS.md",
            "README.md",
        }:
            continue
        data = path.read_bytes()
        if data and not data.endswith(b"\n"):
            errors.append(f"missing final newline: {relative(path)}")
        try:
            lines = data.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            errors.append(f"expected UTF-8 text: {relative(path)}")
            continue
        for number, line in enumerate(lines, start=1):
            if line.rstrip(" \t") != line:
                errors.append(f"trailing whitespace: {relative(path)}:{number}")


def normalize_link(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " \"" in target:
        target = target.split(" \"", 1)[0]
    return unquote(target)


def validate_local_links(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK.findall(text):
            target = normalize_link(raw)
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            file_target = target.split("#", 1)[0]
            if not file_target:
                continue
            resolved = (path.parent / file_target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"local link escapes repository: {relative(path)} -> {target}"
                )
                continue
            if not resolved.exists():
                errors.append(f"broken local link: {relative(path)} -> {target}")


def adr_files() -> list[Path]:
    return sorted(
        path
        for path in DECISIONS.glob("ADR-*.md")
        if path.name != "adr-template.md"
    )


def review_files() -> list[Path]:
    return sorted(
        path
        for path in REVIEWS.glob("ADR-*.md")
        if path.name != "adversarial-review-template.md"
    )


def registry_rows(text: str) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        id_match = REGISTRY_ADR_ID.search(cells[0])
        if not id_match:
            continue
        link_match = REGISTRY_LINK.fullmatch(cells[0])
        rows.append(
            {
                "line": str(number),
                "id": link_match.group("id") if link_match else id_match.group(0),
                "filename": link_match.group("filename") if link_match else None,
                "title": cells[1],
                "status": cells[2],
                "revision": cells[3],
                "review": cells[4],
                "owner": cells[5],
            }
        )
    return rows


def validate_adrs(errors: list[str]) -> None:
    registry_path = DECISIONS / "registry.md"
    registry = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
    rows = registry_rows(registry)
    rows_by_id: dict[str, list[dict[str, str | None]]] = {}
    seen_registry_ids: set[str] = set()
    for row in rows:
        row_id = row["id"]
        if row_id in seen_registry_ids:
            errors.append(f"duplicate registry ADR ID: {row_id}")
        if row_id is not None:
            seen_registry_ids.add(row_id)
            rows_by_id.setdefault(row_id, []).append(row)
        if row["filename"] is None:
            errors.append(
                "registry ADR row must link an ADR filename: "
                f"{relative(registry_path)}:{row['line']}"
            )

    files_by_filename = {path.name: path for path in adr_files()}
    files_by_id: dict[str, Path] = {}
    for path in adr_files():
        match = ADR_FILENAME.fullmatch(path.name)
        if match:
            files_by_id.setdefault(match.group(1), path)

    for row in rows:
        row_id = row["id"]
        filename = row["filename"]
        if row_id not in files_by_id:
            errors.append(f"registry ADR has no corresponding file: {row_id}")
        if filename is not None and filename not in files_by_filename:
            errors.append(f"registry ADR file is missing: {filename}")
        if filename is not None:
            filename_match = ADR_FILENAME.fullmatch(Path(filename).name)
            if filename_match and filename_match.group(1) != row_id:
                errors.append(
                    f"registry ADR ID does not match linked filename at "
                    f"{relative(registry_path)}:{row['line']}: "
                    f"{row_id} vs {filename}"
                )

    seen_ids: set[str] = set()

    for path in adr_files():
        match = ADR_FILENAME.fullmatch(path.name)
        if not match:
            errors.append(f"invalid ADR filename: {relative(path)}")
            continue
        filename_id = match.group(1)
        text = path.read_text(encoding="utf-8")
        values = metadata(text)
        adr_id = values.get("ID")

        if adr_id != filename_id:
            errors.append(
                f"ADR ID mismatch in {relative(path)}: expected {filename_id}, got {adr_id!r}"
            )
        if adr_id in seen_ids:
            errors.append(f"duplicate ADR ID: {adr_id}")
        if adr_id:
            seen_ids.add(adr_id)

        expected_title = f"# {filename_id}:"
        if not text.startswith(expected_title):
            errors.append(f"ADR title must start with '{expected_title}': {relative(path)}")

        for field in (
            "ID",
            "Status",
            "Revision",
            "Decision owner",
            "Owner approval",
            "Review status",
            "Date proposed",
            "Date decided",
            "Supersedes",
            "Superseded by",
        ):
            if field not in values:
                errors.append(f"missing ADR metadata '{field}': {relative(path)}")

        status = values.get("Status")
        review_status = values.get("Review status")
        if status and status not in ADR_STATUSES:
            errors.append(f"invalid ADR status '{status}': {relative(path)}")
        if review_status and review_status not in REVIEW_STATUSES:
            errors.append(f"invalid review status '{review_status}': {relative(path)}")

        registry_matches = rows_by_id.get(filename_id, [])
        if not registry_matches:
            errors.append(f"ADR missing from registry: {filename_id}")
        elif len(registry_matches) != 1:
            errors.append(
                f"ADR must have exactly one registry row: {filename_id} "
                f"(found {len(registry_matches)})"
            )
        else:
            row = registry_matches[0]
            adr_title_match = ADR_TITLE.match(text)
            adr_title = adr_title_match.group("title") if adr_title_match else None
            comparisons = (
                ("ID", row["id"], adr_id),
                ("linked filename", row["filename"], path.name),
                ("title", row["title"], adr_title),
                ("status", row["status"], status),
                ("revision", row["revision"], values.get("Revision")),
                ("review status", row["review"], review_status),
                ("decision owner", row["owner"], values.get("Decision owner")),
            )
            for field, registry_value, adr_value in comparisons:
                if registry_value != adr_value:
                    errors.append(
                        f"ADR registry {field} mismatch for {filename_id}: "
                        f"registry={registry_value!r}, ADR={adr_value!r}"
                    )

        revision_text = values.get("Revision", "")
        try:
            revision = int(revision_text)
            if revision < 1:
                raise ValueError
        except ValueError:
            errors.append(f"ADR revision must be a positive integer: {relative(path)}")
            revision = 0

        for heading in ADR_HEADINGS:
            if heading not in text:
                errors.append(f"missing ADR heading '{heading}': {relative(path)}")

        if review_status == "Waived":
            for field in ("Waiver reason", "Accepted risk"):
                if values.get(field, "").strip() in PLACEHOLDER_VALUES:
                    errors.append(
                        f"waived ADR requires non-placeholder '{field}' metadata: "
                        f"{relative(path)}"
                    )

        if status == "Accepted":
            expected_approval = f"Approved by {values.get('Decision owner')}"
            if values.get("Owner approval") != expected_approval:
                errors.append(
                    "accepted ADR requires exact owner approval "
                    f"'{expected_approval}': {relative(path)}"
                )
            if review_status not in {"Complete", "Waived"}:
                errors.append(
                    f"accepted ADR requires complete review or waiver: {relative(path)}"
                )
            if values.get("Date decided") in {None, "—", "-"}:
                errors.append(f"accepted ADR requires decision date: {relative(path)}")
            canonical = section(text, "## Canonical Design Links")
            if not MARKDOWN_LINK.search(canonical):
                errors.append(f"accepted ADR requires canonical links: {relative(path)}")
            if review_status == "Complete" and revision:
                prefix = f"{filename_id}-rev-{revision:02d}-review-"
                matching_reviews = [
                    review for review in review_files() if review.name.startswith(prefix)
                ]
                if not matching_reviews:
                    errors.append(
                        f"accepted ADR lacks review for revision {revision}: {relative(path)}"
                    )
                response = section(text, "## Adversarial Review Response")
                linked_review = False
                for raw in MARKDOWN_LINK.findall(response):
                    target = normalize_link(raw).split("#", 1)[0]
                    if not target:
                        continue
                    resolved = (path.parent / target).resolve()
                    if any(resolved == review.resolve() for review in matching_reviews):
                        linked_review = True
                        break
                if not linked_review:
                    errors.append(
                        "accepted ADR review response must link a matching review "
                        f"file for revision {revision}: {relative(path)}"
                    )


def validate_reviews(errors: list[str]) -> None:
    known_ids = {
        metadata(path.read_text(encoding="utf-8")).get("ID") for path in adr_files()
    }
    for path in review_files():
        match = REVIEW_FILENAME.fullmatch(path.name)
        if not match:
            errors.append(f"invalid review filename: {relative(path)}")
            continue
        filename_id = match.group(1)
        filename_revision = int(match.group(3))
        text = path.read_text(encoding="utf-8")
        values = metadata(text)

        if values.get("Target ADR") != filename_id:
            errors.append(f"review ADR mismatch: {relative(path)}")
        try:
            target_revision = int(values.get("Target revision", ""))
        except ValueError:
            target_revision = -1
        if target_revision != filename_revision:
            errors.append(f"review revision mismatch: {relative(path)}")
        if filename_id not in known_ids:
            errors.append(f"review targets unknown ADR: {relative(path)}")
        if values.get("Review status") != "Complete":
            errors.append(f"review artifact must be complete: {relative(path)}")
        if values.get("Recommendation") not in {"Accept", "Revise", "Reject"}:
            errors.append(f"invalid review recommendation: {relative(path)}")
        for heading in REVIEW_HEADINGS:
            if heading not in text:
                errors.append(f"missing review heading '{heading}': {relative(path)}")


def main() -> int:
    errors: list[str] = []
    validate_required_paths(errors)
    validate_whitespace(errors)
    validate_local_links(errors)
    validate_adrs(errors)
    validate_reviews(errors)

    if errors:
        print(f"documentation validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "documentation validation passed: "
        f"{len(REQUIRED_PATHS)} required files, "
        f"{len(adr_files())} ADRs, {len(review_files())} reviews"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
