"""Focused, read-only tests for the Phase 3 materialized adapter."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction

import phase3_oracle as oracle
from phase3_common import as_fraction, fraction_to_binary64_bits
from test_phase3_oracle_scorer import transform, wire_response
from phase3_materialized_adapter import (
    MaterializedAdapterError,
    load_materialized_cases,
    run_materialized,
)


PACKAGE = Path(__file__).resolve().parents[1]


class MaterializedAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._package_holder = tempfile.TemporaryDirectory()
        cls.package_root = Path(cls._package_holder.name) / "phase3"
        shutil.copytree(PACKAGE, cls.package_root, symlinks=True)
        freeze_manifest = cls.package_root / "manifests/freeze-manifest.json"
        if freeze_manifest.exists() and not freeze_manifest.is_symlink():
            freeze_manifest.chmod(0o644)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._package_holder.cleanup()
        super().tearDownClass()

    def copy_package(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        holder = tempfile.TemporaryDirectory()
        destination = Path(holder.name) / "phase3"
        shutil.copytree(PACKAGE, destination, symlinks=True)
        # The committed pre-fix artifact was mode 0600; normalize only this
        # disposable copy so adapter tests exercise package contents rather
        # than the stale checkout mode.
        freeze_manifest = destination / "manifests/freeze-manifest.json"
        if freeze_manifest.exists() and not freeze_manifest.is_symlink():
            freeze_manifest.chmod(0o644)
        return holder, destination

    @staticmethod
    def rebind_artifact(root: Path, relative: str) -> None:
        manifest_path = root / "manifests/artifact-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw = (root / relative).read_bytes()
        for item in manifest["artifacts"]:
            if item["path"] == relative:
                item["bytes"] = len(raw)
                item["sha256"] = hashlib.sha256(raw).hexdigest()
                break
        else:
            raise AssertionError(relative)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    @classmethod
    def rebind_recipe(cls, root: Path) -> None:
        cls.rebind_materialized(root, "manifests/recipe-manifest.json")

    @staticmethod
    def rebind_preregistration(root: Path, relative: str) -> None:
        path = root / "preregistration.json"
        prereg = json.loads(path.read_text(encoding="utf-8"))
        materialization = prereg["development_materialization"]
        if relative.startswith("corpora/"):
            entries = materialization["corpora"]
            declaration = next(item for item in entries if item["path"] == relative)
        elif relative == "manifests/recipe-manifest.json":
            declaration = materialization["recipe_manifest"]
        elif relative == "sqrt-vectors.json":
            declaration = materialization["sqrt_vectors"]
        elif relative == "manifests/artifact-manifest.json":
            declaration = materialization["artifact_manifest"]
        else:
            raise AssertionError(relative)
        raw = (root / relative).read_bytes()
        declaration["bytes"] = len(raw)
        declaration["sha256"] = hashlib.sha256(raw).hexdigest()
        path.write_text(json.dumps(prereg, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    @classmethod
    def rebind_materialized(cls, root: Path, relative: str) -> None:
        cls.rebind_artifact(root, relative)
        cls.rebind_preregistration(root, relative)
        cls.rebind_preregistration(root, "manifests/artifact-manifest.json")

    @staticmethod
    def response_for(case: dict[str, object]) -> bytes:
        truth = oracle.evaluate_source(case["source"], case["metric"])
        def exact_transform(value: dict[str, object]) -> dict[str, object]:
            def exact_bits(item: object) -> str:
                token = str(item)
                exact = Fraction(*[int(part) for part in token.split("/", 1)]) if "/" in token else as_fraction(token)
                return fraction_to_binary64_bits(exact)
            return {
                "translation": [exact_bits(item) for item in value["translation_exact"]],
                "rotation_xyzw": [exact_bits(item) for item in value["rotation_raw_exact"]],
            }
        authored = exact_transform(truth["authored_root_local"])
        derived = exact_transform(truth["derived_root_local"])
        return wire_response(case, truth, authored=authored, derived=derived, final_output=derived)

    def test_current_materialization_projects_opaque_cases_and_preserves_ids(self) -> None:
        cases = load_materialized_cases(self.package_root)
        self.assertEqual(len(cases), 60)
        self.assertEqual(cases[0]["request_id"], "p3-{attempt_id}-000")
        self.assertEqual(cases[59]["request_id"], "p3-{attempt_id}-059")
        for case in cases:
            self.assertNotIn("case_id", case)
            self.assertNotIn("construction", case)
            self.assertNotIn("construction_target", case)
            self.assertNotIn("source_truth", case)
            self.assertNotIn("expected_class", case)
        self.assertTrue(all(cases[index].get("observation_only") for index in list(range(8)) + list(range(48, 60))))
        self.assertTrue(all("observation_only" not in cases[index] for index in range(8, 48)))
        self.assertEqual(set(cases[8]), {
            "protocol_id", "request_id", "operation", "resource_profile", "source",
            "tolerances", "providers", "metric",
        })
        self.assertFalse(cases[56]["dispatch_to_candidate"])
        self.assertTrue(cases[48]["observation_only"])
        self.assertEqual(cases[59]["expected_response_status"], "rejected")
        self.assertIsInstance(cases[0]["tolerances"]["translation_absolute"], Decimal)

    def test_successful_non_evidence_runner_handoff(self) -> None:
        cases = load_materialized_cases(self.package_root)
        development = cases[6]
        held_out = cases[8]
        transcript = {
            development["request_id"]: self.response_for(development),
            held_out["request_id"]: self.response_for(held_out),
        }
        result = run_materialized(self.package_root, transcript)
        self.assertEqual(result["mode"], "synthetic-validation")
        self.assertEqual(result["counts"]["cases"], 60)
        self.assertEqual(result["preflight_count"], 3)
        self.assertEqual(result["synthetic_dispatches"], 57)
        entries = {entry["request_id"]: entry for entry in result["entries"]}
        self.assertEqual(entries["synthetic/phase3/006"]["status"], "observation")
        self.assertEqual(entries["synthetic/phase3/008"]["status"], "supported")
        self.assertEqual(entries["synthetic/phase3/008"]["classification"], "agree")

        mismatched = self.response_for(held_out).replace(b"p3-{attempt_id}-008", b"p3-{attempt_id}-009", 1)
        result = run_materialized(self.package_root, {held_out["request_id"]: mismatched})
        mismatch_entry = next(entry for entry in result["entries"] if entry["request_id"] == "synthetic/phase3/008")
        self.assertEqual(mismatch_entry["cause"]["code"], "response-request-id-mismatch")

        synthetic_echo = self.response_for(held_out).replace(b"p3-{attempt_id}-008", b"synthetic/phase3/008", 1)
        result = run_materialized(self.package_root, {held_out["request_id"]: synthetic_echo})
        synthetic_echo_entry = next(entry for entry in result["entries"] if entry["request_id"] == "synthetic/phase3/008")
        self.assertEqual(synthetic_echo_entry["cause"]["code"], "response-request-id-mismatch")

    def test_reserved_unknown_transcript_id_is_extra_and_restored(self) -> None:
        result = run_materialized(self.package_root, {"synthetic/phase3/000": b"{}"})
        self.assertEqual(result["counts"]["extra_responses"], 1)
        extra = next(entry for entry in result["entries"] if entry["cause"]["code"] == "extra-response")
        self.assertEqual(extra["request_id"], "synthetic/phase3/000")

    def test_optional_freeze_sidecars_are_ignored_but_unknown_layout_fails_closed(self) -> None:
        # The development-unfrozen package has no freeze sidecars and remains
        # a valid adapter input.
        holder, root = self.copy_package()
        try:
            (root / "manifests/freeze-manifest.json").unlink(missing_ok=True)
            shutil.rmtree(root / "manifests/build-receipts", ignore_errors=True)
            self.assertEqual(len(load_materialized_cases(root)), 60)
        finally:
            holder.cleanup()

        # The exact future provenance paths are permitted, but are not part of
        # the generated artifact closure and are not parsed as candidate data.
        holder, root = self.copy_package()
        try:
            (root / "manifests/freeze-manifest.json").unlink(missing_ok=True)
            shutil.rmtree(root / "manifests/build-receipts", ignore_errors=True)
            (root / "manifests/freeze-manifest.json").write_bytes(b"not candidate data\n")
            receipts = root / "manifests/build-receipts"
            receipts.mkdir()
            (receipts / "wsl.json").write_bytes(b"{}\n")
            (receipts / "native.json").write_bytes(b"{}\n")
            self.assertEqual(len(load_materialized_cases(root)), 60)
        finally:
            holder.cleanup()

        for relative in (
            "manifests/unexpected.json",
            "manifests/build-receipts/alternate.json",
            "manifests/build-receipts/nested/receipt.json",
        ):
            holder, root = self.copy_package()
            try:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"{}\n")
                with self.assertRaises(MaterializedAdapterError) as context:
                    load_materialized_cases(root)
                self.assertEqual(context.exception.code, "package-layout")
            finally:
                holder.cleanup()

    def test_transcript_shape_errors_are_stable(self) -> None:
        with self.assertRaises(MaterializedAdapterError) as context:
            run_materialized(self.package_root, [])
        self.assertEqual(context.exception.code, "transcript-shape")

        with self.assertRaises(MaterializedAdapterError) as context:
            run_materialized(self.package_root, {1: b"{}"})
        self.assertEqual(context.exception.code, "transcript-key")

        with self.assertRaises(MaterializedAdapterError) as context:
            run_materialized(self.package_root, {"p3-{attempt_id}-000": bytearray(b"{}")})
        self.assertEqual(context.exception.code, "transcript-shape")

    def test_tampered_hash_and_size_fail_before_conversion(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            path.write_bytes(path.read_bytes().replace(b"p3-{attempt_id}-000", b"p3-{attempt_id}-001", 1))
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "artifact-hash")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            manifest_path = root / "manifests/artifact-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = next(item for item in manifest["artifacts"] if item["path"] == "corpora/development.jsonl")
            item["bytes"] += 1
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            prereg_path = root / "preregistration.json"
            prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
            next(item for item in prereg["development_materialization"]["corpora"] if item["path"] == "corpora/development.jsonl")["bytes"] += 1
            prereg_path.write_text(json.dumps(prereg, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_preregistration(root, "manifests/artifact-manifest.json")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "artifact-size")
        finally:
            holder.cleanup()

    def test_symlink_and_non_utf8_fail_closed(self) -> None:
        holder, root = self.copy_package()
        try:
            target = root / "sqrt-vectors.json"
            target.unlink()
            target.symlink_to(root / "README.md")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "symlink")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            path.write_bytes(path.read_bytes().replace(b"p3-{attempt_id}-000", b"p3-{attempt_id}-\xff00", 1))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "invalid-utf8")
        finally:
            holder.cleanup()

    def test_duplicate_member_and_duplicate_recipe_id_are_rejected(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            first = lines[0].rstrip(b"\n")
            lines[0] = first[:-1] + b',"request_id":"p3-{attempt_id}-000"}\n'
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "duplicate-json-member")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "manifests/recipe-manifest.json"
            recipe = json.loads(path.read_text(encoding="utf-8"))
            recipe["cases"][1]["case_id"] = recipe["cases"][0]["case_id"]
            path.write_text(json.dumps(recipe, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_materialized(root, "manifests/recipe-manifest.json")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "duplicate-case-id")
        finally:
            holder.cleanup()

    def test_partition_count_order_dispatch_and_source_linkage(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "corpora/held-out.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            path.write_bytes(b"".join(lines[:-1]))
            self.rebind_materialized(root, "corpora/held-out.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "partition-count")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "manifests/recipe-manifest.json"
            recipe = json.loads(path.read_text(encoding="utf-8"))
            recipe["cases"][8], recipe["cases"][9] = recipe["cases"][9], recipe["cases"][8]
            path.write_text(json.dumps(recipe, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_recipe(root)
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "partition-order")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            second = json.loads(lines[1])
            second["request_id"] = "p3-{attempt_id}-000"
            lines[1] = (json.dumps(second, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "duplicate-request-id")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "manifests/recipe-manifest.json"
            recipe = json.loads(path.read_text(encoding="utf-8"))
            recipe["cases"][8]["dispatch_to_candidate"] = False
            path.write_text(json.dumps(recipe, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_recipe(root)
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "dispatch-mismatch")
        finally:
            holder.cleanup()

    def test_blank_and_oversized_lines_are_bounded(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            lines[0] = b"\n"
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "blank-line")
        finally:
            holder.cleanup()

    def test_preregistration_sqrt_and_typed_metadata_bindings(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "preregistration.json"
            prereg = json.loads(path.read_text(encoding="utf-8"))
            prereg["development_materialization"]["corpora"][0]["sha256"] = "0" * 64
            path.write_text(json.dumps(prereg, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "prereg-binding")
        finally:
            holder.cleanup()

    def test_generator_and_fixture_identities_are_fixed(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "scripts/generate_phase3.py"
            path.write_bytes(path.read_bytes().replace(b"generate_phase3", b"generate_phaseX", 1))
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "generator-hash")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "preregistration.json"
            prereg = json.loads(path.read_text(encoding="utf-8"))
            prereg["development_materialization"]["generator"]["sha256"] = "0" * 64
            path.write_text(json.dumps(prereg, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "generator-hash")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "manifests/recipe-manifest.json"
            recipe = json.loads(path.read_text(encoding="utf-8"))
            recipe["fixture"]["sha256"] = "0" * 64
            path.write_text(json.dumps(recipe, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_recipe(root)
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "recipe-linkage")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "sqrt-vectors.json"
            vectors = json.loads(path.read_text(encoding="utf-8"))
            vectors["vectors"][0]["exact_root"] = "3"
            path.write_text(json.dumps(vectors, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_materialized(root, "sqrt-vectors.json")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "sqrt-vectors")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "manifests/recipe-manifest.json"
            recipe = json.loads(path.read_text(encoding="utf-8"))
            recipe["cases"][59]["typed_expectation"] = {"status": "rejected"}
            path.write_text(json.dumps(recipe, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            self.rebind_recipe(root)
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "manifest-shape")
        finally:
            holder.cleanup()

    def test_numeric_and_file_safety_regressions(self) -> None:
        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            row = json.loads(lines[0])
            row["tolerances"]["translation_relative"] = int("9" * 700)
            lines[0] = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "numeric-significand-too-large")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            row = json.loads(lines[0])
            row["tolerances"]["translation_relative"] = "0.0"
            lines[0] = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "request-shape")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            (root / "preregistration.json").chmod(0o600)
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "file-mode")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            os.link(root / "sqrt-vectors.json", root / "sqrt-vectors-hardlink")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "hardlink")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "corpora/development.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            lines[0] = b"x" * 65536 + b"\n"
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/development.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "line-too-large")
        finally:
            holder.cleanup()

        holder, root = self.copy_package()
        try:
            path = root / "corpora/held-out.jsonl"
            lines = path.read_bytes().splitlines(keepends=True)
            row = json.loads(lines[0])
            row["source"] = row["source"].replace("stylized_digitigrade_biped", "tampered", 1)
            lines[0] = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
            path.write_bytes(b"".join(lines))
            self.rebind_materialized(root, "corpora/held-out.jsonl")
            with self.assertRaises(MaterializedAdapterError) as context:
                load_materialized_cases(root)
            self.assertEqual(context.exception.code, "recipe-linkage")
        finally:
            holder.cleanup()


if __name__ == "__main__":
    unittest.main()
