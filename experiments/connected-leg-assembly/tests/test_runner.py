from __future__ import annotations

import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runner  # noqa: E402


def _dependency(root: Path) -> dict[str, object]:
    return {
        "identity": {
            "root": str(root / "transition"),
            "runtime": {"executable": str(root / "transition/runtime/bin/python")},
        },
        "renderer": {"path": str(root / "transition/source/render.py"), "bytes": 3, "sha256": "abc"},
    }


class RunnerTests(unittest.TestCase):
    def test_json_serialization_is_finite_and_stable(self) -> None:
        value = {"tuple": (1, 2), "nested": {"z": True, "a": 1.5}}
        first = runner._json_bytes(value)
        second = runner._json_bytes({"nested": {"a": 1.5, "z": True}, "tuple": [1, 2]})
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), {"nested": {"a": 1.5, "z": True}, "tuple": [1, 2]})
        with self.assertRaises(runner.RunnerError):
            runner._json_bytes({"bad": float("nan")})

    def test_dynamic_import_registers_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "module.py"
            path.write_text("import sys\nREGISTERED = sys.modules[__name__] is not None\n", encoding="utf-8")
            loaded = runner._load_module("connected_leg_test_module", path)
            self.assertIs(sys.modules["connected_leg_test_module"], loaded)
            self.assertTrue(loaded.REGISTERED)

    def test_protocol_baseline_poses_preserve_zero_ankle_angles(self) -> None:
        poses = runner._protocol_poses({"baseline_poses": [{
            "id": "rest", "left": {"hip": 0, "knee": 0, "ankle": 0},
            "right": {"hip": 2, "knee": 3, "ankle": 0},
        }]})
        self.assertEqual(poses[0]["angles"]["left"]["ankle"], 0)
        self.assertEqual(poses[0]["angles"]["right"]["knee"], 3)

    def test_actual_protocol_pose_metadata_is_not_forwarded_as_angles(self) -> None:
        protocol, _ = runner._read_json(runner.HERE / "protocol.json")
        poses = runner._protocol_poses(protocol)
        self.assertEqual([pose["id"] for pose in poses],
                         [row["id"] for row in protocol["baseline_poses"]])
        mirrored = next(pose for pose in poses if pose["id"] == "mirrored15_15")
        self.assertEqual(set(mirrored["angles"]), {"left", "right"})
        self.assertEqual(mirrored["angles"]["right"]["ankle"], 0)

    def test_protocol_perturbations_are_explicitly_pending(self) -> None:
        status = runner._perturbation_status({"input_perturbations": [{"id": "left_A"}]})
        self.assertEqual(status["status"], "not-implemented")
        self.assertEqual(status["execution"], "not-run")
        self.assertEqual(status["declared_ids"], ["left_A"])

    def test_new_full_foot_capture_includes_broadphase_wrapper_and_test(self) -> None:
        self.assertIn("collision_broadphase.py", runner.CAPTURE_FILES)
        self.assertIn("tests/test_collision_broadphase.py", runner.CAPTURE_FILES)

    def test_chest_envelope_evidence_helper_is_in_source_and_test_inventory(self) -> None:
        self.assertIn("chest_envelope_evidence.py", runner.CAPTURE_FILES)
        self.assertIn("tests/test_chest_envelope_evidence.py", runner.CAPTURE_FILES)

    def test_body_capture_bundle_includes_assembly_components_and_inputs(self) -> None:
        for name in (
            "body_assembly.py", "arm_construction.py", "head_construction.py",
            "arm-inputs.json", "head-inputs.json",
            "tests/test_body_assembly.py", "tests/test_arm_construction.py",
            "tests/test_arm_refinement.py",
            "tests/test_head_construction.py", "torso_refinement.py",
            "tests/test_head_refinement.py",
            "torso-refinement-inputs.json", "foot_form_construction.py",
            "foot-form-inputs.json", "tail_construction.py", "tail-inputs.json",
            "head-refinement-inputs.json", "body-config.json",
            "body-refinement-internal-config.json", "tests/test_torso_refinement.py",
            "torso-chest-depth-ablation-inputs.json",
            "body-chest-depth-ablation-config.json",
            "torso-chest-envelope-inputs.json",
            "body-chest-envelope-config.json",
            "thorax_foundation.py",
            "thorax-foundation-baseline-inputs.json",
            "thorax-foundation-width-inputs.json",
            "thorax-foundation-fullness-inputs.json",
            "body-thorax-foundation-baseline-config.json",
            "body-thorax-foundation-width-config.json",
            "body-thorax-foundation-fullness-config.json",
            "tests/test_foot_form_construction.py", "tests/test_tail_construction.py",
        ):
            self.assertIn(name, runner.CAPTURE_FILES)

    def test_chest_envelope_preserves_junction_non_torso_config_projection(self) -> None:
        junction, _ = runner._read_json(
            ROOT / "body-junction-integration-config.json"
        )
        envelope, _ = runner._read_json(
            ROOT / "body-chest-envelope-config.json"
        )
        excluded = {"schema", "evidence_label", "rationale", "budget", "torso_refinement"}
        junction_projection = {
            key: value for key, value in junction.items() if key not in excluded
        }
        envelope_projection = {
            key: value for key, value in envelope.items() if key not in excluded
        }
        self.assertEqual(envelope_projection, junction_projection)
        self.assertEqual(
            envelope["torso_refinement"],
            {"inputs": "torso-chest-envelope-inputs.json"},
        )

    def test_new_body_components_require_explicit_body_config_selection(self) -> None:
        legacy_foot = object()
        form_foot = object()
        torso = object()
        thorax_foundation = object()
        tail = object()
        arms = object()
        head = object()
        modules = {
            "foot_construction": legacy_foot,
            "foot_inputs": {"cases": [{"case_id": "case", "sides": {}}]},
            "foot_form_construction": form_foot,
            "foot_form_inputs": {"cases": [{"case_id": "case",
                                               "construction": {}, "sides": {}}]},
            "torso_refinement": torso,
            "torso_refinement_inputs": {"schema": "torso"},
            "torso_chest_depth_ablation_inputs": {"schema": "chest-depth-ablation"},
            "torso_chest_envelope_inputs": {"schema": "chest-envelope"},
            "thorax_foundation": thorax_foundation,
            "thorax_foundation_baseline_inputs": {"schema": "thorax-baseline"},
            "thorax_foundation_width_inputs": {"schema": "thorax-width"},
            "thorax_foundation_fullness_inputs": {"schema": "thorax-fullness"},
            "arm_construction": arms,
            "arm_inputs": {"cases": [{"case_id": "case", "sides": {}}]},
            "head_construction": head,
            "head_inputs": {"cases": [{"case_id": "case", "head": {}}]},
            "head_refinement_inputs": {"cases": [{"case_id": "case", "head": {}}]},
            "tail_construction": tail,
            "tail_inputs": {"cases": [{"case_id": "case", "enabled": False}]},
        }
        baseline = runner._body_optional_inputs(modules, "case")
        self.assertIs(baseline["foot_builder"], legacy_foot)
        self.assertIs(baseline["foot_inputs"], modules["foot_inputs"]["cases"][0]["sides"])
        self.assertIsNone(baseline["source_refinement_inputs"])
        self.assertIsNone(baseline["thorax_foundation_inputs"])
        self.assertIsNone(baseline["thorax_foundation"])
        self.assertIsNone(baseline["tail_inputs"])

        for filename, input_key in (
            ("thorax-foundation-baseline-inputs.json", "thorax_foundation_baseline_inputs"),
            ("thorax-foundation-width-inputs.json", "thorax_foundation_width_inputs"),
            ("thorax-foundation-fullness-inputs.json", "thorax_foundation_fullness_inputs"),
        ):
            foundation = runner._body_optional_inputs(
                modules, "case", {"thorax_foundation": {"inputs": filename}}
            )
            self.assertIs(foundation["thorax_foundation"], thorax_foundation)
            self.assertIs(foundation["thorax_foundation_inputs"], modules[input_key])
            self.assertEqual(foundation["thorax_foundation_input_name"], filename)

        with self.assertRaisesRegex(runner.RunnerError, "mutually exclusive"):
            runner._body_optional_inputs(
                modules, "case", {
                    "torso_refinement": {"inputs": "torso-refinement-inputs.json"},
                    "thorax_foundation": {
                        "inputs": "thorax-foundation-baseline-inputs.json"
                    },
                }
            )
        missing_input = dict(modules)
        del missing_input["thorax_foundation_width_inputs"]
        with self.assertRaisesRegex(runner.RunnerError, "requires thorax-foundation-width-inputs.json"):
            runner._body_optional_inputs(
                missing_input, "case", {
                    "thorax_foundation": {"inputs": "thorax-foundation-width-inputs.json"}
                }
            )
        missing_provider = dict(modules)
        del missing_provider["thorax_foundation"]
        with self.assertRaisesRegex(runner.RunnerError, "requires thorax_foundation.py"):
            runner._body_optional_inputs(
                missing_provider, "case", {
                    "thorax_foundation": {
                        "inputs": "thorax-foundation-baseline-inputs.json"
                    }
                }
            )

        missing_arm_refinement = dict(modules)
        with self.assertRaisesRegex(runner.RunnerError, "requires arm-refinement-inputs.json"):
            runner._body_optional_inputs(
                missing_arm_refinement, "case", {
                    "arms": {"inputs": "arm-refinement-inputs.json"}
                }
            )
        missing_head_refinement = dict(modules)
        del missing_head_refinement["head_refinement_inputs"]
        with self.assertRaisesRegex(runner.RunnerError, "requires head-refinement-inputs.json"):
            runner._body_optional_inputs(
                missing_head_refinement, "case", {
                    "head": {"inputs": "head-refinement-inputs.json"}
                }
            )
        omitted_optional_inputs = dict(modules)
        del omitted_optional_inputs["arm_inputs"]
        del omitted_optional_inputs["head_inputs"]
        omitted = runner._body_optional_inputs(omitted_optional_inputs, "case")
        self.assertIsNone(omitted["arm_inputs"])
        self.assertIsNone(omitted["head_inputs"])

        selected = runner._body_optional_inputs(
            modules, "case", {
                "torso_refinement": {"inputs": "torso-refinement-inputs.json"},
                "arms": {"inputs": "arm-inputs.json"},
                "head": {"inputs": "head-refinement-inputs.json"},
                "feet": {"builder": "foot_form_construction.py",
                         "inputs": "foot-form-inputs.json"},
                "tail": {"builder": "tail_construction.py",
                         "inputs": "tail-inputs.json"},
            }
        )
        self.assertIs(selected["foot_builder"], form_foot)
        self.assertIs(selected["foot_inputs"], modules["foot_form_inputs"]["cases"][0])
        self.assertIs(selected["source_refinement_inputs"], modules["torso_refinement_inputs"])
        self.assertIs(selected["arm_inputs"], modules["arm_inputs"]["cases"][0]["sides"])
        self.assertIs(selected["head_inputs"], modules["head_refinement_inputs"]["cases"][0]["head"])
        self.assertIs(selected["tail_builder"], tail)
        self.assertIs(selected["tail_inputs"], modules["tail_inputs"]["cases"][0])

        ablation = runner._body_optional_inputs(
            modules, "case", {
                "torso_refinement": {
                    "inputs": "torso-chest-depth-ablation-inputs.json"
                }
            }
        )
        self.assertIs(
            ablation["source_refinement_inputs"],
            modules["torso_chest_depth_ablation_inputs"],
        )

        envelope = runner._body_optional_inputs(
            modules, "case", {
                "torso_refinement": {
                    "inputs": "torso-chest-envelope-inputs.json"
                }
            }
        )
        self.assertIs(
            envelope["source_refinement_inputs"],
            modules["torso_chest_envelope_inputs"],
        )

        diagnostic = runner._body_optional_inputs(
            modules, "case", {
                "feet": {"builder": "foot_construction.py", "inputs": "foot-inputs.json"},
                "arms": {"inputs": "arm-inputs.json"},
                "head": {"inputs": "head-refinement-inputs.json"},
            }
        )
        self.assertIs(diagnostic["foot_builder"], legacy_foot)
        self.assertIs(diagnostic["foot_inputs"], modules["foot_inputs"]["cases"][0]["sides"])
        self.assertIs(diagnostic["head_inputs"], modules["head_refinement_inputs"]["cases"][0]["head"])

    def test_prepare_captures_tail_bundle_without_enabling_tail_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "experiment"
            (source / "tests").mkdir(parents=True)
            tail_files = {
                "runner.py": "# captured runner\n",
                "tail_construction.py": "# current tail constructor\n",
                "tail-inputs.json": "{\"source_case\": \"ordinary\"}\n",
                "tail-stage.md": "# tail stage\n",
                "tests/test_tail_construction.py": "# focused tail test\n",
            }
            for name, text in tail_files.items():
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            dependency = _dependency(root)
            snapshot = root / "snapshot"
            with mock.patch.object(runner, "HERE", source), \
                    mock.patch.object(runner, "CAPTURE_FILES", tuple(tail_files)), \
                    mock.patch.object(runner, "_dependency_identity", return_value=dependency):
                manifest = runner.prepare(snapshot)

            captured = {row["path"] for row in manifest["source"]["files"]}
            self.assertEqual(captured, set(tail_files))
            self.assertTrue(all(
                (snapshot / "source/experiments/connected-leg-assembly" / name).is_file()
                for name in tail_files
            ))
            self.assertNotIn("tail", manifest["source"].get("loaded_modules", []))

    def test_body_pose_transport_preserves_head_angles(self) -> None:
        poses = runner._protocol_poses({"baseline_poses": [{
            "id": "combined", "left": {"hip": 1, "knee": 2},
            "right": {"hip": 3, "knee": 4}, "head": {"yaw": 6, "nod": 4},
        }]})
        self.assertEqual(poses[0]["angles"]["head"], {"yaw": 6, "nod": 4})

    def test_rest_only_construction_exception_is_overall_error(self) -> None:
        class FailingConstruction:
            @staticmethod
            def build(_root, _leg_inputs):
                raise ValueError("synthetic constructor input-shape failure")

            @staticmethod
            def evaluate(_built):
                raise AssertionError("evaluate must not run after build failure")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot"
            source = snapshot / "source/experiments/connected-leg-assembly"
            source.mkdir(parents=True)
            (source / "runner.py").write_text("captured runner\n", encoding="utf-8")
            (source / "protocol.json").write_text(
                json.dumps({"baseline_poses": [{"id": "rest", "left": {"ankle": 0}, "right": {"ankle": 0}}]}),
                encoding="utf-8")
            (source / "inputs.json").write_text(json.dumps({"cases": [{"id": "human", "leg_inputs": {}}]}), encoding="utf-8")
            input_root = snapshot / "inputs"
            input_root.mkdir()
            for name, value in (("root.json", {}), ("rest.json", {}), ("binding.json", {})):
                (input_root / name).write_text(json.dumps(value), encoding="utf-8")
            path_map = []
            for field, name in (("root_mesh", "root.json"), ("prior_rest_mesh", "rest.json"), ("prior_hip_binding", "binding.json")):
                path_map.append({"case_id": "human", "field": field, "snapshot_path": f"inputs/{name}"})
            manifest = {"schema": "synthetic", "input_manifest": {"path_map": path_map}}
            output = root / "output"
            with mock.patch.object(runner, "verify", return_value=manifest) as verify_mock, \
                    mock.patch.object(runner, "__file__", str(source / "runner.py")), \
                    mock.patch.object(runner, "_load_collaborators", return_value={"construction": FailingConstruction()}):
                report = runner.run(snapshot, output, rest_only=True)
            self.assertEqual(report["cases"][0]["status"], "exception")
            self.assertEqual(report["status"], "error")
            self.assertFalse(report["full_pass"])
            self.assertEqual(verify_mock.call_count, 2)
            self.assertEqual(report["post_run_verification"]["status"], "verified")
            self.assertTrue((output / "run-report.json").is_file())

    def test_full_run_without_checks_keeps_unchecked_pose_evidence(self) -> None:
        mesh = {"vertices": [[0.0, 0.0, 0.0]], "quads": []}

        class Construction:
            @staticmethod
            def build(_root, _leg_inputs):
                return mesh

            @staticmethod
            def evaluate(_base):
                return [mesh]

        class Binding:
            @staticmethod
            def bind(*_args):
                return {"synthetic": True}

            @staticmethod
            def pose(_rest, _binding, _angles):
                return mesh

            @staticmethod
            def joint_points(_binding, _angles):
                return {"left": {"J": [0.0, 0.0, 0.0], "T": [0.0, -1.0, 0.0]}}

        protocol = {"baseline_poses": [
            {"id": "rest", "left": {"hip": 0, "knee": 0, "ankle": 0}, "right": {"hip": 0, "knee": 0, "ankle": 0}},
            {"id": "moving", "left": {"hip": 15, "knee": 10, "ankle": 0}, "right": {"hip": 0, "knee": 0, "ankle": 0}},
        ]}
        case = {"id": "synthetic", "leg_inputs": {}}
        values = {"root_mesh": mesh, "prior_rest_mesh": mesh, "prior_hip_binding": {}, "leg_inputs": {}}
        with tempfile.TemporaryDirectory() as directory:
            result = runner._case_run(
                {"id": "synthetic", "case": case, "values": values},
                protocol, {"construction": Construction(), "binding": Binding()},
                Path(directory) / "case", rest_only=False)
        self.assertEqual(result["status"], "pending", result)
        self.assertFalse(result["full_pass"])
        self.assertEqual([pose["id"] for pose in result["poses"]], ["rest", "moving"])
        self.assertEqual(result["checks"]["status"], "pending")
        self.assertEqual(len(result["bounds_inputs"]), len(result["poses"]) + 1)

    def test_source_rebuild_is_authoritative_and_foot_uses_final_mesh(self) -> None:
        cached_root = {"name": "cached-root", "vertices": [[0.0, 0.0, 0.0]], "quads": []}
        cached_rest = {"name": "cached-rest", "vertices": [[0.0, 0.0, 0.0]], "quads": []}
        source_root = {"name": "source-root", "vertices": [[1.0, 0.0, 0.0]], "quads": []}
        source_rest = {"name": "source-rest", "vertices": [[1.0, 1.0, 0.0]], "quads": []}
        leg_l0 = {"name": "leg-L0", "vertices": [[2.0, 0.0, 0.0]], "quads": []}
        leg_l2 = {"name": "leg-L2", "vertices": [[2.0, 1.0, 0.0]], "quads": []}
        foot_l0 = {"name": "foot-L0", "vertices": [[3.0, 0.0, 0.0]], "quads": []}
        foot_l2 = {"name": "foot-L2", "vertices": [[3.0, 1.0, 0.0]], "quads": []}
        calls: list[tuple[str, object]] = []

        class Construction:
            @staticmethod
            def build(root, _leg_inputs):
                calls.append(("leg-root", root))
                return leg_l0

            @staticmethod
            def evaluate(_mesh, levels=2):
                self.assertEqual(levels, 2)
                return [leg_l0, leg_l2]

        class RootSource:
            @staticmethod
            def reconstruct_source_case(_case):
                return {"levels": {"L0": source_root, "L2": source_rest},
                        "provenance": {"adapter": "root"}}

        source_binding = {"base_weights": [[1.0]], "evaluated_weights": [[1.0]],
                          "rest_frames": {"left": {}}}

        class HipSource:
            @staticmethod
            def bind_source_case(root, rest, _case, leg_inputs=None):
                calls.extend([("hip-root", root), ("hip-rest", rest),
                              ("hip-inputs", leg_inputs)])
                return {"binding": source_binding, "provenance": {"adapter": "hip"}}

        class FootConstruction:
            @staticmethod
            def build(base, _leg_inputs, _foot_inputs):
                calls.append(("foot-base", base))
                return foot_l0

            @staticmethod
            def evaluate(_mesh, levels=2):
                self.assertEqual(levels, 2)
                return [foot_l0, foot_l2]

        class Binding:
            @staticmethod
            def bind(*args):
                calls.append(("final-binding", args))
                return {"joint_order": [], "evaluated_weights": [[1.0]]}

            @staticmethod
            def pose(mesh, _binding, _angles):
                calls.append(("pose-mesh", mesh))
                return mesh

            @staticmethod
            def joint_points(_binding, _angles):
                return {}

        protocol = {"baseline_poses": [{"id": "rest", "left": {}, "right": {}}]}
        leg_inputs = {"left": {}, "right": {}}
        modules = {
            "construction": Construction(), "root_source": RootSource(),
            "hip_source": HipSource(), "foot_construction": FootConstruction(),
            "foot_inputs": {"cases": [{"case_id": "synthetic",
                                         "sides": {"left": {}, "right": {}}}]},
            "binding": Binding(),
        }
        values = {"root_mesh": cached_root, "prior_rest_mesh": cached_rest,
                  "prior_hip_binding": {"cached": True}, "original_case": {},
                  "leg_inputs": leg_inputs}
        with tempfile.TemporaryDirectory() as directory:
            legacy_case = Path(directory) / "case"
            result = runner._case_run(
                {"id": "synthetic", "case": {"id": "synthetic"}, "values": values},
                protocol, modules, legacy_case, rest_only=False)
            self.assertFalse(
                (legacy_case / "thorax-foundation-source-evidence.json").exists()
            )

        self.assertEqual(result["materialization"], "source-rebuilt")
        self.assertTrue(result["foot_materialized"])
        self.assertEqual(dict(calls)["leg-root"], source_root)
        self.assertEqual(dict(calls)["foot-base"], leg_l0)
        final_binding = dict(calls)["final-binding"]
        self.assertEqual(final_binding[0], foot_l0)
        self.assertEqual(final_binding[1], foot_l2)
        self.assertIs(final_binding[2], source_root)
        self.assertIs(final_binding[3], source_binding)
        self.assertEqual(result["source_rebuild"]["cache_role"],
                         "comparison-only; never a construction or binding input")

    def test_source_body_mode_injects_captured_modules_and_uses_final_levels(self) -> None:
        cached_root = {"name": "root", "vertices": [[0.0, 0.0, 0.0]], "quads": []}
        cached_rest = {"name": "root-rest", "vertices": [[0.0, 1.0, 0.0]], "quads": []}
        cached_binding = {"base_weights": [], "evaluated_weights": [], "rest_frames": {}}
        leg_l0 = {"name": "leg-l0", "vertices": [[1.0, 0.0, 0.0]], "quads": []}
        leg_l1 = {"name": "leg-l1", "vertices": [[1.0, 0.5, 0.0]], "quads": []}
        leg_l2 = {"name": "leg-l2", "vertices": [[1.0, 1.0, 0.0]], "quads": []}
        final_l0 = {"name": "body-l0", "vertices": [[2.0, 0.0, 0.0]], "quads": []}
        final_l2 = {"name": "body-l2", "vertices": [[2.0, 2.0, 0.0]], "quads": []}
        foundation_root = {"name": "foundation-root", "vertices": [[9.0, 0.0, 0.0]], "quads": []}
        foundation_rest = {"name": "foundation-rest", "vertices": [[9.0, 2.0, 0.0]], "quads": []}
        foundation_binding = {"base_weights": [9], "evaluated_weights": [9],
                              "rest_frames": {"foundation": True}}
        events = []

        class Construction:
            @staticmethod
            def build(root, _legs):
                events.append(("leg-build", root))
                return leg_l0

            @staticmethod
            def evaluate(mesh, levels=2):
                events.append(("leg-evaluate", mesh, levels))
                return [leg_l0, leg_l1, leg_l2]

        class RootSource:
            reconstruct_source_case = staticmethod(lambda _case: {"levels": {
                "L0": cached_root, "L2": cached_rest}})

        class HipSource:
            bind_source_case = staticmethod(lambda *_args, **_kwargs: {
                "binding": cached_binding, "provenance": {"adapter": "hip"}})

        class Body:
            class AssemblyDependencies:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs
                    events.append(("dependencies", kwargs))

            @staticmethod
            def assemble(source_case, legs, *, foot_inputs, arm_inputs,
                         head_inputs, dependencies, thorax_foundation_inputs=None):
                events.append(("body", source_case, legs, foot_inputs,
                               arm_inputs, head_inputs, dependencies,
                               thorax_foundation_inputs))
                rebuilt_root_l0 = (
                    foundation_root if thorax_foundation_inputs is not None else cached_root
                )
                rebuilt_root_l2 = (
                    foundation_rest if thorax_foundation_inputs is not None else cached_rest
                )
                rebuilt_binding = (
                    foundation_binding if thorax_foundation_inputs is not None else cached_binding
                )
                result = {
                    "rebuilt_root_l0": rebuilt_root_l0,
                    "rebuilt_root_l2": rebuilt_root_l2,
                    "rebuilt_root_binding": rebuilt_binding,
                    "final_l0": final_l0,
                    "final_l2": final_l2,
                    "binding": {"body": True},
                    "source_provenance": {"root": {}, "hip": {}},
                    "component_manifest": {"arms": {"status": "built"}},
                }
                if thorax_foundation_inputs is not None:
                    result["foundation_records"] = {
                        "selected_inputs": thorax_foundation_inputs,
                    }
                return result

        class Binding:
            @staticmethod
            def pose(rest, _binding, angles):
                events.append(("pose", rest, angles))
                return rest

            @staticmethod
            def joint_points(_binding, _angles):
                return {}

        arm_module = object()
        head_module = object()
        foot_module = object()
        modules = {
            "construction": Construction(), "root_source": RootSource(),
            "hip_source": HipSource(), "body_assembly": Body(),
            "binding": Binding(), "foot_construction": foot_module,
            "arm_construction": arm_module, "head_construction": head_module,
            "foot_inputs": {"cases": [{"case_id": "synthetic", "sides": {}}]},
            "arm_inputs": {"cases": [{"case_id": "synthetic", "sides": {}}]},
            "head_inputs": {"cases": [{"case_id": "synthetic", "head": {}}]},
            "thorax_foundation": object(),
            "thorax_foundation_baseline_inputs": {"schema": "thorax-baseline"},
            "thorax_foundation_width_inputs": {"schema": "thorax-width"},
            "thorax_foundation_fullness_inputs": {"schema": "thorax-fullness"},
        }
        values = {"root_mesh": cached_root, "prior_rest_mesh": cached_rest,
                  "prior_hip_binding": cached_binding,
                  "original_case": {"id": "synthetic"}, "leg_inputs": {}}
        protocol = runner._body_provisional_protocol(
            {"input_perturbations": []}, has_arms=True, has_head=True)
        with tempfile.TemporaryDirectory() as directory:
            legacy_case = Path(directory) / "case"
            result = runner._case_run(
                {"id": "synthetic", "case": {"id": "synthetic"}, "values": values},
                protocol, modules, legacy_case, rest_only=False)
            self.assertFalse(
                (legacy_case / "thorax-foundation-source-evidence.json").exists()
            )

        self.assertTrue(result["body_materialized"])
        self.assertTrue(result["foot_materialized"])
        self.assertTrue(result["source_rebuild"]["root_L0_exact"])
        self.assertTrue(result["source_rebuild"]["root_L2_exact"])
        self.assertNotIn("required_for_full_pass", result["source_rebuild"])
        self.assertEqual([event[0] for event in events],
                         ["dependencies", "body", "leg-build", "leg-evaluate",
                          "pose", "pose"])
        dependencies = events[0][1]
        self.assertIs(dependencies["root_source"], modules["root_source"])
        self.assertIs(dependencies["hip_source"], modules["hip_source"])
        self.assertIs(dependencies["leg_builder"], modules["construction"])
        self.assertIs(dependencies["binding"], modules["binding"])
        self.assertIs(dependencies["arm_builder"], arm_module)
        self.assertIs(dependencies["head_builder"], head_module)
        body_event = events[1]
        self.assertEqual(body_event[3], {})
        self.assertEqual(body_event[4], {})
        self.assertEqual(body_event[5], {})
        self.assertTrue(all(event[1] == final_l2 for event in events if event[0] == "pose"))
        self.assertEqual(len(result["poses"]), 2)

        with tempfile.TemporaryDirectory() as directory:
            foundation_result = runner._case_run(
                {"id": "synthetic", "case": {"id": "synthetic"}, "values": values},
                protocol, modules, Path(directory) / "case", rest_only=False,
                body_config={"thorax_foundation": {
                    "inputs": "thorax-foundation-baseline-inputs.json"
                }})
            evidence = Path(directory) / "case" / "thorax-foundation-source-evidence.json"
            self.assertEqual(foundation_result["thorax_foundation_source_evidence"],
                             "thorax-foundation-source-evidence.json")
            self.assertEqual(json.loads(evidence.read_text(encoding="utf-8")), {
                "selected_inputs": {"schema": "thorax-baseline"},
            })
            foundation_dependency = next(
                event[1] for event in events
                if event[0] == "dependencies" and "thorax_foundation" in event[1]
            )
            self.assertIs(foundation_dependency["thorax_foundation"],
                          modules["thorax_foundation"])
            foundation_body_event = next(
                event for event in reversed(events)
                if event[0] == "body" and event[-1] is not None
            )
            self.assertEqual(foundation_body_event[-1],
                             {"schema": "thorax-baseline"})
            self.assertFalse(foundation_result["source_rebuild"]["root_L0_exact"])
            self.assertFalse(foundation_result["source_rebuild"]["root_L2_exact"])
            self.assertFalse(
                any(foundation_result["source_rebuild"]["root_binding_exact"].values())
            )
            self.assertEqual(foundation_result["source_rebuild"]["comparison_role"],
                             "diagnostic-only")
            self.assertFalse(foundation_result["source_rebuild"]["required_for_full_pass"])
            self.assertIn("intentionally rebuilds J/skin",
                          foundation_result["source_rebuild"]["reason"])
            self.assertNotEqual(foundation_result["status"], "exception")

    def test_explicit_body_config_rejects_legacy_and_rest_only_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot"
            source = snapshot / runner.SNAPSHOT_SOURCE
            source.mkdir(parents=True)
            (source / "protocol.json").write_text("{}", encoding="utf-8")
            (source / "inputs.json").write_text("{}", encoding="utf-8")
            captured_runner = source / "runner.py"
            captured_runner.write_text("# captured runner\n", encoding="utf-8")
            with mock.patch.object(runner, "verify", return_value={}), \
                    mock.patch.object(runner, "_load_case_inputs", return_value=[]), \
                    mock.patch.object(runner, "_load_collaborators", return_value={}), \
                    mock.patch.object(runner, "__file__", str(captured_runner)):
                for rest_only in (False, True):
                    with self.subTest(rest_only=rest_only):
                        output = root / f"output-{rest_only}"
                        with self.assertRaisesRegex(
                                runner.RunnerError,
                                "requires source-driven body mode"):
                            runner.run(
                                snapshot, output,
                                rest_only=rest_only,
                                body_config="body-config.json",
                            )
                        self.assertFalse(output.exists())

    def test_foot_run_labels_legacy_perturbations_as_leg_only(self) -> None:
        mesh = {"vertices": [[0.0, 0.0, 0.0]], "quads": []}

        class Construction:
            @staticmethod
            def build(_root, _leg_inputs):
                return mesh

            @staticmethod
            def evaluate(_mesh, levels=2):
                return [mesh]

        class Foot:
            @staticmethod
            def build(_base, _leg_inputs, _foot_inputs):
                return mesh

            @staticmethod
            def evaluate(_mesh, levels=2):
                return [mesh]

        class Binding:
            @staticmethod
            def bind(*_args):
                return {"joint_order": [], "evaluated_weights": [[1.0]]}

            @staticmethod
            def pose(_mesh, _binding, _angles):
                return mesh

            @staticmethod
            def joint_points(_binding, _angles):
                return {}

        class Perturbations:
            @staticmethod
            def run_case(*_args):
                return {"status": "pass", "perturbations": [
                    {"id": "left_A", "status": "pass"},
                ]}

        protocol = {"baseline_poses": [{"id": "rest", "left": {}, "right": {}}],
                    "input_perturbations": [{"id": "left_A"}]}
        modules = {"construction": Construction(), "foot_construction": Foot(),
                   "foot_inputs": {"cases": [{"case_id": "synthetic",
                                                "sides": {"left": {}, "right": {}}}]},
                   "binding": Binding(), "perturbations": Perturbations()}
        values = {"root_mesh": mesh, "prior_rest_mesh": mesh,
                  "prior_hip_binding": {}, "leg_inputs": {}}
        with tempfile.TemporaryDirectory() as directory:
            result = runner._case_run(
                {"id": "synthetic", "case": {"id": "synthetic"}, "values": values},
                protocol, modules, Path(directory) / "case", rest_only=False)
        self.assertEqual(result["perturbations"]["status"], "leg-only")
        self.assertEqual(result["perturbations"]["coverage"], "leg-baseline-only")
        self.assertEqual(result["perturbations"]["foot_coverage"], "not-run")
        self.assertFalse(result["full_pass"])

    def test_checker_calls_use_immutable_inputs_and_original_l2(self) -> None:
        mesh = {"vertices": [[0.0, 0.0, 0.0]], "quads": []}
        calls = []

        class Construction:
            @staticmethod
            def build(_root, _leg_inputs):
                return mesh

            @staticmethod
            def evaluate(_base):
                return [mesh, mesh]

        class Binding:
            @staticmethod
            def bind(*_args):
                return {"synthetic": True}

            @staticmethod
            def pose(_rest, _binding, _angles):
                return mesh

            @staticmethod
            def joint_points(_binding, _angles):
                return {}

        class Checks:
            @staticmethod
            def check_mesh(*args):
                calls.append(("mesh", args))
                return {"pass": True}

            @staticmethod
            def check_binding(*args):
                calls.append(("binding", args))
                return {"pass": True}

            @staticmethod
            def check_pose(*args):
                calls.append(("pose", args))
                return {"pass": True}

            @staticmethod
            def compare_root(*args):
                calls.append(("root", args))
                return {"pass": True}

        protocol = {"baseline_poses": [{"id": "rest", "left": {"ankle": 0}, "right": {"ankle": 0}}]}
        leg_inputs = {"left": {"J": [0, 0, 0]}, "right": {"J": [0, 0, 0]}}
        with tempfile.TemporaryDirectory() as directory:
            result = runner._case_run(
                {"id": "synthetic", "case": {"id": "synthetic", "leg_inputs": leg_inputs},
                 "values": {"root_mesh": mesh, "prior_rest_mesh": mesh,
                            "prior_hip_binding": {}, "leg_inputs": leg_inputs}},
                protocol, {"construction": Construction(), "binding": Binding(), "checks": Checks()},
                Path(directory) / "case", rest_only=False)
        self.assertEqual(result["status"], "technical-pass", result)
        by_name = dict(calls)
        self.assertEqual(len(by_name["binding"]), 7)
        self.assertIs(by_name["binding"][5], leg_inputs)
        self.assertEqual(len(by_name["pose"]), 6)
        self.assertIs(by_name["pose"][5], leg_inputs)
        self.assertIs(by_name["root"][0], mesh)
        self.assertIs(by_name["root"][2], mesh)

    def test_perturbation_hook_saves_all_returned_meshes_and_never_passes_missing(self) -> None:
        mesh = {"vertices": [[0.0, 0.0, 0.0]], "quads": []}
        calls = []

        class Construction:
            @staticmethod
            def build(_root, _leg_inputs):
                return mesh

            @staticmethod
            def evaluate(_base):
                return [mesh, mesh]

        class Binding:
            @staticmethod
            def bind(*_args):
                return {"synthetic": True}

            @staticmethod
            def pose(_rest, _binding, _angles):
                return mesh

            @staticmethod
            def joint_points(_binding, _angles):
                return {}

        class Checks:
            check_mesh = staticmethod(lambda *_args: {"pass": True})
            check_binding = staticmethod(lambda *_args: {"pass": True})
            check_pose = staticmethod(lambda *_args: {"pass": True})
            compare_root = staticmethod(lambda *_args: {"pass": True})

        class Perturbations:
            @staticmethod
            def run_case(*args):
                calls.append(args)
                return {"status": "pass", "perturbations": [
                    {"id": "left_A_y_minus_0.02", "status": "pass", "diagnostic_meshes": {"actual": mesh}},
                    {"id": "left_calf_posterior_radius_times_1.10", "status": "pass", "diagnostic_meshes": {"failed": mesh}},
                    {"id": "left_J_y_plus_0.01_at_hip15", "status": "pass", "diagnostic_meshes": {"expected": mesh}},
                ]}

        protocol = {"baseline_poses": [{"id": "rest", "left": {"ankle": 0}, "right": {"ankle": 0}}],
                    "input_perturbations": [
                        {"id": "left_A_y_minus_0.02"},
                        {"id": "left_calf_posterior_radius_times_1.10"},
                        {"id": "left_J_y_plus_0.01_at_hip15"},
                    ]}
        values = {"root_mesh": mesh, "prior_rest_mesh": mesh, "prior_hip_binding": {}, "leg_inputs": {}}
        modules = {"construction": Construction(), "binding": Binding(), "checks": Checks(),
                   "perturbations": Perturbations()}
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory) / "case"
            result = runner._case_run({"id": "synthetic", "case": {"id": "synthetic"}, "values": values},
                                      protocol, modules, case_dir, rest_only=False)
            self.assertTrue((case_dir / "perturbations.json").is_file())
            self.assertTrue((case_dir / "perturbations/left_A_y_minus_0.02/actual.json").is_file())
            self.assertTrue((case_dir / "perturbations/left_calf_posterior_radius_times_1.10/failed.json").is_file())
            self.assertTrue((case_dir / "perturbations/left_J_y_plus_0.01_at_hip15/expected.json").is_file())
        self.assertEqual(result["status"], "technical-pass", result)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]), 10)

        missing = dict(result)
        missing["perturbations"] = {"status": "pass", "perturbations": []}
        self.assertFalse(runner._perturbation_result_ready(
            missing["perturbations"], [
                "left_A_y_minus_0.02",
                "left_calf_posterior_radius_times_1.10",
                "left_J_y_plus_0.01_at_hip15",
            ]))

    def test_pose_failure_blocks_present_perturbation_dispatch_with_cause(self) -> None:
        mesh = {"vertices": [[0.0, 0.0, 0.0]], "quads": []}

        class Construction:
            @staticmethod
            def build(_root, _leg_inputs):
                return mesh

            @staticmethod
            def evaluate(_base):
                return [mesh, mesh]

        class Binding:
            @staticmethod
            def bind(*_args):
                return {"synthetic": True}

            @staticmethod
            def pose(_rest, _binding, _angles):
                raise ValueError("synthetic pose input failure")

            @staticmethod
            def joint_points(_binding, _angles):
                raise AssertionError("joint_points must not run after pose failure")

        class Perturbations:
            @staticmethod
            def run_case(*_args):
                raise AssertionError("perturbations must not dispatch after pose failure")

        protocol = {
            "baseline_poses": [{"id": "rest", "left": {"hip": 0, "knee": 0, "ankle": 0},
                                "right": {"hip": 0, "knee": 0, "ankle": 0}}],
            "input_perturbations": [
                {"id": "left_A_y_minus_0.02"},
                {"id": "left_calf_posterior_radius_times_1.10"},
                {"id": "left_J_y_plus_0.01_at_hip15"},
            ],
        }
        values = {"root_mesh": mesh, "prior_rest_mesh": mesh,
                  "prior_hip_binding": {}, "leg_inputs": {}}
        with tempfile.TemporaryDirectory() as directory:
            result = runner._case_run(
                {"id": "synthetic", "case": {"id": "synthetic"}, "values": values},
                protocol,
                {"construction": Construction(), "binding": Binding(),
                 "perturbations": Perturbations()},
                Path(directory) / "case", rest_only=False)
        self.assertEqual(result["status"], "exception")
        self.assertEqual(result["perturbations"]["status"], "blocked-by-earlier-error")
        self.assertEqual(result["perturbations"]["execution"], "not-run")
        self.assertEqual(result["perturbations"]["blocker"]["stage"], "pose:rest")
        self.assertEqual(result["perturbations"]["blocker"]["message"], "synthetic pose input failure")

    def test_shared_bounds_include_outlying_perturbation_surface(self) -> None:
        rest = {"vertices": [[0.0, 0.0, 0.0]], "quads": []}
        outlier = {"vertices": [[100.0, -100.0, 50.0]], "quads": []}
        results = [{"bounds_inputs": [rest],
                    "perturbation_meshes": [{"mesh": outlier}]}]
        bounds = runner._bounds(runner._render_bounds_inputs(results))
        self.assertLessEqual(bounds[0][0], 100.0)
        self.assertLessEqual(bounds[0][1], -100.0)
        self.assertGreaterEqual(bounds[1][2], 50.0)

    def test_cli_returns_nonzero_for_failed_execution(self) -> None:
        with mock.patch.object(runner, "run", return_value={"status": "error"}):
            self.assertEqual(runner._main(["run", "--snapshot", "/tmp/snapshot", "--output", "/tmp/output"]), 1)

    def test_prepare_captures_exact_sources_and_mapped_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "experiment"
            source.mkdir()
            for name, text in {
                "runner.py": "# captured runner\n",
                "protocol.json": '{"poses":[{"id":"rest"}]}\n',
                "construction.py": "import binding\n",
                "binding.py": "VALUE = 1\n",
            }.items():
                (source / name).write_text(text, encoding="utf-8")
            for name, value in {
                "root.json": {"vertices": [[0, 0, 0]]},
                "prior-rest.json": {"vertices": [[0, 0, 0]]},
                "prior-binding.json": {"weights": []},
            }.items():
                (source / name).write_text(json.dumps(value), encoding="utf-8")
            def descriptor(name: str) -> dict[str, str]:
                path = source / name
                return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            (source / "inputs.json").write_text(json.dumps({"cases": [{
                "id": "ordinary", "root_mesh": descriptor("root.json"),
                "prior_rest_mesh": descriptor("prior-rest.json"),
                "prior_hip_binding": descriptor("prior-binding.json"),
                "leg_inputs": {"J": [0, 1, 0], "T": [0, 0, 0], "K": [0, -1, 0], "A": [0, -2, 0]},
            }]}), encoding="utf-8")
            dependency = _dependency(root)
            snapshot = root / "snapshot"
            with mock.patch.object(runner, "HERE", source), \
                    mock.patch.object(runner, "CAPTURE_FILES", (
                        "runner.py", "construction.py", "binding.py", "protocol.json", "inputs.json")), \
                    mock.patch.object(runner, "_dependency_identity", return_value=dependency):
                manifest = runner.prepare(snapshot)
                checked = runner.verify(snapshot)
            self.assertEqual(checked["schema"], manifest["schema"])
            self.assertTrue((snapshot / "source/experiments/connected-leg-assembly/runner.py").is_file())
            self.assertTrue((snapshot / "source/experiments/connected-leg-assembly/binding.py").is_file())
            path_map = manifest["input_manifest"]["path_map"]
            self.assertEqual({row["field"] for row in path_map}, {
                "root_mesh", "prior_rest_mesh", "prior_hip_binding"})
            self.assertTrue(all(str(row["snapshot_path"]).startswith("inputs/") for row in path_map))
            self.assertTrue(manifest["dependency"]["reused_without_copy"])
            self.assertIn("does not claim hermetic", " ".join(manifest["host"]["limitations"]).lower())

    def test_prepare_refuses_existing_snapshot_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "experiment"
            source.mkdir()
            (source / "runner.py").write_text("runner\n", encoding="utf-8")
            snapshot = Path(directory) / "snapshot"
            snapshot.mkdir()
            with mock.patch.object(runner, "HERE", source), \
                    mock.patch.object(runner, "CAPTURE_FILES", ("runner.py",)):
                with self.assertRaisesRegex(runner.RunnerError, "snapshot must be absent"):
                    runner.prepare(snapshot)
            self.assertEqual(list(snapshot.iterdir()), [])

    def test_verify_refuses_drifted_captured_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "experiment"
            source.mkdir()
            (source / "runner.py").write_text("runner\n", encoding="utf-8")
            snapshot = root / "snapshot"
            dependency = _dependency(root)
            with mock.patch.object(runner, "HERE", source), \
                    mock.patch.object(runner, "CAPTURE_FILES", ("runner.py",)), \
                    mock.patch.object(runner, "_dependency_identity", return_value=dependency):
                manifest = runner.prepare(snapshot)
            # A source-only staged capture has no input files; adding one is
            # still rejected as unexpected output rather than silently ignored.
            (snapshot / "unexpected.json").write_text("{}", encoding="utf-8")
            with mock.patch.object(runner, "_dependency_identity", return_value=dependency):
                with self.assertRaisesRegex(runner.RunnerError, "unexpected files"):
                    runner.verify(snapshot)
            self.assertEqual(manifest["status"], "prepared")


if __name__ == "__main__":
    unittest.main()
