from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import phase2_adjudicator as adjudicator
import run_development


def observations(members: list[dict[str, object]]) -> dict[str, object]:
    return {"root": {}, "members": members, "tolerances": {}, "providers": {}}


def compared(outcomes: list[str]) -> dict[str, object]:
    return {
        "outcome": "compared",
        "attachments": [{"outcome": outcome} for outcome in outcomes],
    }


def skipped(cause: dict[str, object]) -> dict[str, object]:
    return {"outcome": "skipped", "attachments": [], "skip": {"code": "skip", "cause": cause}}


class AdjudicatorTests(unittest.TestCase):
    def test_unknown_and_invalid_tolerance_overrides_are_rejected(self) -> None:
        with self.assertRaisesRegex(run_development.DevelopmentRunError, "unknown override field"):
            run_development._profile_tolerances("strict", {"unknown": Decimal("0")})
        with self.assertRaisesRegex(run_development.DevelopmentRunError, "invalid override value"):
            run_development._profile_tolerances("strict", {"translation_absolute": True})

    def test_classification_algebra(self) -> None:
        self.assertEqual(adjudicator.classify_observations(observations([compared(["agree"])])), ("agree", None))
        self.assertEqual(adjudicator.classify_observations(observations([compared(["conflict"])])), ("conflict", None))
        cause = {"code": "frame", "failure": "provider-unavailable", "stage": "scaled-component"}
        classification, observed = adjudicator.classify_observations(observations([skipped(cause)]))
        self.assertEqual(classification, "skipped")
        self.assertEqual(observed, cause)
        self.assertEqual(
            adjudicator.classify_observations(observations([compared(["conflict"]), skipped(cause)])),
            ("incomplete", None),
        )
        second = {"code": "frame", "failure": "gate-rejected", "stage": "input"}
        self.assertEqual(
            adjudicator.classify_observations(observations([skipped(cause), skipped(second)])),
            ("incomplete", None),
        )

    def test_missing_compared_evidence_and_malformed_response_fail_closed(self) -> None:
        with self.assertRaisesRegex(adjudicator.AdjudicationError, "missing-evidence"):
            adjudicator.classify_observations(observations([compared([])]))
        with self.assertRaisesRegex(adjudicator.AdjudicationError, "response-status"):
            adjudicator.classify_response({"protocol_id": "p", "request_id": "r", "status": "error", "error": "bad"})

    def test_cause_matching_uses_stable_subset_only(self) -> None:
        observed = {
            "code": "frame",
            "failure": "provider-unavailable",
            "operation": "div",
            "stage": "scaled-component",
            "index": 0,
            "location": {"member": "display-only"},
        }
        expected = {"code": "frame", "failure": "provider-unavailable", "operation": "div"}
        self.assertTrue(adjudicator.cause_matches(observed, expected))
        self.assertFalse(adjudicator.cause_matches(observed, {"code": "other"}))
        self.assertFalse(adjudicator.cause_matches(observed, None))
        self.assertFalse(adjudicator.cause_matches({"code": "frame", "index": 0}, {"code": "frame", "index": False}))
        with self.assertRaisesRegex(adjudicator.AdjudicationError, "cause-size"):
            adjudicator.stable_cause({"code": "frame", "failure": "x" * 257})


class DevelopmentRunnerE2ETests(unittest.TestCase):
    def test_error_report_does_not_duplicate_a_typed_error_code(self) -> None:
        report = run_development._error_report(
            run_development.DevelopmentRunError("file-type", "candidate is missing")
        )
        self.assertEqual(report["summary"]["failures"], ["file-type:candidate is missing"])

    def test_real_subprocess_runs_all_48_and_reports_mismatch_and_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            counter = root / "count"
            candidate = root / "candidate.py"
            candidate.write_text(
                """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

counter = Path(sys.argv[1])
count = int(counter.read_text() or '0') if counter.exists() else 0
for line in sys.stdin:
    count += 1
    counter.write_text(str(count))
    request = json.loads(line)
    if count == 1:
        members = []
    else:
        members = [{'outcome': 'compared', 'attachments': [{'outcome': 'agree'}]}]
    response = {
        'protocol_id': 'ck.exp-0002.r3-authored-conflict-candidate-response-1',
        'request_id': request['request_id'],
        'status': 'observed',
        'observations': {'root': {}, 'members': members, 'tolerances': {}, 'providers': {}},
    }
    print(json.dumps(response, separators=(',', ':')), flush=True)
""",
                encoding="utf-8",
            )
            candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR)
            report = run_development.run_development([str(candidate), str(counter)])
            self.assertEqual(counter.read_text(encoding="utf-8"), "48")
            self.assertEqual(report["run_status"], "fail")
            self.assertEqual(report["summary"]["planned"], 48)
            self.assertEqual(report["summary"]["entries"], 48)
            self.assertEqual(report["summary"]["requests_sent"], 48)
            self.assertEqual(report["summary"]["responses_received"], 48)
            self.assertGreater(report["summary"]["failed"], 0)
            self.assertEqual(report["entries"][0]["observed_classification"], "incomplete")
            self.assertTrue(all("request_sha256" in entry and "response_sha256" in entry for entry in report["entries"]))
            self.assertTrue(report["non_authoritative"])
            self.assertEqual(report["profile_selection"], "none")
            self.assertEqual(report["r3_activation"], "inactive")

    def test_answers_then_nonzero_exit_is_reported_as_terminal_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "candidate.py"
            candidate.write_text(
                """#!/usr/bin/env python3
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    response = {
        'protocol_id': 'ck.exp-0002.r3-authored-conflict-candidate-response-1',
        'request_id': request['request_id'],
        'status': 'observed',
        'observations': {'root': {}, 'members': [{'outcome': 'compared', 'attachments': [{'outcome': 'agree'}]}], 'tolerances': {}, 'providers': {}},
    }
    print(json.dumps(response, separators=(',', ':')), flush=True)
sys.exit(7)
""",
                encoding="utf-8",
            )
            candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR)
            report = run_development.run_development([str(candidate)])
            self.assertEqual(report["summary"]["requests_sent"], 48)
            self.assertEqual(report["summary"]["responses_received"], 48)
            self.assertEqual(report["run_status"], "fail")
            self.assertIn("candidate-exit:7", report["summary"]["failures"])

    def test_oversized_cause_is_per_entry_incomplete_with_bounded_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "candidate.py"
            candidate.write_text(
                """#!/usr/bin/env python3
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    response = {
        'protocol_id': 'ck.exp-0002.r3-authored-conflict-candidate-response-1',
        'request_id': request['request_id'],
        'status': 'observed',
        'observations': {'root': {}, 'members': [{'outcome': 'skipped', 'attachments': [], 'skip': {'code': 'skip', 'cause': {'code': 'frame', 'failure': 'x' * 10000}}}], 'tolerances': {}, 'providers': {}},
    }
    print(json.dumps(response, separators=(',', ':')), flush=True)
""",
                encoding="utf-8",
            )
            candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR)
            report = run_development.run_development([str(candidate)])
            self.assertEqual(report["summary"]["entries"], 48)
            self.assertEqual(report["summary"]["requests_sent"], 48)
            self.assertEqual(report["summary"]["responses_received"], 48)
            self.assertEqual(report["summary"]["classification_totals"], {"incomplete": 48})
            self.assertTrue(all(entry["request_sha256"] and entry["response_sha256"] for entry in report["entries"]))
            self.assertEqual(report["run_status"], "fail")

    def test_cli_candidate_arg_option_like_value_reaches_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "candidate.py"
            marker = root / "marker"
            candidate.write_text(
                """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

if sys.argv[1] != '--sentinel':
    raise SystemExit(9)
Path(sys.argv[2]).write_text('seen')
for line in sys.stdin:
    request = json.loads(line)
    print(json.dumps({'protocol_id': 'ck.exp-0002.r3-authored-conflict-candidate-response-1', 'request_id': request['request_id'], 'status': 'observed', 'observations': {'root': {}, 'members': [{'outcome': 'compared', 'attachments': [{'outcome': 'agree'}]}], 'tolerances': {}, 'providers': {}}}, separators=(',', ':')), flush=True)
""",
                encoding="utf-8",
            )
            candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(Path(run_development.__file__).resolve().parent)
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(run_development.__file__).resolve()),
                    "--candidate",
                    str(candidate),
                    "--candidate-arg=--sentinel",
                    "--candidate-arg",
                    str(marker),
                ],
                capture_output=True,
                text=True,
                env=environment,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "seen")
            self.assertEqual(json.loads(result.stdout)["summary"]["requests_sent"], 48)


if __name__ == "__main__":
    unittest.main()
