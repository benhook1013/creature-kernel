"""Focused in-memory tests for the Phase 3 oracle and actual wire scorer."""

from __future__ import annotations

import copy
import json
import unittest
from fractions import Fraction

import phase3_oracle as oracle
import phase3_scorer as scorer
from phase3_common import (
    REQUEST_PROTOCOL_ID, RESPONSE_PROTOCOL_ID, ProtocolError, as_fraction,
    RationalInterval, float_to_bits, fraction_to_binary64_bits, parse_json,
)


def address(role: str, anchors: list[str] | None = None, kind: str = "part") -> dict[str, object]:
    return {"namespace": "synthetic", "anchors": anchors or [], "kind": kind, "role": role}


def source_text(*, root_t: list[float] | None = None, root_q: list[float] | None = None, host_q: list[float] | None = None, offset_t: list[float] | None = None, descendants: list[list[float]] | None = None, basis: dict[str, object] | None = None) -> str:
    root = address("tail_root", ["tail"])
    parts: list[dict[str, object]] = [{"address": root, "containment": {"parent": root}, "placement": {"translation": root_t or [0, 0, 0], "rotation_xyzw": root_q or [0, 0, 0, 1]}}]
    parent = root
    for index, translation in enumerate(descendants or []):
        child = address(f"link-{index}", ["tail", str(index)])
        parts.append({"address": child, "containment": {"parent": parent}, "placement": {"translation": translation, "rotation_xyzw": [0, 0, 0, 1]}})
        parent = child
    host = address("tail_mount", [], "socket")
    mating = address("tail_mount", ["tail"], "socket")
    attachment = address("tail_mount", ["tail"], "attachment")
    value = {
        "source": {"document": "synthetic-doc", "namespace": "synthetic"},
        "basis": basis or {"up": "+y", "forward": "+z", "handedness": "right", "length_unit": "metre"},
        "body": {
            "parts": parts, "joints": [], "frames": [], "landmarks": [],
            "sockets": [
                {"address": host, "owner": root, "interface_frame": {"translation": [0, 0, 0], "rotation_xyzw": host_q or [0, 0, 0, 1]}},
                {"address": mating, "owner": parent, "interface_frame": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}},
            ],
            "attachments": [{"address": attachment, "host": host, "mating": mating, "offset": {"translation": offset_t or [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}}],
        },
    }
    return json.dumps(value, separators=(",", ":"))


def request(request_id: str = "synthetic-1", *, metric: str = "translation", absolute: object = 2, half_chord: object = 1) -> dict[str, object]:
    return {
        "protocol_id": REQUEST_PROTOCOL_ID,
        "request_id": request_id,
        "operation": "observe-authored-conflict",
        "resource_profile": "ordinary",
        "source": source_text(),
        "tolerances": {"translation_absolute": absolute, "translation_relative": 0, "rotation_half_chord": half_chord},
        "providers": {"gate": "allow", "arithmetic": "native", "sqrt": "native", "environment": "unattested-no-probe-v1"},
        "metric": metric,
    }


def transform(x: float = 0, q: list[float] | None = None) -> dict[str, object]:
    return {"translation": [float_to_bits(x), float_to_bits(0), float_to_bits(0)], "rotation_xyzw": [float_to_bits(item) for item in (q or [0, 0, 0, 1])]}


def wire_response(req: dict[str, object], truth: dict[str, object], *, authored: dict[str, object] | None = None, derived: dict[str, object] | None = None, final_output: dict[str, object] | None = None, outcome: str = "agree") -> bytes:
    identity = truth["source_identity"]
    provenance_truth = truth["provenance"]
    identity_transform = transform()
    path = provenance_truth.get("root_to_mating_owner_path", [])
    provenance = {key: copy.deepcopy(provenance_truth[key]) for key in ("attachment", "root", "host_socket", "mating_socket", "host_owner", "mating_owner")}
    provenance.update({"offset": identity_transform, "root_to_mating_owner_path": copy.deepcopy(path)})
    equation_steps = [{"operation": operation, "output": copy.deepcopy(identity_transform)} for operation in ("attachment-containment", "attachment-mating-socket", "attachment-host-offset", "attachment-inverse", "attachment-equation")]
    if final_output is not None:
        equation_steps[-1]["output"] = copy.deepcopy(final_output)
    equation = {
        "host_socket_local": identity_transform,
        "mating_socket_local": identity_transform,
        "root_to_mating_owner_part_locals": [{"address": copy.deepcopy(item), "local": identity_transform} for item in path],
        "equation_steps": equation_steps,
    }
    attachment = {"provenance": provenance, "equation": equation, "authored_root_local": authored or transform(), "derived_root_local": derived or transform(), "outcome": outcome}
    tolerances = req["tolerances"]
    tolerance_bits = {key: fraction_to_binary64_bits(as_fraction(tolerances[key])) for key in ("translation_absolute", "translation_relative", "rotation_half_chord")}
    providers = req["providers"]
    observations = {
        "root": identity,
        "members": [{"identity": identity, "role": "root", "outcome": "compared", "attachments": [attachment]}],
        "tolerances": tolerance_bits,
        "providers": {
            "gate": {"selection": providers["gate"], "attestation": "unattested"},
            "arithmetic": {"selection": providers["arithmetic"], "attestation": "unattested"},
            "sqrt": {"selection": providers["sqrt"], "attestation": "unattested"},
            "environment": providers["environment"],
        },
    }
    return (json.dumps({"protocol_id": RESPONSE_PROTOCOL_ID, "request_id": req["request_id"], "status": "observed", "observations": observations}, separators=(",", ":")) + "\n").encode()


def skipped_response(req: dict[str, object], truth: dict[str, object], *, location: dict[str, object] | None = None, member_outcome: str = "skipped") -> bytes:
    identity = truth["source_identity"]
    cause = {"code": scorer.FRAME_VALUE_QUATERNION_CODE, "failure": "zero-quaternion", "location": location or truth["domain"]["zero_quaternion_locations"][0]}
    if member_outcome == "compared":
        nested = json.loads(wire_response(req, truth))
        attachment = nested["observations"]["members"][0]["attachments"][0]
        attachment.update({"outcome": "skipped", "component": "rotation", "code": scorer.FRAME_VALUE_QUATERNION_CODE, "detail": "synthetic", "cause": {**cause, "component": "rotation"}})
        member = {"identity": identity, "role": "root", "outcome": "compared", "attachments": [attachment]}
    else:
        member = {"identity": identity, "role": "root", "outcome": member_outcome, "attachments": [], "skip": {"code": scorer.FRAME_VALUE_QUATERNION_CODE, "detail": "synthetic", "cause": cause}}
    tolerances = req["tolerances"]
    observations = {
        "root": identity, "members": [member],
        "tolerances": {key: fraction_to_binary64_bits(as_fraction(tolerances[key])) for key in tolerances},
        "providers": {"gate": {"selection": "allow", "attestation": "unattested"}, "arithmetic": {"selection": "native", "attestation": "unattested"}, "sqrt": {"selection": "native", "attestation": "unattested"}, "environment": "unattested-no-probe-v1"},
    }
    return (json.dumps({"protocol_id": RESPONSE_PROTOCOL_ID, "request_id": req["request_id"], "status": "observed", "observations": observations}, separators=(",", ":")) + "\n").encode()


class OracleTests(unittest.TestCase):
    def test_translation_basis_unit_and_four_edges(self) -> None:
        converted = {"up": "+z", "forward": "+x", "handedness": "left", "length_unit": "centimetre"}
        result = oracle.evaluate_source(source_text(descendants=[[100, 0, 0]], basis=converted), "translation")
        self.assertEqual(result["I_truth"]["lower"], "1")
        four = oracle.evaluate_source(source_text(descendants=[[0, 0, 0]] * 4), "translation")
        self.assertEqual(four["domain"]["path_edges"], 4)

    def test_nonunit_quaternion_and_q_neg_q(self) -> None:
        result = oracle.evaluate_source(source_text(root_q=[0, 0, 0, 0.5]), "rotation")
        self.assertEqual(result["status"], "admitted")
        self.assertEqual(result["I_truth"]["lower"], "0")
        negative = oracle.evaluate_source(source_text(root_q=[0, 0, 0, -1]), "rotation")
        self.assertEqual(negative["I_truth"]["upper"], "0")

    def test_nonunit_quaternion_projective_representatives_rotate_translation_identically(self) -> None:
        half = oracle.evaluate_source(source_text(host_q=[0, 0, 0.5, 0.5], offset_t=[1, 0, 0]), "translation")
        whole = oracle.evaluate_source(source_text(host_q=[0, 0, 1, 1], offset_t=[1, 0, 0]), "translation")
        self.assertEqual(half["status"], "admitted")
        self.assertEqual(half["derived_root_local"]["translation_exact"], whole["derived_root_local"]["translation_exact"])
        self.assertEqual(half["I_truth"], whole["I_truth"])

    def test_kappa_pair_999999(self) -> None:
        result = oracle.evaluate_source(source_text(descendants=[[0.5, 0, 0], [-0.499999, 0, 0]]), "translation")
        self.assertEqual(result["domain"]["kappa_pair_exact"], "999999/1")

    def test_sqrt_fixture_shape_in_memory(self) -> None:
        fixture = {"vectors": [{"kind": "exact-square", "radicand": "4", "exact_root": "2"}, {"kind": "certified-bracket", "radicand": "2", "lower": "1", "upper": "2"}, {"kind": "scale-metamorphic", "base_radicand": "2", "scale": "4", "scaled_radicand": "32", "expected": {"operation": "root-scale", "factor": "4"}}]}
        self.assertEqual(oracle.verify_sqrt_vectors(fixture)["checked"], 3)

    def test_huge_decimal_exponents_rejected_before_fraction(self) -> None:
        for token in ("1e999999", "1e-999999"):
            with self.assertRaises(ProtocolError) as context:
                parse_json('{"x":' + token + '}')
            self.assertEqual(context.exception.code, "numeric-exponent-too-large")


class ScorerTests(unittest.TestCase):
    def test_actual_nested_success_and_request_echo(self) -> None:
        req = request()
        truth = oracle.evaluate_source(req["source"], "translation")
        response = wire_response(req, truth)
        self.assertEqual(scorer.score_response(req, truth, response, expected_class="agree")["status"], "supported")
        wrong = json.loads(response)
        wrong["request_id"] = "synthetic-other"
        self.assertEqual(scorer.score_response(req, truth, json.dumps(wrong).encode())["cause"]["code"], "response-request-id-mismatch")

    def test_exact_translation_threshold_is_inclusive(self) -> None:
        threshold = 0.5
        req = request(absolute=threshold)
        req["source"] = source_text(root_t=[threshold, 0, 0])
        truth = oracle.evaluate_source(req["source"], "translation")
        response = wire_response(req, truth, authored=transform(threshold), derived=transform(0), outcome="agree")
        self.assertEqual(scorer.score_response(req, truth, response, expected_class="agree")["status"], "supported")

    def test_exact_rotation_threshold_and_certified_straddle(self) -> None:
        req = request(metric="rotation", half_chord=0)
        truth = oracle.evaluate_source(req["source"], "rotation")
        response = wire_response(req, truth, outcome="agree")
        self.assertEqual(scorer.score_response(req, truth, response, expected_class="agree")["status"], "supported")
        interval = RationalInterval(Fraction(9, 10), Fraction(11, 10))
        self.assertEqual(scorer.classify_candidate_interval(interval, Fraction(1)), "straddling")

    def test_interval_cap_and_failed_precedence(self) -> None:
        req = request(absolute=2)
        truth = oracle.evaluate_source(req["source"], "translation")
        cap = wire_response(req, truth, authored=transform(9e-11), derived=transform(-9e-11), final_output=transform(-9e-11), outcome="agree")
        self.assertEqual(scorer.score_response(req, truth, cap, expected_class="agree")["status"], "inconclusive")
        wrong = wire_response(req, truth, authored=transform(0), derived=transform(10), final_output=transform(10), outcome="agree")
        result = scorer.score_response(req, truth, wrong, expected_class="agree")
        self.assertEqual(result["status"], "failed")

    def test_root_transforms_are_bound_before_interval_logic(self) -> None:
        req = request(absolute=2)
        truth = oracle.evaluate_source(req["source"], "translation")
        tiny = wire_response(req, truth, authored=transform(5e-11), derived=transform(), outcome="agree")
        self.assertEqual(scorer.score_response(req, truth, tiny)["status"], "supported")
        fabricated_authored = wire_response(req, truth, authored=transform(1e-9), derived=transform(), outcome="agree")
        authored_result = scorer.score_response(req, truth, fabricated_authored)
        self.assertEqual((authored_result["status"], authored_result["cause"]["code"]), ("failed", "witness-mismatch"))
        fabricated_derived = wire_response(req, truth, authored=transform(), derived=transform(5e-11), outcome="agree")
        derived_result = scorer.score_response(req, truth, fabricated_derived)
        self.assertEqual((derived_result["status"], derived_result["cause"]["code"]), ("failed", "witness-mismatch"))

    def test_complete_wrong_witness_fails_but_incomplete_is_inconclusive(self) -> None:
        req = request()
        truth = oracle.evaluate_source(req["source"], "translation")
        base = json.loads(wire_response(req, truth))
        mutations = []
        wrong_root = copy.deepcopy(base)
        wrong_root["observations"]["members"][0]["identity"]["document"] = "wrong"
        mutations.append(wrong_root)
        wrong_provenance = copy.deepcopy(base)
        wrong_provenance["observations"]["members"][0]["attachments"][0]["provenance"]["attachment"]["role"] = "wrong"
        mutations.append(wrong_provenance)
        wrong_operation = copy.deepcopy(base)
        wrong_operation["observations"]["members"][0]["attachments"][0]["equation"]["equation_steps"][-1]["operation"] = "wrong"
        mutations.append(wrong_operation)
        wrong_output = copy.deepcopy(base)
        wrong_output["observations"]["members"][0]["attachments"][0]["equation"]["equation_steps"][-1]["output"] = transform(1)
        mutations.append(wrong_output)
        duplicate = copy.deepcopy(base)
        duplicate["observations"]["members"][0]["attachments"].append(copy.deepcopy(duplicate["observations"]["members"][0]["attachments"][0]))
        mutations.append(duplicate)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                result = scorer.score_response(req, truth, json.dumps(value).encode())
                self.assertEqual((result["status"], result["cause"]["code"]), ("failed", "witness-mismatch"))
        incomplete = copy.deepcopy(base)
        del incomplete["observations"]["members"][0]["attachments"][0]["equation"]
        self.assertEqual(scorer.score_response(req, truth, json.dumps(incomplete).encode())["status"], "inconclusive")

    def test_zero_quaternion_location_and_outcome(self) -> None:
        req = request()
        req["source"] = source_text(root_q=[0, 0, 0, 0])
        truth = oracle.evaluate_source(req["source"], "translation")
        good = skipped_response(req, truth)
        self.assertEqual(scorer.score_response(req, truth, good)["status"], "supported")
        attachment_req = request("synthetic-attachment-zero")
        attachment_req["source"] = source_text(host_q=[0, 0, 0, 0])
        attachment_truth = oracle.evaluate_source(attachment_req["source"], "translation")
        compared_attachment_skip = skipped_response(attachment_req, attachment_truth, member_outcome="compared")
        self.assertEqual(scorer.score_response(attachment_req, attachment_truth, compared_attachment_skip)["status"], "supported")
        contradictory_member_skip = json.loads(compared_attachment_skip)
        contradictory_member_skip["observations"]["members"][0]["skip"] = {
            "code": scorer.FRAME_VALUE_QUATERNION_CODE,
            "detail": "contradictory synthetic member skip",
            "cause": {
                "code": scorer.FRAME_VALUE_QUATERNION_CODE,
                "failure": "zero-quaternion",
                "location": attachment_truth["domain"]["zero_quaternion_locations"][0],
            },
        }
        contradiction = scorer.score_response(attachment_req, attachment_truth, json.dumps(contradictory_member_skip).encode())
        self.assertEqual(contradiction["status"], "failed")
        self.assertEqual(contradiction["cause"], {"code": "typed-control-mismatch", "failure": "compared-member-skip-contradiction"})
        bad_location = copy.deepcopy(truth["domain"]["zero_quaternion_locations"][0])
        bad_location["slot"]["address"]["role"] = "wrong"
        self.assertEqual(scorer.score_response(req, truth, skipped_response(req, truth, location=bad_location))["status"], "failed")
        missing_location = json.loads(good)
        del missing_location["observations"]["members"][0]["skip"]["cause"]["location"]
        self.assertEqual(scorer.score_response(req, truth, json.dumps(missing_location).encode())["status"], "inconclusive")
        wrong_outcome = json.loads(good)
        wrong_outcome["observations"]["members"][0]["outcome"] = "compared"
        self.assertEqual(scorer.score_response(req, truth, json.dumps(wrong_outcome).encode())["status"], "failed")

    def test_typed_control_header_and_decimal_cause_index(self) -> None:
        req = request()
        req["source"] = source_text(root_q=[0, 0, 0, 0])
        truth = oracle.evaluate_source(req["source"], "translation")
        indexed = json.loads(skipped_response(req, truth))
        indexed["observations"]["members"][0]["skip"]["cause"]["index"] = 7
        result = scorer.score_response(req, truth, json.dumps(indexed).encode())
        self.assertEqual((result["status"], result["cause"]["index"]), ("supported", 7))
        observed = scorer.score_response(req, truth, json.dumps(indexed).encode(), observation_only=True)
        self.assertEqual(observed["status"], "observation")
        wrong_header = copy.deepcopy(indexed)
        wrong_header["observations"]["root"]["document"] = "wrong"
        self.assertEqual(scorer.score_response(req, truth, json.dumps(wrong_header).encode())["status"], "failed")
        incomplete_header = copy.deepcopy(indexed)
        del incomplete_header["observations"]["providers"]
        self.assertEqual(scorer.score_response(req, truth, json.dumps(incomplete_header).encode())["status"], "inconclusive")

    def test_malformed_typed_control_locations_are_inconclusive(self) -> None:
        req = request()
        req["source"] = source_text(root_q=[0, 0, 0, 0])
        truth = oracle.evaluate_source(req["source"], "translation")
        base = json.loads(skipped_response(req, truth))
        malformed = copy.deepcopy(base)
        malformed["observations"]["members"][0]["skip"]["cause"]["location"] = []
        self.assertEqual(scorer.score_response(req, truth, json.dumps(malformed).encode())["status"], "inconclusive")
        missing_slot = copy.deepcopy(base)
        del missing_slot["observations"]["members"][0]["skip"]["cause"]["location"]["slot"]
        self.assertEqual(scorer.score_response(req, truth, json.dumps(missing_slot).encode())["status"], "inconclusive")
        wrong_semantic = copy.deepcopy(base)
        wrong_semantic["observations"]["members"][0]["skip"]["cause"]["location"]["slot"]["component"] = "translation"
        self.assertEqual(scorer.score_response(req, truth, json.dumps(wrong_semantic).encode())["status"], "failed")

    def test_actual_typed_top_level_rejection(self) -> None:
        req = request()
        req.update({"expected_response_status": "rejected", "expected_cause": {"code": "ck.provisional-r3-authored-conflict.numeric-comparison.invalid-profile", "failure": "negative", "field": "translation-relative", "index": 3}})
        truth = oracle.evaluate_source(req["source"], "translation")
        response = {"protocol_id": RESPONSE_PROTOCOL_ID, "request_id": req["request_id"], "status": "rejected", "error": "ck.provisional-r3-authored-conflict.invalid-tolerance", "cause": req["expected_cause"]}
        result = scorer.score_response(req, truth, json.dumps(response).encode())
        self.assertEqual((result["status"], result["cause"]["index"]), ("supported", 3))
        self.assertEqual(result["cause"], req["expected_cause"])
        observed = scorer.score_response(req, truth, json.dumps(response).encode(), observation_only=True)
        self.assertEqual((observed["status"], observed["classification"], observed["cause"]), ("observation", "rejected", req["expected_cause"]))
        for bad_index in (True, -1, 1.5, 1_000_001):
            bad = copy.deepcopy(response)
            bad["cause"]["index"] = bad_index
            with self.subTest(index=bad_index):
                self.assertEqual(scorer.score_response(req, truth, json.dumps(bad).encode())["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
