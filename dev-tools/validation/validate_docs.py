#!/usr/bin/env python3
"""Validate Creature Kernel's foundational documentation contracts."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "decisions"
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
    "docs/decisions/README.md",
    "docs/decisions/registry.md",
    "docs/decisions/decision-record-template.md",
    "docs/decisions/reviews/README.md",
    "docs/decisions/reviews/adversarial-review-template.md",
    "docs/decisions/reviews/fresh-reread-preamble.md",
    "dev-tools/validation/tests/test_validate_docs.py",
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

DR_FILENAME = re.compile(r"^(DR-(\d{4}))-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
REVIEW_FILENAME = re.compile(
    r"^(DR-(\d{4}))-rev-(\d{2})-review-(\d{2})\.md$"
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
METADATA_LINE = re.compile(r"^([A-Za-z][A-Za-z ]+):\s*(.*?)\s*$")
FENCE_LINE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(?:.*)$")
LEVEL_TWO_HEADING = re.compile(r"^##(?!#)(?: .*)?$")
RESPONSE_BLOCK_HEADING = re.compile(r"^### Objection response ([1-9][0-9]*)$")

DR_STATUSES = {
    "Candidate",
    "Proposed",
    "Under Review",
    "Accepted",
    "Rejected",
    "Superseded",
    "Withdrawn",
}
DR_SCOPES = {"governance", "product", "specification", "architecture"}
REVIEW_STATUSES = {"Pending", "In Progress", "Complete", "Stale"}
RESPONSE_STATUSES = {"Pending", "Complete"}
RESPONSE_DISPOSITIONS = {"Addressed", "Accepted risk", "Deferred", "Rejected"}
DR_HEADINGS = (
    "## Context",
    "## Decision",
    "## Consequences",
    "## Alternatives Considered",
    "## Adversarial Review Response",
    "## Implementation and Proof Obligations",
    "## Canonical Design Links",
    "## Reversibility and Revisit Triggers",
)
REVIEW_EVIDENCE_HEADINGS = (
    "## Canonical Review Bundle",
    "## Sources Actually Read",
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
    r"^\[(?P<id>DR-\d{4})\]\((?P<filename>[^)]+)\)$"
)
REGISTRY_DR_ID = re.compile(r"\bDR-\d{4}\b")
DR_TITLE = re.compile(r"^# (?P<id>DR-\d{4}): (?P<title>[^\n]+)$", re.MULTILINE)
PLACEHOLDER_VALUES = {"", "—", "-", "pending", "todo", "tbd"}

DR_METADATA_FIELDS = {
    "ID",
    "Scope",
    "Status",
    "Revision",
    "Decision owner",
    "Owner approval",
    "Review status",
    "Response status",
    "Date proposed",
    "Date decided",
    "Supersedes",
    "Superseded by",
}
REVIEW_METADATA_FIELDS = {
    "Target DR",
    "Target revision",
    "Review status",
    "Recommendation",
}


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _fence_marker(line: str) -> tuple[str, int] | None:
    match = FENCE_LINE.match(line)
    if not match:
        return None
    marker = match.group(1)
    return marker[0], len(marker)


def _outside_fence_lines(text: str) -> list[tuple[int, str]]:
    """Return line numbers and contents outside ordinary Markdown fences."""

    lines: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        marker = _fence_marker(line)
        if fence is not None:
            if marker is not None and marker[0] == fence[0] and marker[1] >= fence[1]:
                fence = None
            continue
        if marker is not None:
            fence = marker
            continue
        lines.append((number, line))
    return lines


def _top_level_preamble_lines(text: str) -> list[str]:
    """Read only the metadata preamble, stopping at the first level-2 heading."""

    preamble: list[str] = []
    for _, line in _outside_fence_lines(text):
        if LEVEL_TWO_HEADING.fullmatch(line):
            break
        preamble.append(line)
    return preamble


def metadata_entries(text: str) -> tuple[dict[str, str], set[str]]:
    """Return top-level metadata and duplicate keys in that metadata only."""

    values: dict[str, str] = {}
    duplicates: set[str] = set()
    for line in _top_level_preamble_lines(text):
        match = METADATA_LINE.fullmatch(line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if key in values:
            duplicates.add(key)
        values[key] = value
    return values, duplicates


def metadata(text: str) -> dict[str, str]:
    return metadata_entries(text)[0]


def scope_parts(value: str) -> set[str]:
    return {
        part.strip().casefold()
        for part in re.split(r"\s*(?:,|/|\band\b|\+|\|)\s*", value)
        if part.strip()
    }


def sections(text: str, heading: str) -> list[str]:
    """Return exact level-2 sections, excluding headings in fenced examples."""

    lines = text.splitlines()
    outside = {number: line for number, line in _outside_fence_lines(text)}
    starts = [number for number, line in outside.items() if line == heading]
    result: list[str] = []
    for start in starts:
        end = len(lines) + 1
        for number in range(start + 1, len(lines) + 1):
            line = outside.get(number)
            if line is not None and LEVEL_TWO_HEADING.fullmatch(line):
                end = number
                break
        result.append("\n".join(lines[start:end - 1]))
    return result


def section(text: str, heading: str) -> str:
    matches = sections(text, heading)
    return matches[0] if matches else ""


def exact_heading_error(
    errors: list[str], text: str, heading: str, path: Path, kind: str
) -> bool:
    count = len(sections(text, heading))
    if count == 0:
        errors.append(f"missing {kind} heading '{heading}': {relative(path)}")
        return False
    if count > 1:
        errors.append(
            f"duplicate {kind} heading '{heading}' ({count}): {relative(path)}"
        )
        return False
    return True


def markdown_links_outside_fences(text: str) -> list[str]:
    return [
        raw
        for _, line in _outside_fence_lines(text)
        for raw in MARKDOWN_LINK.findall(line)
    ]


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
    if ' "' in target:
        target = target.split(' "', 1)[0]
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return unquote(target)


def is_placeholder(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in PLACEHOLDER_VALUES or (
        len(normalized) >= 2
        and normalized.startswith("<")
        and normalized.endswith(">")
    )


def local_markdown_targets(path: Path, text: str) -> list[Path]:
    """Resolve valid local Markdown links outside code fences."""

    targets: list[Path] = []
    for raw in markdown_links_outside_fences(text):
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
            continue
        if resolved.is_file() and resolved.suffix.casefold() == ".md":
            targets.append(resolved)
    return targets


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


def dr_files() -> list[Path]:
    return sorted(
        path
        for path in DECISIONS.glob("DR-*.md")
        if path.name != "decision-record-template.md"
    )


def review_files() -> list[Path]:
    return sorted(
        path
        for path in REVIEWS.glob("DR-*.md")
        if path.name != "adversarial-review-template.md"
    )


def registry_rows(text: str) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        id_match = REGISTRY_DR_ID.search(cells[0])
        if not id_match:
            continue
        link_match = REGISTRY_LINK.fullmatch(cells[0])
        rows.append(
            {
                "line": str(number),
                "id": link_match.group("id") if link_match else id_match.group(0),
                "filename": link_match.group("filename") if link_match else None,
                "title": cells[1],
                "scope": cells[2],
                "status": cells[3],
                "revision": cells[4],
                "review": cells[5],
                "owner": cells[6],
            }
        )
    return rows


def response_blocks(text: str) -> list[dict[str, str]]:
    """Parse exact, repeatable objection response blocks from one section."""

    lines = text.splitlines()
    outside = {number: line for number, line in _outside_fence_lines(text)}
    starts = [
        number
        for number, line in outside.items()
        if RESPONSE_BLOCK_HEADING.fullmatch(line)
    ]
    blocks: list[dict[str, str]] = []
    field_patterns = {
        "Objection": re.compile(r"^Objection:\s*(.*?)\s*$"),
        "Response": re.compile(r"^Response:\s*(.*?)\s*$"),
        "Disposition": re.compile(r"^Disposition:\s*(.*?)\s*$"),
    }
    for start in starts:
        end = len(lines) + 1
        for number in range(start + 1, len(lines) + 1):
            line = outside.get(number)
            if line is not None and (
                LEVEL_TWO_HEADING.fullmatch(line)
                or RESPONSE_BLOCK_HEADING.fullmatch(line)
            ):
                end = number
                break
        block_lines = [
            outside[number]
            for number in range(start + 1, end)
            if number in outside
        ]
        fields: dict[str, str] = {}
        for field, pattern in field_patterns.items():
            matches = [pattern.fullmatch(line) for line in block_lines]
            values = [match.group(1).strip() for match in matches if match]
            if len(values) == 1:
                fields[field] = values[0]
            elif len(values) > 1:
                fields[field] = "__duplicate__"
        blocks.append(fields)
    return blocks


def current_revision_reviews(dr_id: str, revision: int) -> list[Path]:
    """Find only reviews whose complete filename parses to this ID/revision."""

    matches: list[Path] = []
    for path in review_files():
        match = REVIEW_FILENAME.fullmatch(path.name)
        if match and match.group(1) == dr_id and int(match.group(3)) == revision:
            matches.append(path)
    return matches


def validate_decision_records(errors: list[str]) -> None:
    registry_path = DECISIONS / "registry.md"
    registry = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
    rows = registry_rows(registry)
    rows_by_id: dict[str, list[dict[str, str | None]]] = {}
    seen_registry_ids: set[str] = set()
    for row in rows:
        row_id = row["id"]
        if row_id in seen_registry_ids:
            errors.append(f"duplicate registry DR ID: {row_id}")
        if row_id is not None:
            seen_registry_ids.add(row_id)
            rows_by_id.setdefault(row_id, []).append(row)
        if row["filename"] is None:
            errors.append(
                "registry DR row must link a DR filename: "
                f"{relative(registry_path)}:{row['line']}"
            )

    files_by_filename = {path.name: path for path in dr_files()}
    files_by_id: dict[str, Path] = {}
    for path in dr_files():
        match = DR_FILENAME.fullmatch(path.name)
        if match:
            if match.group(1) in files_by_id:
                errors.append(f"duplicate DR ID in filenames: {match.group(1)}")
            files_by_id[match.group(1)] = path

    for row in rows:
        row_id = row["id"]
        filename = row["filename"]
        if row_id not in files_by_id:
            errors.append(f"registry DR has no corresponding file: {row_id}")
        if filename is not None and filename not in files_by_filename:
            errors.append(f"registry DR file is missing: {filename}")
        if filename is not None:
            filename_match = DR_FILENAME.fullmatch(Path(filename).name)
            if filename_match and filename_match.group(1) != row_id:
                errors.append(
                    f"registry DR ID does not match linked filename at "
                    f"{relative(registry_path)}:{row['line']}: "
                    f"{row_id} vs {filename}"
                )

    seen_ids: set[str] = set()
    for path in dr_files():
        match = DR_FILENAME.fullmatch(path.name)
        if not match:
            errors.append(f"invalid DR filename: {relative(path)}")
            continue
        filename_id = match.group(1)
        text = path.read_text(encoding="utf-8")
        values, duplicate_keys = metadata_entries(text)
        for key in sorted(duplicate_keys & DR_METADATA_FIELDS):
            errors.append(f"duplicate top-level DR metadata '{key}': {relative(path)}")
        dr_id = values.get("ID")

        if dr_id != filename_id:
            errors.append(
                f"DR ID mismatch in {relative(path)}: expected {filename_id}, got {dr_id!r}"
            )
        if dr_id in seen_ids:
            errors.append(f"duplicate DR ID: {dr_id}")
        if dr_id:
            seen_ids.add(dr_id)

        expected_title = f"# {filename_id}:"
        if not text.startswith(expected_title):
            errors.append(f"DR title must start with '{expected_title}': {relative(path)}")

        for field in DR_METADATA_FIELDS:
            if field not in values:
                errors.append(f"missing DR metadata '{field}': {relative(path)}")

        status = values.get("Status")
        scope = values.get("Scope", "")
        review_status = values.get("Review status")
        response_status = values.get("Response status")
        if "Status" in values and status not in DR_STATUSES:
            errors.append(f"invalid DR status '{status}': {relative(path)}")
        invalid_scopes = scope_parts(scope) - DR_SCOPES
        if not scope or invalid_scopes:
            errors.append(f"invalid DR scope '{scope}': {relative(path)}")
        if "Review status" in values and review_status not in REVIEW_STATUSES:
            errors.append(f"invalid review status '{review_status}': {relative(path)}")
        if "Response status" in values and response_status not in RESPONSE_STATUSES:
            errors.append(f"invalid response status '{response_status}': {relative(path)}")

        registry_matches = rows_by_id.get(filename_id, [])
        if not registry_matches:
            errors.append(f"DR missing from registry: {filename_id}")
        elif len(registry_matches) != 1:
            errors.append(
                f"DR must have exactly one registry row: {filename_id} "
                f"(found {len(registry_matches)})"
            )
        else:
            row = registry_matches[0]
            dr_title_match = DR_TITLE.match(text)
            dr_title = dr_title_match.group("title") if dr_title_match else None
            comparisons = (
                ("ID", row["id"], dr_id),
                ("linked filename", row["filename"], path.name),
                ("title", row["title"], dr_title),
                ("scope", row["scope"], values.get("Scope")),
                ("status", row["status"], status),
                ("revision", row["revision"], values.get("Revision")),
                ("review status", row["review"], review_status),
                ("decision owner", row["owner"], values.get("Decision owner")),
            )
            for field, registry_value, dr_value in comparisons:
                if registry_value != dr_value:
                    errors.append(
                        f"DR registry {field} mismatch for {filename_id}: "
                        f"registry={registry_value!r}, DR={dr_value!r}"
                    )

        revision_text = values.get("Revision", "")
        try:
            revision = int(revision_text)
            if revision < 1:
                raise ValueError
        except ValueError:
            errors.append(f"DR revision must be a positive integer: {relative(path)}")
            revision = 0

        for heading in DR_HEADINGS:
            exact_heading_error(errors, text, heading, path, "DR")

        if status == "Accepted":
            expected_approval = f"Approved by {values.get('Decision owner')}"
            if values.get("Owner approval") != expected_approval:
                errors.append(
                    "accepted DR requires exact owner approval "
                    f"'{expected_approval}': {relative(path)}"
                )
            if review_status != "Complete":
                errors.append(f"accepted DR requires complete review: {relative(path)}")
            if values.get("Response status") != "Complete":
                errors.append(
                    f"accepted DR requires complete response status: {relative(path)}"
                )
            if is_placeholder(values.get("Date decided", "")):
                errors.append(f"accepted DR requires decision date: {relative(path)}")
            canonical = section(text, "## Canonical Design Links")
            if not markdown_links_outside_fences(canonical):
                errors.append(f"accepted DR requires canonical links: {relative(path)}")
            if review_status == "Complete" and revision:
                matching_reviews = current_revision_reviews(filename_id, revision)
                if not matching_reviews:
                    errors.append(
                        f"accepted DR lacks review for revision {revision}: {relative(path)}"
                    )
                response = section(text, "## Adversarial Review Response")
                linked_review = False
                for raw in markdown_links_outside_fences(response):
                    target = normalize_link(raw).split("#", 1)[0]
                    if not target:
                        continue
                    resolved = (path.parent / target).resolve()
                    if any(resolved == review.resolve() for review in matching_reviews):
                        linked_review = True
                        break
                if not linked_review:
                    errors.append(
                        "accepted DR review response must link a matching review "
                        f"file for revision {revision}: {relative(path)}"
                    )
                blocks = response_blocks(response)
                if not blocks:
                    errors.append(
                        "accepted DR requires at least one objection response block: "
                        f"{relative(path)}"
                    )
                # Shape, fields, and identity are mechanical; response
                # adequacy and disposition remain human review questions.
                for number, block in enumerate(blocks, start=1):
                    for field in ("Objection", "Response", "Disposition"):
                        value = block.get(field)
                        if (
                            value is None
                            or value == "__duplicate__"
                            or is_placeholder(value)
                        ):
                            errors.append(
                                f"accepted DR objection response {number} requires "
                                f"non-placeholder '{field}': {relative(path)}"
                            )
                    disposition = block.get("Disposition")
                    if disposition not in RESPONSE_DISPOSITIONS:
                        errors.append(
                            f"accepted DR objection response {number} has invalid "
                            f"disposition {disposition!r}: {relative(path)}"
                        )


def validate_reviews(errors: list[str]) -> None:
    known_ids = {
        metadata(path.read_text(encoding="utf-8")).get("ID") for path in dr_files()
    }
    dr_paths_by_id = {
        match.group(1): path
        for path in dr_files()
        if (match := DR_FILENAME.fullmatch(path.name))
    }
    for path in review_files():
        match = REVIEW_FILENAME.fullmatch(path.name)
        if not match:
            errors.append(f"invalid review filename: {relative(path)}")
            continue
        filename_id = match.group(1)
        filename_revision = int(match.group(3))
        text = path.read_text(encoding="utf-8")
        values, duplicate_keys = metadata_entries(text)
        for key in sorted(duplicate_keys & REVIEW_METADATA_FIELDS):
            errors.append(
                f"duplicate top-level review metadata '{key}': {relative(path)}"
            )

        for field in REVIEW_METADATA_FIELDS:
            if field not in values:
                errors.append(f"missing review metadata '{field}': {relative(path)}")

        if values.get("Target DR") != filename_id:
            errors.append(f"review DR mismatch: {relative(path)}")
        try:
            target_revision = int(values.get("Target revision", ""))
        except ValueError:
            target_revision = -1
        if target_revision != filename_revision:
            errors.append(f"review revision mismatch: {relative(path)}")
        if filename_id not in known_ids:
            errors.append(f"review targets unknown DR: {relative(path)}")
        if values.get("Review status") != "Complete":
            errors.append(f"review artifact must be complete: {relative(path)}")
        if values.get("Recommendation") not in {"Accept", "Revise", "Reject"}:
            errors.append(f"invalid review recommendation: {relative(path)}")
        for heading in REVIEW_HEADINGS:
            exact_heading_error(errors, text, heading, path, "review")

        if values.get("Review status") == "Complete":
            target_dr = dr_paths_by_id.get(filename_id)
            for heading in REVIEW_EVIDENCE_HEADINGS:
                if not exact_heading_error(errors, text, heading, path, "review"):
                    continue
                evidence = section(text, heading)
                targets = local_markdown_targets(path, evidence)
                if not targets:
                    errors.append(
                        f"complete review requires a local Markdown link in "
                        f"'{heading}': {relative(path)}"
                    )
                # This checks evidence identity and linkability only; humans
                # judge whether the bundle was complete and actually read.
                if target_dr is None or not any(
                    target == target_dr.resolve() for target in targets
                ):
                    errors.append(
                        f"complete review '{heading}' must link target DR "
                        f"{filename_id}: {relative(path)}"
                    )


def main() -> int:
    errors: list[str] = []
    validate_required_paths(errors)
    validate_whitespace(errors)
    validate_local_links(errors)
    validate_decision_records(errors)
    validate_reviews(errors)

    if errors:
        print(f"documentation validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "documentation validation passed: "
        f"{len(REQUIRED_PATHS)} required files, "
        f"{len(dr_files())} DRs, {len(review_files())} reviews"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
