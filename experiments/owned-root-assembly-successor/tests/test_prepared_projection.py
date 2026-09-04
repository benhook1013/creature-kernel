# ruff: noqa: SIM905
from __future__ import annotations

import copy
import hashlib
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[1]
SOURCE = REPOSITORY / "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_TABLE = REPOSITORY / "experiments/current-form-surface-preview/structural_profile_candidates.json"
CONTRACT = PACKAGE / "design-contract.md"
SIDECAR = PACKAGE / "design-contract.sha256"
CONTRACT_ROLE = "experiments/owned-root-assembly-successor/design-contract.md"
SOURCE_ROLE = "examples/body-documents/stylized-digitigrade-biped-authored-form.json"
PROFILE_ROLE = "experiments/current-form-surface-preview/structural_profile_candidates.json"
CONTRACT_HASH = "3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490"
SOURCE_HASH = "82269e843555ff1aad3c66399e3fcaeb11bbee81d72b69d15765ea9c4e7aff14"
PROFILE_HASH = "a5fba6643d0031bac83c08e9093e11fd7945806963509fa939865866112d9640"
COMPONENTS_HASH = "58c7ba6d4fd20135f9e93bc8b92690102287f11ae6092b9f3b82459e59375a5f"
BINDINGS_HASH = "57ce3638fd31cca47294d8c9ddf142d783b527b18be431a5501fccda1085bc12"
SIDECAR_BYTES = (b"3122f0db2235754ed782bd38a88c4d7ad7cc7edbf635d147194f1e93f8556490  "
                 b"experiments/owned-root-assembly-successor/design-contract.md\n")
sys.path.insert(0, str(PACKAGE))

import artifact_serialization as artifacts
import prepared_projection as projection
from prepared_projection import (
    PreparedProjectionError,
    _admit_profile_bytes,
    _admit_source_bytes,
    _validate_binding_records,
    _validate_profile_table,
    _validate_source_document,
    admit_prepared_bytes,
    build_source_binding_records,
    canonical_json_bytes,
    canonical_json_sha256,
    normalize_source_address,
    prepare_standard_neutral,
    source_binding_records,
    validate_prepared,
)

PROFILE_DIMENSION_KEYS = frozenset("""
arm_profile_forward arm_profile_lateral arm_profile_up arm_radius arm_shoulder
body_extent_x body_extent_y body_extent_z body_profile_depth body_profile_lateral
foot_extent_x foot_extent_y foot_extent_z foot_profile_forward foot_profile_lateral
foot_profile_up hand_extent_x hand_extent_y hand_extent_z head_extent_x head_extent_y
head_extent_z head_profile_forward head_profile_lateral head_profile_up
leg_profile_forward leg_profile_lateral leg_profile_up leg_radius neck_profile_forward
neck_profile_lateral neck_profile_up neck_radius tail_root_end tail_root_start
tail_tip_end tail_tip_start
""".split())
def _address(role: str, side: str | None = None) -> list[object]:
    return ["main", [] if side is None else [side], "part", role]
def _mutated(value, path, replacement):
    candidate = copy.deepcopy(value)
    target = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    return candidate
class _Explosive:
    def __eq__(self, other):
        raise RuntimeError("comparison escaped")
    def __hash__(self):
        raise RuntimeError("hash escaped")
    def __fspath__(self):
        raise RuntimeError("path conversion escaped")
PART_ADDRESS_BY_INDEX = {
    0: _address("pelvis"), 1: _address("torso"), 2: _address("neck"),
    4: _address("upper_arm", "left"), 7: _address("upper_arm", "right"),
    10: _address("thigh", "left"), 13: _address("thigh", "right"),
}
def _expected_world_records(component, chain, landmark):
    derivation = ("source.world-placement-axis-sum.v1" if landmark is None
                  else "source.world-landmark-axis-sum.v1")
    addresses = sorted((PART_ADDRESS_BY_INDEX[index] for index in chain), key=canonical_json_bytes)
    result = []
    for axis in range(3):
        pointers = [f"/body/parts/{index}/placement/translation/{axis}" for index in chain]
        if landmark is not None:
            pointers.append(f"/body/landmarks/{landmark}/position/{axis}")
        result.append({
            "prepared_component": f"{component}.{'xyz'[axis]}",
            "derivation_id": derivation,
            "source_addresses": addresses,
            "source_pointers": sorted(pointers),
        })
    return result
def _expected_dimension(component, owner, index):
    return {
        "prepared_component": component,
        "derivation_id": "source.dimension-value.v1",
        "source_addresses": [PART_ADDRESS_BY_INDEX[owner]],
        "source_pointers": [f"/body/dimensions/{index}/value"],
    }
def _expected_bindings():
    records = []
    stations = (("lower_pelvis", (0,), 24, 0, (6, 7, 8)),
        ("upper_pelvis", (0,), 25, 0, (9, 10, 11)),
        ("lower_abdomen", (0, 1), 26, 1, (12, 13, 14)),
        ("waist_abdomen", (0, 1), 27, 1, (15, 16, 17)),
        ("upper_abdomen", (0, 1), 28, 1, (18, 19, 20)),
        ("lower_ribcage", (0, 1), 29, 1, (21, 22, 23)),
        ("upper_ribcage_shoulder", (0, 1), 30, 1, (24, 25, 26)),
        ("neck_collar", (0, 1, 2), 31, 2, (27, 29, 29)),
        ("neck_upper", (0, 1, 2), 32, 2, (30, 32, 32)),
    )
    for name, chain, landmark, owner, indices in stations:
        records.extend(_expected_world_records(f"stations.{name}.C", chain, landmark))
        for field, index in zip(("rL", "rA", "rP"), indices):
            records.append(_expected_dimension(f"stations.{name}.{field}", owner, index))
    for side, owner, axilla, peak, indices in (("left", 4, 1, 0, (67, 68, 69, 56)),
        ("right", 7, 3, 2, (82, 83, 84, 62)),
    ):
        chain = (0, 1, owner)
        records.extend(_expected_world_records(f"shoulders.{side}.axilla", chain, axilla))
        records.extend(_expected_world_records(f"shoulders.{side}.peak", chain, peak))
        records.extend(_expected_world_records(f"shoulders.{side}.arm_origin", chain, None))
        fields = ("start_lateral", "start_up", "start_forward", "shoulder_depth")
        records.extend(_expected_dimension(f"shoulders.{side}.{field}", owner, index)
                       for field, index in zip(fields, indices))
    for side, owner, landmark, indices in (("left", 10, 14, (97, 98, 99)),
                                           ("right", 13, 19, (112, 113, 114)),
    ):
        records.extend(_expected_world_records(f"hips.{side}.P_s", (0, owner), landmark))
        records.extend(_expected_dimension(f"hips.{side}.{field}", owner, index)
                       for field, index in zip(("r_x", "r_y", "r_z"), indices))
    return sorted(records, key=lambda record: record["prepared_component"].encode("utf-8"))
class PreparedProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_document = json.loads(SOURCE.read_bytes())
        cls.profile_document = json.loads(PROFILE_TABLE.read_bytes())
        cls.prepared = prepare_standard_neutral(SOURCE)

    def assert_runtime_vector(self, value, length=3):
        self.assertIs(type(value), list)
        self.assertEqual(len(value), length)
        self.assertTrue(all(type(item) is float for item in value))
    def test_complete_prepared_schema_values_and_runtime_types(self):
        prepared = self.prepared
        self.assertEqual(set(prepared), {
            "schema", "contract", "source", "profile_selection", "basis",
            "parts", "stations", "shoulders", "hips", "provenance",
        })
        self.assertEqual(prepared["schema"], "owned-root-assembly-successor-prepared.v1")
        for key, path, digest in (("contract", CONTRACT_ROLE, CONTRACT_HASH),
                                  ("source", SOURCE_ROLE, SOURCE_HASH),
        ):
            self.assertEqual(prepared[key], {"path": path, "sha256": digest})
            self.assertEqual(set(prepared[key]), {"path", "sha256"})
        selection = prepared["profile_selection"]
        self.assertEqual(set(selection), {
            "profile_id", "profile_table_path", "profile_table_sha256", "dimensions",
        })
        self.assertEqual((selection["profile_id"], selection["profile_table_path"],
                          selection["profile_table_sha256"]),
                         ("standard_neutral_reference", PROFILE_ROLE, PROFILE_HASH))
        self.assertEqual(set(selection["dimensions"]), PROFILE_DIMENSION_KEYS)
        self.assertTrue(all(type(value) is float and value == 1000.0
                            for value in selection["dimensions"].values()))
        self.assertEqual(prepared["basis"], {
            "length_unit": "metre", "handedness": "right", "up": "+y", "forward": "+z",
        })
        parts = (("pelvis", None, [0.0, 0.0, 0.0]), ("torso", None, [0.0, 1.0, 0.0]),
            ("neck", None, [0.0, 1.0, 0.0]), ("upper_arm", "left", [-1.0, 1.0, 0.0]),
            ("upper_arm", "right", [1.0, 1.0, 0.0]), ("thigh", "left", [-1.0, -1.0, 0.0]),
            ("thigh", "right", [1.0, -1.0, 0.0]),
        )
        self.assertEqual(len(prepared["parts"]), len(parts))
        for record, (role, side, translation) in zip(prepared["parts"], parts):
            self.assertEqual(set(record), {"address", "placement"})
            self.assertEqual(record["address"], _address(role, side))
            self.assertEqual(set(record["placement"]), {"translation", "rotation_xyzw"})
            self.assertEqual(record["placement"]["translation"], translation)
            self.assertEqual(record["placement"]["rotation_xyzw"], [0.0, 0.0, 0.0, 1.0])
            self.assert_runtime_vector(record["placement"]["translation"])
            self.assert_runtime_vector(record["placement"]["rotation_xyzw"], 4)
        stations = {
            "lower_pelvis": ("pelvis", "form_torso_profile_lower_pelvis", [0.0, -0.45, 0.0], (1.5, .85, .6)),
            "upper_pelvis": ("pelvis", "form_torso_profile_upper_pelvis", [0.0, -.2, 0.0], (1.35, .78, .56)),
            "lower_abdomen": ("torso", "form_torso_profile_lower_abdomen", [0.0, .25, 0.0], (1.125, .68, .54)),
            "waist_abdomen": ("torso", "form_torso_profile_waist_abdomen", [0.0, .5, 0.0], (.875, .5, .4)),
            "upper_abdomen": ("torso", "form_torso_profile_upper_abdomen", [0.0, .8, 0.0], (1.225, .725, .56)),
            "lower_ribcage": ("torso", "form_torso_profile_lower_ribcage", [0.0, 1.05, 0.0], (1.45, .875, .675)),
            "upper_ribcage_shoulder": (
                "torso", "form_torso_profile_upper_ribcage_shoulder", [0.0, 1.95, 0.0], (1.5, .9, .7)),
            "neck_collar": ("neck", "form_head_neck_profile_neck_collar", [0.0, 2.15, 0.0], (.42, .4, .4)),
            "neck_upper": ("neck", "form_head_neck_profile_neck_upper", [0.0, 2.55, 0.0], (.34, .33, .33)),
        }
        self.assertEqual(list(prepared["stations"]), list(stations))
        for name, (owner, prefix, center, radii) in stations.items():
            record = prepared["stations"][name]
            self.assertEqual(set(record), {"owner", "prefix", "C", "rL", "rA", "rP"})
            self.assertEqual((record["owner"], record["prefix"], record["C"]), (_address(owner), prefix, center))
            self.assertEqual(tuple(record[field] for field in ("rL", "rA", "rP")), radii)
            self.assert_runtime_vector(record["C"])
            self.assertTrue(all(type(record[field]) is float for field in ("rL", "rA", "rP")))
        for side, sign in (("left", -1.0), ("right", 1.0)):
            shoulder = prepared["shoulders"][side]
            self.assertEqual(set(shoulder), {
                "axilla", "peak", "arm_origin", "start_lateral", "start_up",
                "start_forward", "shoulder_depth",
            })
            expected = ([1.1 * sign, 1.7, 0.0], [1.1 * sign, 2.15, 0.0],
                        [sign, 2.0, 0.0], .35, .3, .32, .35)
            self.assertEqual(tuple(shoulder.values()), expected)
            for field in ("axilla", "peak", "arm_origin"):
                self.assert_runtime_vector(shoulder[field])
            self.assertTrue(all(type(shoulder[field]) is float
                                for field in ("start_lateral", "start_up", "start_forward", "shoulder_depth")))
            hip = prepared["hips"][side]
            self.assertEqual(set(hip), {"P_s", "r_x", "r_y", "r_z"})
            self.assertEqual(tuple(hip.values()), ([sign, -1.0, 0.0], .32, .28, .3))
            self.assert_runtime_vector(hip["P_s"])
            self.assertTrue(all(type(hip[field]) is float for field in ("r_x", "r_y", "r_z")))
        self.assertEqual(prepared["provenance"], {"source_files": [
            {"path": SOURCE_ROLE, "sha256": SOURCE_HASH, "bytes": 56984},
            {"path": PROFILE_ROLE, "sha256": PROFILE_HASH, "bytes": 29970},
        ]})
    def test_public_validator_is_closed_against_schema_and_value_forgery(self):
        self.assertIs(validate_prepared(self.prepared), self.prepared)
        extra = copy.deepcopy(self.prepared)
        extra["stations"]["neck_upper"]["unknown"] = 1.0
        missing = copy.deepcopy(self.prepared)
        del missing["profile_selection"]["dimensions"]["arm_radius"]
        cases = (("extra", extra), ("missing", missing),
            ("type", _mutated(self.prepared, ("shoulders", "left", "axilla"), (0.0, 0.0, 0.0))),
            ("part", _mutated(self.prepared, ("parts", 0, "placement", "translation", 0), .125)),
            ("station", _mutated(self.prepared, ("stations", "lower_pelvis", "rL"), 1.51)),
            ("shoulder", _mutated(self.prepared, ("shoulders", "left", "axilla", 0), -1.05)),
            ("hip", _mutated(self.prepared, ("hips", "right", "r_x"), .33)),
        )
        for name, candidate in cases:
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                validate_prepared(candidate)
    def test_canonical_prepared_bytes_round_trip_and_rejections(self):
        encoded = canonical_json_bytes(self.prepared)
        admitted = admit_prepared_bytes(encoded)
        self.assertEqual(admitted, self.prepared)
        self.assertEqual(canonical_json_bytes(admitted), encoded)
        self.assertIs(type(admitted["parts"][0]["placement"]["translation"][0]), float)
        negative_zero = _mutated(self.prepared, ("parts", 0, "placement", "translation", 0), -0.0)
        self.assertEqual(canonical_json_bytes(negative_zero), encoded)
        self.assertEqual(admit_prepared_bytes(canonical_json_bytes(negative_zero)), self.prepared)
        integer = _mutated(self.prepared, ("parts", 0, "placement", "translation", 0), 1)
        boolean = _mutated(self.prepared, ("shoulders", "left", "shoulder_depth"), True)
        unknown = copy.deepcopy(self.prepared)
        unknown["hips"]["left"]["forged"] = 0.0
        cases = (("nonzero integer", canonical_json_bytes(integer)),
            ("boolean", canonical_json_bytes(boolean)),
            ("unknown field", canonical_json_bytes(unknown)),
            ("nonfinite", encoded.replace(b'"r_x":0.32', b'"r_x":NaN', 1)),
            ("duplicate", encoded[:-1] + b',"schema":"owned-root-assembly-successor-prepared.v1"}'),
            ("noncanonical", encoded + b"\n"),
        )
        for name, raw in cases:
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                admit_prepared_bytes(raw)
    def test_all_92_bindings_match_independent_complete_mapping(self):
        expected = _expected_bindings()
        actual = source_binding_records(SOURCE)
        components = [record["prepared_component"] for record in expected]
        self.assertEqual(len(expected), 92)
        self.assertEqual(hashlib.sha256(canonical_json_bytes(components)).hexdigest(), COMPONENTS_HASH)
        self.assertEqual(hashlib.sha256(canonical_json_bytes(expected)).hexdigest(), BINDINGS_HASH)
        self.assertEqual(actual, expected)
        self.assertEqual(build_source_binding_records(SOURCE), expected)
        self.assertEqual(len(set(components)), 92)
        self.assertEqual(components, sorted(components))
        for record in actual:
            self.assertEqual(set(record), {
                "prepared_component", "derivation_id", "source_addresses", "source_pointers",
            })
            self.assertTrue(record["source_addresses"] and record["source_pointers"])
            self.assertEqual(record["source_pointers"], sorted(set(record["source_pointers"])))
            addresses = record["source_addresses"]
            self.assertEqual(len(addresses), len({canonical_json_bytes(item) for item in addresses}))
            self.assertEqual(addresses, sorted(addresses, key=canonical_json_bytes))
    def test_binding_commitments_reject_each_forgery_class(self):
        records = _expected_bindings()
        for name, path, value in (("id", (0, "prepared_component"), "forged.component"),
            ("derivation", (0, "derivation_id"), "forged.derivation"),
            ("address", (0, "source_addresses", 0, 3), "forged_role"),
            ("pointer", (0, "source_pointers", 0), "/forged/pointer"),
        ):
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                _validate_binding_records(_mutated(records, path, value))
    def test_fixed_paths_reject_exact_byte_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copies = root / "contract.md", root / "source.json", root / "profiles.json"
            for target, canonical in zip(copies, (CONTRACT, SOURCE, PROFILE_TABLE)):
                target.write_bytes(canonical.read_bytes())
            cases = (("contract path", {"source_path": SOURCE, "contract_path": copies[0]}),
                ("source path", {"source_path": copies[1]}),
                ("profile table path", {"source_path": SOURCE, "profile_table_path": copies[2]}),
            )
            for message, kwargs in cases:
                with self.subTest(message=message), self.assertRaisesRegex(PreparedProjectionError, message):
                    prepare_standard_neutral(**kwargs)
    def test_public_constant_reassignment_cannot_redirect_fixed_admission(self):
        encoded, expected_bindings = canonical_json_bytes(self.prepared), _expected_bindings()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ("contract", "sidecar", "source", "profile")]
            for target, canonical in zip(paths, (CONTRACT, SIDECAR, SOURCE, PROFILE_TABLE)):
                target.write_bytes(canonical.read_bytes())
            replacements = {
                "CONTRACT_ROLE": "forged/contract", "SOURCE_ROLE": "forged/source",
                "PROFILE_ROLE": "forged/profile", "CONTRACT_PATH": paths[0],
                "SIDECAR_PATH": paths[1], "SOURCE_PATH": paths[2], "PROFILE_TABLE_PATH": paths[3],
                "EXPECTED_CONTRACT_SHA256": "0" * 64, "EXPECTED_SOURCE_SHA256": "1" * 64,
                "EXPECTED_PROFILE_TABLE_SHA256": "2" * 64, "EXPECTED_SOURCE_BYTES": 1,
                "EXPECTED_PROFILE_BYTES": 2, "EXPECTED_BINDING_COMPONENTS_SHA256": "3" * 64,
                "EXPECTED_BINDINGS_SHA256": "4" * 64,
            }
            with patch.multiple(projection, **replacements), patch.object(
                projection.artifacts, "contract_sidecar_bytes", side_effect=RuntimeError("redirected"),
            ):
                self.assertEqual(projection.prepare_standard_neutral(), self.prepared)
                self.assertIs(projection.validate_prepared(self.prepared), self.prepared)
                self.assertEqual(projection.admit_prepared_bytes(encoded), self.prepared)
                self.assertEqual(projection.source_binding_records(), expected_bindings)
                with self.assertRaises(PreparedProjectionError):
                    projection.prepare_standard_neutral(
                        projection.SOURCE_PATH, contract_path=projection.CONTRACT_PATH,
                        profile_table_path=projection.PROFILE_TABLE_PATH)
    def test_fixed_hashes_sidecar_and_sizes_are_independent_literals(self):
        for path, size, digest in (
            (CONTRACT, 173184, CONTRACT_HASH), (SIDECAR, 127, hashlib.sha256(SIDECAR_BYTES).hexdigest()),
            (SOURCE, 56984, SOURCE_HASH), (PROFILE_TABLE, 29970, PROFILE_HASH),
        ):
            raw = path.read_bytes()
            self.assertEqual(len(raw), size)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
        self.assertEqual(SIDECAR.read_bytes(), SIDECAR_BYTES)
        self.assertEqual(projection._SIDECAR_CONTENT, SIDECAR_BYTES)
    def test_contract_sidecar_call_uses_fixed_signature(self):
        with patch.object(artifacts, "contract_sidecar_bytes", wraps=artifacts.contract_sidecar_bytes) as call:
            runpy.run_path(str(PACKAGE / "prepared_projection.py"))
        call.assert_called_once_with(CONTRACT_HASH)
    def test_source_and_profile_identity_fail_closed_through_byte_seams(self):
        source = _mutated(self.source_document, ("basis", "forward"), "-z")
        with self.assertRaisesRegex(PreparedProjectionError, "source identity mismatch"):
            _admit_source_bytes(json.dumps(source).encode())
        profile = _mutated(self.profile_document, ("profiles", 0, "dimension_scales", "arm_radius"), 1001)
        mutated_profile = json.dumps(profile).encode()
        real_read = projection._READ_FILE

        def read_with_mutated_profile(path):
            return mutated_profile if Path(path) == PROFILE_TABLE else real_read(path)

        with patch.object(projection, "_READ_FILE", side_effect=read_with_mutated_profile), \
                self.assertRaisesRegex(PreparedProjectionError, "profile identity mismatch"):
            prepare_standard_neutral(SOURCE)
        with self.assertRaisesRegex(PreparedProjectionError, "profile identity mismatch"):
            _admit_profile_bytes(mutated_profile)
    def test_source_profile_schema_and_selector_boundaries(self):
        missing = copy.deepcopy(self.source_document)
        del missing["body"]["parts"][0]["placement"]
        duplicate = _mutated(self.source_document, ("body", "dimensions", 1),
                             copy.deepcopy(self.source_document["body"]["dimensions"][0]))
        source_cases = (
            ("schema", missing),
            ("identity", _mutated(self.source_document, ("source", "document"), "forged")),
            ("cardinality", _mutated(self.source_document, ("body", "dimensions"),
                                     self.source_document["body"]["dimensions"][:-1])),
            ("rotation", _mutated(self.source_document,
                                  ("body", "parts", 17, "placement", "rotation_xyzw"), [0.0] * 4)),
            ("selector", duplicate),
            ("frame", _mutated(self.source_document,
                               ("body", "landmarks", 0, "frame", "role"), "missing_frame")),
        )
        for name, candidate in source_cases:
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                _validate_source_document(candidate)
        wrong_order = copy.deepcopy(self.profile_document)
        wrong_order["profiles"][0], wrong_order["profiles"][1] = wrong_order["profiles"][1::-1]
        for name, candidate in (
            ("order", wrong_order),
            ("scale", _mutated(self.profile_document,
                               ("profiles", 0, "dimension_scales", "arm_radius"), 1001)),
        ):
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                _validate_profile_table(candidate)
    def test_every_source_dimension_requires_positive_finite_binary64(self):
        for index in range(153):
            with self.subTest(index=index), self.assertRaises(PreparedProjectionError):
                _validate_source_document(_mutated(
                    self.source_document, ("body", "dimensions", index, "value"), 0))
        for name, value in (("boolean", True), ("nonfinite", float("inf")), ("overflow", 10 ** 400)):
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                _validate_source_document(_mutated(
                    self.source_document, ("body", "dimensions", 152, "value"), value))
    def test_strict_source_json_boundaries(self):
        source = SOURCE.read_bytes()
        cases = (
            source.replace(b'"extensions": []', b'"extensions": [], "extensions": []', 1),
            source.replace(b'"value": 1.7', b'"value": NaN', 1), b"\xff",
        )
        for raw in cases:
            with self.subTest(raw=raw[:24]), self.assertRaisesRegex(PreparedProjectionError, "strict UTF-8 JSON"):
                _admit_source_bytes(raw)
    def test_malformed_public_admissions_normalize_exceptions(self):
        for name, path in (
            ("schema", ("schema",)), ("address", ("parts", 0, "address", 3)),
            ("provenance", ("provenance", "source_files", 0, "sha256")),
            ("basis", ("basis", "up")),
        ):
            with self.subTest(name=name), self.assertRaises(PreparedProjectionError):
                validate_prepared(_mutated(self.prepared, path, _Explosive()))
        with patch.object(projection, "_DECODE_JSON", side_effect=RecursionError), \
                self.assertRaises(PreparedProjectionError):
            admit_prepared_bytes(b"{}")
        with patch.object(projection, "_JSON_BYTES",
                          side_effect=artifacts.ArtifactSerializationError("forged")), \
                self.assertRaises(PreparedProjectionError):
            validate_prepared(self.prepared)
        for function in (prepare_standard_neutral, source_binding_records):
            with self.subTest(function=function.__name__), self.assertRaises(PreparedProjectionError):
                function(_Explosive())
    def test_normalization_aliases_canonical_bytes_and_closed_content(self):
        raw = {"role": "upper_arm", "kind": "part", "anchors": ["left"], "namespace": "main"}
        normalized = normalize_source_address(raw)
        self.assertEqual(normalized, ["main", ["left"], "part", "upper_arm"])
        self.assertIsNot(normalized, raw)
        self.assertIsNot(normalized[1], raw["anchors"])
        for bad in (
            {"namespace": "main", "anchors": [], "kind": "part"},
            {"namespace": "main", "anchors": [1], "kind": "part", "role": "x"},
            {"namespace": "main", "anchors": [], "kind": "", "role": "x"},
            {"namespace": "main", "anchors": [], "kind": "part", "role": "x", "extra": 1},
        ):
            with self.subTest(bad=bad), self.assertRaises(PreparedProjectionError):
                normalize_source_address(bad)
        stations = self.prepared["stations"]
        self.assertEqual(stations["neck_collar"]["rA"], stations["neck_collar"]["rP"])
        encoded = canonical_json_bytes(self.prepared)
        self.assertNotIn(b"-0.0", encoded)
        self.assertIn(b'"rotation_xyzw":[0,0,0,1.0]', encoded)
        self.assertEqual(canonical_json_sha256(self.prepared), hashlib.sha256(encoded).hexdigest())
        self.assertEqual(encoded, canonical_json_bytes(prepare_standard_neutral(SOURCE)))
        self.assertEqual(canonical_json_bytes({"value": -0.0}), b'{"value":0}')
        serialized = encoded.decode()
        for field in ("vertices", "faces", "edges", "connectivity", "perimeter", "point_cloud",
                      "mask", "silhouette", "corrective_offset", "serialized_output", "part_placements"):
            self.assertNotIn(field, serialized)

if __name__ == "__main__":
    unittest.main()
