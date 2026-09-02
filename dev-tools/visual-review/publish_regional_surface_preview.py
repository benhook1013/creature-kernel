#!/usr/bin/env python3
"""Publish one standard-neutral regional-surface preview.

The renderer is deliberately an experiment-local dependency and is loaded
only when publication is requested.  This module owns the small boundary
between a validated current-form input, the renderer's immutable result, and
the existing immutable visual-review session format.  It does not contain
surface construction or rendering logic.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import struct
import sys
import tempfile
import threading
import types
import zlib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple, NoReturn

import common
from common import ValidationError, canonical_json, validate_id
from publish import PublishError, publish_session


class RegionalSurfacePublicationError(RuntimeError):
    """A bounded, fail-closed regional-surface publication failure."""


PUBLISHER_IMPLEMENTATION_ID = "regional-surface-publication-v1"
PREVIEW_FORMAT = "creature-kernel.disposable-regional-surface-preview.v2"
CANDIDATE_FORMAT = "creature-kernel.disposable-regional-surface-candidate.v3"
RENDERER_SOURCE_ID = "regional_surface_preview.render_regional_surface_preview"
RENDERER_ENTRYPOINT_FILENAME = "regional_surface_preview.py"
RENDERER_DEPENDENCY_FILENAMES = (
    "regional_surface_candidate.py",
    "regional_hybrid_surface.py",
    "surface_preview.py",
)
RENDERER_SOURCE_FILENAMES = (
    RENDERER_ENTRYPOINT_FILENAME,
    *RENDERER_DEPENDENCY_FILENAMES,
)
RENDERER_IMPORTED_MODULE_NAMES = (
    "regional_surface_preview_surface_preview",
    "regional_surface_preview_candidate",
    "regional_surface_candidate_surface_preview",
    "regional_surface_candidate_hybrid",
)
MAX_RENDERER_SOURCE_BYTES = 4 * 1024 * 1024
MAX_RENDERER_BUNDLE_BYTES = MAX_RENDERER_SOURCE_BYTES * len(RENDERER_SOURCE_FILENAMES)
MAX_PUBLISHER_SOURCE_BYTES = 4 * 1024 * 1024
EXTERNAL_ID = "standard_neutral_reference"
SOURCE_VARIANT = "neutral-v0"
EXPECTED_SOURCE_DOCUMENT = (
    "stylized_digitigrade_biped_authored_form__structural_profile__"
    "standard_neutral_reference"
)
EXPECTED_CANDIDATE_TYPE = "regional_surface_preview_candidate.RegionalSurfaceCandidate"
EXPECTED_BASE_TYPE = "regional_surface_candidate_hybrid.AxialMassChain"
EXPECTED_FINAL_FIELD_TYPE = "regional_surface_candidate_hybrid.FullSectionComposite"
EXPECTED_OPERAND_EVALUATORS = {
    "skin-source:base": f"{EXPECTED_BASE_TYPE}.evaluate",
    "skin-source:route": "regional_surface_candidate_hybrid.AnisotropicSectionSweep.evaluate",
    "derived-interface-patch": "regional_surface_candidate_hybrid.ParentTargetedInterfacePatch.evaluate",
}
GROUP_ID = "regional-surface-preview"
TITLE = "Standard neutral regional-surface preview"
DESCRIPTION = (
    "Disposable standard-neutral regional-surface preview; this is visual "
    "implementation evidence and not a production geometry or topology contract."
)
INSTRUCTIONS = (
    "Inspect the standard neutral reference for regional surface continuity, "
    "silhouette, and diagnostics. This preview records no acceptance decision."
)

MAX_PREPARED_INPUT_BYTES = common.MAX_JSON_BYTES
MAX_RENDERER_METADATA_BYTES = common.MAX_JSON_BYTES
MAX_RENDERER_DESCRIPTOR_BYTES = common.MAX_CONTEXT_JSON
MAX_PNG_BYTES = 256 * 1024 * 1024
# The current regional candidate bounds are 20..80 samples per axis.  Keep the
# publication boundary aligned with the renderer's actual bounded contract.
MIN_MESH_SAMPLES = 20
MAX_MESH_SAMPLES = 80
MAX_MESH_PADDING = 1_000_000.0
MAX_PNG_WIDTH = 4096
MAX_PNG_HEIGHT = 4096
MAX_PNG_INFLATED_BYTES = 64 * 1024 * 1024
EXPECTED_PNG_FORMAT = "PNG"
EXPECTED_PNG_MODE = "RGB"
EXPECTED_CANVAS = {"width": 1800, "height": 1500, "mode": EXPECTED_PNG_MODE}
EXPECTED_VIEWS = ["front", "side", "three-quarter"]
EXPECTED_PANEL_CONTENTS = ["skin", "field-contributors", "source-diagnostics"]
EXPECTED_REGION_NAMES = ["pelvis", "abdominal-bridge", "ribcage"]
EXPECTED_CONTROL_NAMES = [
    "left-shoulder-peak",
    "left-axilla",
    "right-shoulder-peak",
    "right-axilla",
]
EXPECTED_CONTROL_FRAME_ROLE = "form_shoulder_control"
EXPECTED_CONTROL_AUTHORITY_INFLUENCE = "proven"
EXPECTED_CONTROL_LOCAL_INFLUENCE = False
EXPECTED_CONTROL_LOCAL_INFLUENCE_STATUS = "unverified"
EXPECTED_CONTROL_VISUAL_FLOOR_SATISFACTION = "unverified"
EXPECTED_AUTHORITY_CONTROL_IDENTITIES = [
    (f"control:{name}", "authority-only-control", f"control:{name}")
    for name in EXPECTED_CONTROL_NAMES
]
EXPECTED_ROUTE_NAMES = [
    "head-neck",
    "left-arm",
    "right-arm",
    "left-leg",
    "right-leg",
    "left-foot",
    "right-foot",
]
EXPECTED_SKIN_SOURCE_IDENTITIES = [
    ("base", "skin-source", "chain:regional-surface"),
    *[(f"route:{name}", "skin-source", f"route:{name}") for name in EXPECTED_ROUTE_NAMES],
]
EXPECTED_INTERFACE_RELATIONS = [
    ("torso", "head-neck"),
    ("torso", "left-arm"),
    ("torso", "right-arm"),
    ("torso", "left-leg"),
    ("torso", "right-leg"),
    ("left-leg", "left-foot"),
    ("right-leg", "right-foot"),
]
EXPECTED_INTERFACE_GRAPH_RELATIONS = sorted(EXPECTED_INTERFACE_RELATIONS)
EXPECTED_PATCH_IDENTITIES = [
    (f"patch:{parent}->{child}", "derived-interface-patch", f"interface:{parent}->{child}", parent, child)
    for parent, child in EXPECTED_INTERFACE_RELATIONS
]
EXPECTED_OPERANDS = (
    EXPECTED_SKIN_SOURCE_IDENTITIES
    + EXPECTED_PATCH_IDENTITIES
)
# FullSectionComposite owns a deterministic name-sorted attachment view; the
# authored route and operand inventories remain in their declared order.
EXPECTED_ATTACHMENT_NAMES = sorted(EXPECTED_ROUTE_NAMES)
EXPECTED_GRAPH_PATCH_IDS = [
    f"interface:{parent}->{child}" for parent, child in EXPECTED_INTERFACE_GRAPH_RELATIONS
]
EXPECTED_FINAL_SKIN_SOURCE_PATHS = [
    "candidate.chain",
    *(f"candidate.routes[{index}]" for index in range(len(EXPECTED_ROUTE_NAMES))),
]
EXPECTED_PANEL_ORDER = [
    f"{view}-{content}"
    for content in EXPECTED_PANEL_CONTENTS
    for view in EXPECTED_VIEWS
]
EXPECTED_PROJECTION_BASES = {
    "front": "x-right/y-up/z-depth",
    "side": "-z-right/y-up/x-depth",
    "three-quarter": "front-right/y-up/depth",
}
EXPECTED_PROJECTION_BASES_MATRICES = {
    "front": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    "side": [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
    "three-quarter": [
        [1.0 / math.sqrt(2.0), 0.0, -1.0 / math.sqrt(2.0)],
        [0.0, 1.0, 0.0],
        [1.0 / math.sqrt(2.0), 0.0, 1.0 / math.sqrt(2.0)],
    ],
}
EXPECTED_WITNESS_COUNT = (
    len(EXPECTED_REGION_NAMES)
    + len(EXPECTED_ROUTE_NAMES)
    + len(EXPECTED_INTERFACE_RELATIONS)
    + len(EXPECTED_CONTROL_NAMES)
)
EXPECTED_WITNESS_IDENTITIES = [
    *(f"region:{name}" for name in EXPECTED_REGION_NAMES),
    *(f"route:{name}" for name in EXPECTED_ROUTE_NAMES),
    *(f"patch:{parent}->{child}" for parent, child in EXPECTED_INTERFACE_RELATIONS),
    *(f"control:{name}" for name in EXPECTED_CONTROL_NAMES),
]
EXPECTED_TORSO_STATION_NAMES = [
    "lower-pelvis",
    "upper-pelvis",
    "lower-abdomen",
    "waist-abdomen",
    "upper-abdomen",
    "lower-ribcage",
    "upper-ribcage-shoulder",
]
EXPECTED_TORSO_REGION_INTERVALS = [[0, 2], [2, 4], [4, 6]]
EXPECTED_ROUTE_SECTION_NAMES = {
    "head-neck": [
        "neck-collar",
        "neck-upper",
        "head-base",
        "cranium-mid",
        "cranium-crown",
        "muzzle-root",
        "muzzle-mid",
        "muzzle-tip",
    ],
    "left-arm": ["torso-arm-interface", "upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "wrist-transition", "forearm-distal"],
    "right-arm": ["torso-arm-interface", "upper-arm-start", "upper-arm-midpoint", "elbow", "forearm-midpoint", "wrist-transition", "forearm-distal"],
    "left-leg": ["pelvis-seat", "hip-cup-rim", "femoral-neck", "thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"],
    "right-leg": ["pelvis-seat", "hip-cup-rim", "femoral-neck", "thigh-start", "thigh-midpoint", "knee", "shin-midpoint", "hock-endpoint"],
    "left-foot": ["hock-endpoint", "pad", "toe"],
    "right-foot": ["hock-endpoint", "pad", "toe"],
}
EXPECTED_ARM_INTERFACE_ROUTE_INDEX = 0
EXPECTED_ARM_SHOULDER_CLOSURE_ROUTE_INDEX = 1
EXPECTED_ARM_ELBOW_ROUTE_INDEX = 3
EXPECTED_ARM_WRIST_TRANSITION_ROUTE_INDEX = 5
EXPECTED_ARM_TOTAL_SECTION_COUNT = 7
EXPECTED_ARM_CONNECTION_COUNT = 6
EXPECTED_ARM_AUTHORED_SOURCE_INDICES = [0, 1, 2, 3, 4]
EXPECTED_ROUTE_BINDING_EVIDENCE_COUNT = 42
EXPECTED_TOTAL_BINDING_EVIDENCE_COUNT = 53
EXPECTED_LEG_PELVIS_SEAT_ROUTE_INDEX = 0
EXPECTED_LEG_HIP_CUP_RIM_ROUTE_INDEX = 1
EXPECTED_LEG_FEMORAL_NECK_ROUTE_INDEX = 2
EXPECTED_LEG_KNEE_ROUTE_INDEX = 5
EXPECTED_LEG_HOCK_ROUTE_INDEX = 7
EXPECTED_LEG_AUTHORED_SOURCE_INDICES = [0, 1, 2, 3, 4]
EXPECTED_LEG_AUTHORED_SECTION_COUNT = 5
EXPECTED_LEG_DERIVED_SECTION_NAMES = ["pelvis-seat", "hip-cup-rim", "femoral-neck"]
EXPECTED_LEG_TOTAL_SECTION_COUNT = 8
EXPECTED_LEG_CONNECTION_COUNT = 7
EXPECTED_ROUTE_METADATA_FIELDS = {
    "routes",
    "count",
    "names",
    "required_head_neck_sections",
    "required_head_neck_connections",
    "bilateral_arm_authored_sections",
    "bilateral_arm_total_sections",
    "binding_evidence_count",
    "total_binding_evidence_count",
    "bilateral_leg_authored_sections",
    "bilateral_leg_derived_sections",
    "bilateral_leg_total_sections",
    "bilateral_foot_authored_sections",
    "endpoint_closures_explicit",
    "shared_interfaces",
}
EXPECTED_HEAD_CONNECTIONS = [
    ("neck-collar-to-neck-upper", 0, 1, "vertical-neck-cranium"),
    ("neck-upper-to-head-base", 1, 2, "vertical-neck-cranium"),
    ("head-base-to-cranium-mid", 2, 3, "vertical-neck-cranium"),
    ("cranium-mid-to-cranium-crown", 3, 4, "vertical-neck-cranium"),
    ("cranium-mid-to-muzzle-root", 3, 5, "forward-muzzle"),
    ("muzzle-root-to-muzzle-mid", 5, 6, "forward-muzzle"),
    ("muzzle-mid-to-muzzle-tip", 6, 7, "forward-muzzle"),
]
TRACE_TOLERANCE = 2.0e-9
INFLUENCE_TOLERANCE = 1.0e-12
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RENDERER_LOAD_LOCK = common.__dict__.setdefault(
    "_CK_REGIONAL_SURFACE_RENDERER_LOAD_LOCK",
    threading.RLock(),
)


class _IdentityUniverse:
    __slots__ = ("semantic_keys", "source_keys")

    def __init__(
        self,
        semantic_keys: frozenset[str],
        source_keys: frozenset[str],
    ) -> None:
        self.semantic_keys = semantic_keys
        self.source_keys = source_keys

    @property
    def report_keys(self) -> frozenset[str]:
        return self.semantic_keys | self.source_keys


class RendererDependencySourceSnapshot(NamedTuple):
    """One exact file-relative renderer dependency retained for execution."""

    path: Path
    source_bytes: bytes
    sha256: str

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "id": self.path.name,
            "bytes": len(self.source_bytes),
            "sha256": self.sha256,
        }


class RendererSourceSnapshot(NamedTuple):
    """The exact four-file renderer source bundle retained for execution."""

    path: Path
    source_bytes: bytes
    sha256: str
    dependencies: tuple[RendererDependencySourceSnapshot, ...]

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "id": RENDERER_SOURCE_ID,
            "bytes": len(self.source_bytes),
            "sha256": self.sha256,
            "dependencies": [dependency.identity for dependency in self.dependencies],
        }


class PublisherSourceSnapshot(NamedTuple):
    """The immutable publisher bytes from which all public behavior executes."""

    path: Path
    source_bytes: bytes
    sha256: str

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "id": PUBLISHER_IMPLEMENTATION_ID,
            "bytes": len(self.source_bytes),
            "sha256": self.sha256,
        }


class _DuplicateJSONMemberError(ValueError):
    """Raised when a prepared-form JSON object repeats a member name."""


def _reject_duplicate_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONMemberError(
                f"duplicate JSON object member {key!r}"
            )
        result[key] = value
    return result


def _fail(message: str) -> NoReturn:
    raise RegionalSurfacePublicationError(message)


def _json_copy(value: Any, where: str, *, maximum: int) -> Any:
    """Return detached canonical JSON data, rejecting non-JSON values."""

    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        _fail(f"{where} is not JSON-compatible: {exc}")
    if len(encoded) > maximum:
        _fail(f"{where} exceeds {maximum} bytes")
    try:
        return json.loads(encoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        _fail(f"{where} could not be normalized as JSON: {exc}")


def _canonical_bytes(value: Any, where: str, *, maximum: int) -> bytes:
    copied = _json_copy(value, where, maximum=maximum)
    try:
        return json.dumps(
            copied,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        _fail(f"{where} is not deterministically serializable: {exc}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_value(value: Any, where: str, *, maximum: int) -> str:
    return _sha256(_canonical_bytes(value, where, maximum=maximum))


def _text(value: Any, where: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        _fail(f"{where} must be a non-empty string of at most {maximum} characters")
    return value


def _digest(value: Any, where: str) -> str:
    result = _text(value, where, maximum=64)
    if SHA256_RE.fullmatch(result) is None or result == "0" * 64:
        _fail(f"{where} must be a lowercase SHA-256 digest")
    return result


def _mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unexpected {', '.join(extra)}")
        _fail(f"{where} has invalid fields ({'; '.join(details)})")


def _source_identity(anchors: list[str], role: str) -> dict[str, Any]:
    return {"namespace": "main", "anchors": anchors, "kind": "part", "role": role}


def _source_address(anchors: list[str], role: str) -> str:
    return json.dumps(
        _source_identity(anchors, role),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _expected_control_binding(name: str) -> dict[str, Any]:
    if name not in EXPECTED_CONTROL_NAMES:
        _fail(f"expected shoulder control binding requested for {name}")
    side = name.split("-", 1)[0]
    role = "form_shoulder_peak" if name.endswith("shoulder-peak") else "form_axilla"
    owner = _source_identity([side], "upper_arm")
    frame = {"owner": owner, "role": EXPECTED_CONTROL_FRAME_ROLE}
    source_key = "source-landmark:" + json.dumps(
        {
            "frame": frame,
            "namespace": "main",
            "owner": owner,
            "role": role,
            "side": side,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "name": name,
        "namespace": "main",
        "side": side,
        "owner": owner,
        "role": role,
        "frame": frame,
        "frame_role": EXPECTED_CONTROL_FRAME_ROLE,
        "semantic_key": f"control:{name}",
        "source_key": source_key,
        "canonical_source_key": source_key,
        "authority_only": True,
        "skin_consumer": False,
        "counterfactual_authority_bound_influence": EXPECTED_CONTROL_AUTHORITY_INFLUENCE,
        "control_local_final_skin_influence": EXPECTED_CONTROL_LOCAL_INFLUENCE,
        "control_local_final_skin_influence_status": EXPECTED_CONTROL_LOCAL_INFLUENCE_STATUS,
        "visual_floor_satisfaction": EXPECTED_CONTROL_VISUAL_FLOOR_SATISFACTION,
        "interface_id": f"interface:torso->{side}-arm",
    }


def _validate_candidate_control_record(
    value: Any,
    name: str,
    where: str,
) -> dict[str, Any]:
    record = _mapping(value, where)
    expected = _expected_control_binding(name)
    _exact_fields(record, set(expected), where)
    if record != expected:
        _fail(f"{where} identity is invalid")
    return record


def _expected_arm_route_sections(route_name: str) -> list[dict[str, Any]]:
    """Reconstruct the v3 candidate's arm route and derived interfaces."""

    if route_name not in {"left-arm", "right-arm"}:
        _fail(f"expected arm route requested for {route_name}")
    side = route_name.split("-", 1)[0]
    torso_address = _source_address([], "torso")
    upper_arm_address = _source_address([side], "upper_arm")
    interface_source = (
        f"derived-torso-arm-interface:torso={torso_address}:"
        f"upper-arm={upper_arm_address}"
    )
    sections = [
        {
            "index": EXPECTED_ARM_INTERFACE_ROUTE_INDEX,
            "name": "torso-arm-interface",
            "source_key": interface_source,
            "semantic_key": f"section:{route_name}:torso-arm-interface:{interface_source}",
            "source_index": None,
            "derived": True,
        }
    ]
    authored_names = (
        "upper-arm-start",
        "upper-arm-midpoint",
        "elbow",
        "forearm-midpoint",
        "forearm-distal",
    )
    for index, (name, source_index) in enumerate(
        zip(authored_names, EXPECTED_ARM_AUTHORED_SOURCE_INDICES),
        start=1,
    ):
        owner_role = "upper_arm" if source_index < 3 else "forearm"
        source_key = f"source-route:{route_name}:{name}:{_source_address([side], owner_role)}"
        sections.append(
            {
                "index": index if index <= 4 else EXPECTED_ARM_WRIST_TRANSITION_ROUTE_INDEX + 1,
                "name": name,
                "source_key": source_key,
                "semantic_key": f"section:{route_name}:{name}:{_source_address([side], owner_role)}",
                "source_index": source_index,
                "derived": False,
            }
        )
    wrist_source = (
        f"derived-wrist-transition:forearm={_source_address([side], 'forearm')}:"
        f"hand={_source_address([side], 'hand')}"
    )
    wrist = {
        "index": EXPECTED_ARM_WRIST_TRANSITION_ROUTE_INDEX,
        "name": "wrist-transition",
        "source_key": wrist_source,
        "semantic_key": f"section:{route_name}:wrist-transition:{wrist_source}",
        "source_index": None,
        "derived": True,
    }
    sections.insert(EXPECTED_ARM_WRIST_TRANSITION_ROUTE_INDEX, wrist)
    return sections


def _expected_leg_route_sections(route_name: str) -> list[dict[str, Any]]:
    """Reconstruct the v3 leg route with its live hip-cup sections."""

    if route_name not in {"left-leg", "right-leg"}:
        _fail(f"expected leg route requested for {route_name}")
    side = route_name.split("-", 1)[0]
    pelvis_address = _source_address([], "pelvis")
    thigh_address = _source_address([side], "thigh")
    def derived_section(index: int, name: str) -> dict[str, Any]:
        source_key = (
            f"derived-{name}:pelvis={pelvis_address}:thigh={thigh_address}"
        )
        return {
            "index": index,
            "name": name,
            "source_key": source_key,
            "semantic_key": f"section:{route_name}:{name}:{source_key}",
            "source_index": None,
            "derived": True,
        }

    sections = [
        derived_section(index, name)
        for index, name in enumerate(EXPECTED_LEG_DERIVED_SECTION_NAMES)
    ]
    for route_index, (name, source_index) in enumerate(
        zip(
            EXPECTED_ROUTE_SECTION_NAMES[route_name][len(EXPECTED_LEG_DERIVED_SECTION_NAMES):],
            EXPECTED_LEG_AUTHORED_SOURCE_INDICES,
        ),
        start=len(EXPECTED_LEG_DERIVED_SECTION_NAMES),
    ):
        role = "thigh" if source_index < 3 else "shin"
        owner = _source_address([side], role)
        sections.append(
            {
                "index": route_index,
                "name": name,
                "source_key": f"source-route:{route_name}:{name}:{owner}",
                "semantic_key": f"section:{route_name}:{name}:{owner}",
                "source_index": source_index,
                "derived": False,
            }
        )
    return sections


def _expected_foot_route_sections(
    route_name: str,
    shared_hock: dict[str, Any],
) -> list[dict[str, Any]]:
    """Reconstruct a foot route and its explicit borrowed leg-authored hock."""

    if route_name not in {"left-foot", "right-foot"}:
        _fail(f"expected foot route requested for {route_name}")
    leg_route = route_name.replace("-foot", "-leg")
    side = route_name.split("-", 1)[0]
    _exact_fields(
        shared_hock,
        {"index", "name", "source_key", "semantic_key", "source_index", "derived"},
        f"renderer candidate route {route_name} shared leg hock",
    )
    if (
        shared_hock["index"] != EXPECTED_LEG_HOCK_ROUTE_INDEX
        or shared_hock["name"] != "hock-endpoint"
        or shared_hock["source_index"] != EXPECTED_LEG_AUTHORED_SOURCE_INDICES[-1]
        or shared_hock["derived"] is not False
    ):
        _fail(f"renderer candidate route {route_name} shared leg hock identity is invalid")
    owner = _source_identity([side], "shin")
    borrowed_identity = {
        "route": leg_route,
        "name": shared_hock["name"],
        "source_index": shared_hock["source_index"],
        "owner": owner,
        "source_key": shared_hock["source_key"],
        "semantic_key": shared_hock["semantic_key"],
    }
    borrowed_hock = {
        **shared_hock,
        "index": 0,
        "route_index": 0,
        "binding_kind": "borrowed-shared-leg-station",
        "authored_in_foot_route": False,
        "shared_with": leg_route,
        "source_route": leg_route,
        "owner": owner,
        "leg_authored_identity": borrowed_identity,
    }
    foot_owner = _source_address([side], "foot")
    return [
        borrowed_hock,
        {
            "index": 1,
            "name": "pad",
            "source_key": f"source-route:{route_name}:pad:{foot_owner}",
            "semantic_key": f"section:{route_name}:pad:{foot_owner}",
            "source_index": 0,
            "derived": False,
        },
        {
            "index": 2,
            "name": "toe",
            "source_key": f"source-route:{route_name}:toe:{foot_owner}",
            "semantic_key": f"section:{route_name}:toe:{foot_owner}",
            "source_index": 1,
            "derived": False,
        },
    ]


def _expected_leg_endpoint_closures(
    route_name: str,
    sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if route_name not in {"left-leg", "right-leg"} or len(sections) != EXPECTED_LEG_TOTAL_SECTION_COUNT:
        _fail(f"renderer candidate route {route_name} has an invalid leg closure inventory")
    return [
        {
            "name": f"{route_name}:hip-cup-rim-closure",
            "source_key": sections[EXPECTED_LEG_HIP_CUP_RIM_ROUTE_INDEX]["source_key"],
        },
        {
            "name": f"{route_name}:hock-closure",
            "source_key": sections[EXPECTED_LEG_HOCK_ROUTE_INDEX]["source_key"],
        },
    ]


def _expected_shared_interface_metadata() -> dict[str, Any]:
    return {
        "cranium_mid": {"head_section_index": 3, "connection_indices": [2, 3, 4]},
        "elbows": [EXPECTED_ARM_ELBOW_ROUTE_INDEX, EXPECTED_ARM_ELBOW_ROUTE_INDEX],
        "wrist_transitions": [EXPECTED_ARM_WRIST_TRANSITION_ROUTE_INDEX, EXPECTED_ARM_WRIST_TRANSITION_ROUTE_INDEX],
        "knees": [EXPECTED_LEG_KNEE_ROUTE_INDEX, EXPECTED_LEG_KNEE_ROUTE_INDEX],
        "hocks": [EXPECTED_LEG_HOCK_ROUTE_INDEX, EXPECTED_LEG_HOCK_ROUTE_INDEX],
        "hip_cup_sections": EXPECTED_LEG_DERIVED_SECTION_NAMES,
        "feet_use_leg_hock_identity": True,
    }


class _Missing:
    pass


_MISSING = _Missing()


def _validate_mesh_settings(mesh_samples: Any, mesh_padding: Any) -> tuple[int, float]:
    if type(mesh_samples) is not int or not MIN_MESH_SAMPLES <= mesh_samples <= MAX_MESH_SAMPLES:
        _fail(
            f"mesh_samples must be an integer in "
            f"{MIN_MESH_SAMPLES}..{MAX_MESH_SAMPLES}"
        )
    if type(mesh_padding) not in {int, float}:
        _fail("mesh_padding must be a finite non-negative number")
    padding = float(mesh_padding)
    if not math.isfinite(padding) or padding < 0.0 or padding > MAX_MESH_PADDING:
        _fail("mesh_padding must be a finite non-negative bounded number")
    return mesh_samples, padding


def _read_prepared_input(
    path: Path,
    *,
    expected_source_document: str,
) -> tuple[dict[str, Any], str, str]:
    """Read and hash one validated input descriptor without reopening its path."""

    absolute = Path(path).absolute()
    try:
        reference = common._resolve_file_reference(str(absolute), absolute, "--prepared-form")
        with common.open_source_reference(reference, "--prepared-form") as stream:
            info = os.fstat(stream.fileno())
            if info.st_size > MAX_PREPARED_INPUT_BYTES:
                raise ValidationError(
                    f"--prepared-form exceeds {MAX_PREPARED_INPUT_BYTES} bytes"
                )
            raw = stream.read(MAX_PREPARED_INPUT_BYTES + 1)
            final_info = os.fstat(stream.fileno())
            if len(raw) > MAX_PREPARED_INPUT_BYTES or final_info.st_size != len(raw):
                raise ValidationError("--prepared-form changed or exceeds its bounded size")
    except (ValidationError, OSError) as exc:
        _fail(str(exc))
    raw_prepared_form_sha256 = _sha256(raw)
    try:
        prepared = json.loads(
            raw.decode("utf-8"),
            parse_constant=common._reject_constant,
            object_pairs_hook=_reject_duplicate_json_members,
        )
    except _DuplicateJSONMemberError as exc:
        _fail(f"invalid JSON in --prepared-form: {exc}")
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        _fail(f"invalid JSON in --prepared-form: {exc}")
    prepared_obj = _mapping(prepared, "prepared input")
    if prepared_obj.get("format") != common.PROVISIONAL_FORM_FORMAT:
        _fail(
            "prepared input must use the current "
            f"{common.PROVISIONAL_FORM_FORMAT} format"
        )
    source = _mapping(prepared_obj.get("source"), "prepared input.source")
    if source.get("resource_profile_id") != common.PROVISIONAL_FORM_RESOURCE_PROFILE:
        _fail(
            "prepared input.source.resource_profile_id must be "
            f"{common.PROVISIONAL_FORM_RESOURCE_PROFILE}"
        )
    if source.get("namespace") != "main":
        _fail("prepared input.source.namespace must be main")
    if source.get("document") != expected_source_document:
        _fail(
            "prepared input.source.document must be "
            f"{expected_source_document}"
        )
    try:
        validated = common._validate_provisional_form_envelope(
            prepared_obj, "prepared input"
        )
    except ValidationError as exc:
        _fail(str(exc))
    canonical_sha256 = _sha256_value(
        validated,
        "prepared validated-envelope identity",
        maximum=MAX_PREPARED_INPUT_BYTES,
    )
    return validated, canonical_sha256, raw_prepared_form_sha256


def _renderer_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "current-form-surface-preview"
        / RENDERER_ENTRYPOINT_FILENAME
    )


def _read_renderer_source_file(path: Path, where: str) -> bytes:
    absolute = path.absolute()
    try:
        reference = common._resolve_file_reference(str(absolute), absolute, where)
        with common.open_source_reference(reference, where) as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_size > MAX_RENDERER_SOURCE_BYTES
            ):
                _fail(f"{where} is not a bounded regular file")
            source_bytes = stream.read(MAX_RENDERER_SOURCE_BYTES + 1)
            after = os.fstat(stream.fileno())
            if (
                not source_bytes
                or len(source_bytes) > MAX_RENDERER_SOURCE_BYTES
                or after.st_size != len(source_bytes)
                or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            ):
                _fail(f"{where} changed, is empty, or exceeds its bound")
    except RegionalSurfacePublicationError:
        raise
    except (OSError, ValidationError) as exc:
        _fail(f"could not read {where}: {exc}")
    return source_bytes


def _snapshot_renderer_source(path: Path | None = None) -> RendererSourceSnapshot:
    """Read and retain the exact four files used by the renderer."""

    renderer_path = Path(path) if path is not None else _renderer_path()
    absolute = renderer_path.absolute()
    if absolute.name != RENDERER_ENTRYPOINT_FILENAME:
        _fail(
            "regional surface renderer source must be named "
            f"{RENDERER_ENTRYPOINT_FILENAME}"
        )
    source_bytes = _read_renderer_source_file(
        absolute,
        "regional surface renderer source",
    )
    dependencies = tuple(
        RendererDependencySourceSnapshot(
            dependency_path,
            dependency_bytes,
            _sha256(dependency_bytes),
        )
        for dependency_name in RENDERER_DEPENDENCY_FILENAMES
        for dependency_path in [absolute.with_name(dependency_name)]
        for dependency_bytes in [
            _read_renderer_source_file(
                dependency_path,
                f"regional surface renderer dependency {dependency_name}",
            )
        ]
    )
    return _validate_renderer_source_snapshot(
        RendererSourceSnapshot(
            absolute,
            source_bytes,
            _sha256(source_bytes),
            dependencies,
        )
    )


def _snapshot_publisher_source(path: Path | None = None) -> PublisherSourceSnapshot:
    """Read one immutable publisher source descriptor for bootstrap execution."""

    publisher_path = Path(path) if path is not None else Path(__file__)
    absolute = publisher_path.absolute()
    try:
        reference = common._resolve_file_reference(
            str(absolute), absolute, "regional surface publisher source"
        )
        with common.open_source_reference(reference, "regional surface publisher source") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_PUBLISHER_SOURCE_BYTES:
                _fail("regional surface publisher source is not a bounded regular file")
            source_bytes = stream.read(MAX_PUBLISHER_SOURCE_BYTES + 1)
            after = os.fstat(stream.fileno())
            if (
                len(source_bytes) > MAX_PUBLISHER_SOURCE_BYTES
                or after.st_size != len(source_bytes)
                or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            ):
                _fail("regional surface publisher source changed or exceeds its bound")
    except RegionalSurfacePublicationError:
        raise
    except (OSError, ValidationError) as exc:
        _fail(f"could not read regional surface publisher source: {exc}")
    if not source_bytes:
        _fail("regional surface publisher source is empty")
    return PublisherSourceSnapshot(absolute, source_bytes, _sha256(source_bytes))


def _publisher_source_snapshot() -> PublisherSourceSnapshot:
    """Return the retained source snapshot that defined this module's callables."""

    snapshot = globals().get("_PUBLISHER_IMPLEMENTATION_SOURCE_SNAPSHOT")
    if not isinstance(snapshot, PublisherSourceSnapshot):
        _fail("regional surface publisher source snapshot is unavailable")
    if _sha256(snapshot.source_bytes) != snapshot.sha256:
        _fail("regional surface publisher source snapshot is invalid")
    return snapshot


def _publisher_implementation_identity() -> dict[str, Any]:
    return _publisher_source_snapshot().identity


def _bootstrap_publisher_source() -> None:
    """Re-execute this module from the exact immutable bytes it will identify."""

    snapshot = _snapshot_publisher_source()
    globals()["_PUBLISHER_SNAPSHOT_EXECUTION"] = True
    globals()["_PUBLISHER_SNAPSHOT_PATH"] = snapshot.path
    globals()["_PUBLISHER_SNAPSHOT_BYTES"] = snapshot.source_bytes
    globals()["_PUBLISHER_SNAPSHOT_SHA256"] = snapshot.sha256
    code = compile(
        snapshot.source_bytes,
        str(snapshot.path),
        "exec",
        dont_inherit=True,
    )
    exec(code, globals())


def _renderer_source_identity(value: Any, where: str = "renderer source identity") -> dict[str, Any]:
    identity = _mapping(value, where)
    _exact_fields(identity, {"id", "bytes", "sha256", "dependencies"}, where)
    if identity["id"] != RENDERER_SOURCE_ID:
        _fail(f"{where}.id is not the regional surface renderer")
    if type(identity["bytes"]) is not int or not 0 < identity["bytes"] <= MAX_RENDERER_SOURCE_BYTES:
        _fail(f"{where}.bytes is invalid")
    digest = _digest(identity["sha256"], f"{where}.sha256")
    dependencies = identity["dependencies"]
    if not isinstance(dependencies, list) or len(dependencies) != len(
        RENDERER_DEPENDENCY_FILENAMES
    ):
        _fail(f"{where}.dependencies must identify the exact renderer dependencies")
    normalized_dependencies = []
    total_bytes = identity["bytes"]
    for index, (value, expected_id) in enumerate(
        zip(dependencies, RENDERER_DEPENDENCY_FILENAMES)
    ):
        dependency_where = f"{where}.dependencies[{index}]"
        dependency = _mapping(value, dependency_where)
        _exact_fields(dependency, {"id", "bytes", "sha256"}, dependency_where)
        if dependency["id"] != expected_id:
            _fail(f"{dependency_where}.id is not {expected_id}")
        if (
            type(dependency["bytes"]) is not int
            or not 0 < dependency["bytes"] <= MAX_RENDERER_SOURCE_BYTES
        ):
            _fail(f"{dependency_where}.bytes is invalid")
        total_bytes += dependency["bytes"]
        normalized_dependencies.append(
            {
                "id": expected_id,
                "bytes": dependency["bytes"],
                "sha256": _digest(
                    dependency["sha256"],
                    f"{dependency_where}.sha256",
                ),
            }
        )
    if total_bytes > MAX_RENDERER_BUNDLE_BYTES:
        _fail(f"{where} exceeds the renderer bundle byte bound")
    return {
        "id": identity["id"],
        "bytes": identity["bytes"],
        "sha256": digest,
        "dependencies": normalized_dependencies,
    }


def _validate_renderer_source_snapshot(
    snapshot: RendererSourceSnapshot,
) -> RendererSourceSnapshot:
    if snapshot.path.name != RENDERER_ENTRYPOINT_FILENAME:
        _fail("regional surface renderer source snapshot has the wrong filename")
    if type(snapshot.source_bytes) is not bytes:
        _fail("regional surface renderer source snapshot bytes are invalid")
    if not 0 < len(snapshot.source_bytes) <= MAX_RENDERER_SOURCE_BYTES:
        _fail("regional surface renderer source snapshot is empty or exceeds its bound")
    recorded_sha256 = _digest(
        snapshot.sha256,
        "regional surface renderer source snapshot.sha256",
    )
    actual_sha256 = _sha256(snapshot.source_bytes)
    if recorded_sha256 != actual_sha256:
        _fail("regional surface renderer source snapshot hash does not match its bytes")
    if snapshot.identity["bytes"] != len(snapshot.source_bytes):
        _fail("regional surface renderer source snapshot byte count does not match its bytes")
    if type(snapshot.dependencies) is not tuple or len(snapshot.dependencies) != len(
        RENDERER_DEPENDENCY_FILENAMES
    ):
        _fail("regional surface renderer source snapshot dependencies are invalid")
    total_bytes = len(snapshot.source_bytes)
    for expected_name, dependency in zip(
        RENDERER_DEPENDENCY_FILENAMES,
        snapshot.dependencies,
    ):
        if not isinstance(dependency, RendererDependencySourceSnapshot):
            _fail("regional surface renderer dependency snapshot is invalid")
        if dependency.path.name != expected_name:
            _fail("regional surface renderer dependency snapshot has the wrong filename")
        if type(dependency.source_bytes) is not bytes or not (
            0 < len(dependency.source_bytes) <= MAX_RENDERER_SOURCE_BYTES
        ):
            _fail("regional surface renderer dependency snapshot bytes are invalid")
        recorded_dependency_sha256 = _digest(
            dependency.sha256,
            f"regional surface renderer dependency {expected_name}.sha256",
        )
        if recorded_dependency_sha256 != _sha256(dependency.source_bytes):
            _fail(
                "regional surface renderer dependency snapshot hash does not match "
                "its bytes"
            )
        total_bytes += len(dependency.source_bytes)
    if total_bytes > MAX_RENDERER_BUNDLE_BYTES:
        _fail("regional surface renderer source snapshot exceeds its bundle bound")
    _renderer_source_identity(snapshot.identity)
    return snapshot


def _renderer_module_name(snapshot: RendererSourceSnapshot) -> str:
    return f"_ck_current_regional_surface_preview_{snapshot.sha256}"


def _renderer_bundle_sources(
    snapshot: RendererSourceSnapshot,
) -> tuple[tuple[str, bytes, str], ...]:
    return (
        (RENDERER_ENTRYPOINT_FILENAME, snapshot.source_bytes, snapshot.sha256),
        *tuple(
            (dependency.path.name, dependency.source_bytes, dependency.sha256)
            for dependency in snapshot.dependencies
        ),
    )


def _validate_materialized_renderer_bundle(
    snapshot: RendererSourceSnapshot,
    entrypoint: Path,
) -> Path:
    execution_path = entrypoint.absolute()
    if execution_path.name != RENDERER_ENTRYPOINT_FILENAME:
        _fail("materialized regional surface renderer has the wrong entrypoint filename")
    for filename, source_bytes, expected_sha256 in _renderer_bundle_sources(snapshot):
        materialized = _read_renderer_source_file(
            execution_path.with_name(filename),
            f"materialized regional surface renderer source {filename}",
        )
        if len(materialized) != len(source_bytes) or _sha256(materialized) != expected_sha256:
            _fail("materialized regional surface renderer bundle does not match its snapshot")
    return execution_path


@contextmanager
def _materialized_renderer_bundle(
    snapshot: RendererSourceSnapshot,
) -> Iterator[Path]:
    """Yield one private read-only directory containing the retained bundle."""

    snapshot = _validate_renderer_source_snapshot(snapshot)
    with tempfile.TemporaryDirectory(prefix="ck-regional-renderer-bundle-") as directory:
        bundle_root = Path(directory)
        try:
            for filename, source_bytes, _ in _renderer_bundle_sources(snapshot):
                destination = bundle_root / filename
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                flags |= getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(destination, flags, stat.S_IRUSR)
                try:
                    with os.fdopen(descriptor, "wb", closefd=True) as stream:
                        descriptor = -1
                        stream.write(source_bytes)
                        stream.flush()
                        os.fsync(stream.fileno())
                finally:
                    if descriptor >= 0:
                        os.close(descriptor)
            entrypoint = _validate_materialized_renderer_bundle(
                snapshot,
                bundle_root / RENDERER_ENTRYPOINT_FILENAME,
            )
            os.chmod(bundle_root, stat.S_IRUSR | stat.S_IXUSR)
        except OSError as exc:
            _fail(f"could not materialize regional surface renderer bundle: {exc}")
        try:
            yield entrypoint
        finally:
            try:
                os.chmod(bundle_root, stat.S_IRWXU)
            except OSError:
                pass


@contextmanager
def _isolated_renderer_modules(snapshot: RendererSourceSnapshot) -> Iterator[None]:
    """Prevent fixed file-relative module names from crossing render calls."""

    module_names = (
        _renderer_module_name(snapshot),
        *RENDERER_IMPORTED_MODULE_NAMES,
    )
    with _RENDERER_LOAD_LOCK:
        retained = {
            name: sys.modules[name]
            for name in module_names
            if name in sys.modules
        }
        for name in module_names:
            sys.modules.pop(name, None)
        try:
            yield
        finally:
            for name in module_names:
                sys.modules.pop(name, None)
            sys.modules.update(retained)


def _load_renderer(
    snapshot: RendererSourceSnapshot,
    execution_path: Path,
) -> tuple[Any, type[Exception]]:
    """Compile retained bytes with imports rooted in the materialized bundle."""

    if not isinstance(snapshot, RendererSourceSnapshot):
        _fail("regional surface renderer source snapshot is invalid")
    snapshot = _validate_renderer_source_snapshot(snapshot)
    execution_path = _validate_materialized_renderer_bundle(
        snapshot,
        Path(execution_path),
    )
    module_name = _renderer_module_name(snapshot)
    try:
        spec = importlib.util.spec_from_loader(
            module_name,
            loader=None,
            origin=str(execution_path),
        )
        if spec is None:
            _fail("current regional surface renderer has no importable module")
        module = types.ModuleType(module_name)
        module.__spec__ = spec
        module.__file__ = str(execution_path)
        module.__package__ = ""
        sys.modules[module_name] = module
        code = compile(snapshot.source_bytes, str(execution_path), "exec")
        exec(code, module.__dict__)
    except RegionalSurfacePublicationError:
        raise
    except Exception:  # noqa: BLE001 - renderer loading must be one concise publication error
        sys.modules.pop(module_name, None)
        _fail("could not load regional surface renderer")
    renderer = getattr(module, "render_regional_surface_preview", None)
    if not callable(renderer):
        _fail("regional surface renderer has no callable render_regional_surface_preview")
    validation_error_type = getattr(module, "RegionalSurfacePreviewError", None)
    if (
        not isinstance(validation_error_type, type)
        or not issubclass(validation_error_type, Exception)
        or getattr(module, "PreviewError", None) is not validation_error_type
    ):
        _fail("regional surface renderer has no exact controlled validation exception")
    return renderer, validation_error_type


def _refuse_existing_destination(reviews_root: Path, review_id: str) -> None:
    """Reject an occupied session before invoking the potentially heavy renderer."""

    try:
        root = common.ensure_root(Path(reviews_root))
        common.require_secure_fs_support()
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except (ValidationError, OSError) as exc:
        _fail(str(exc))
    try:
        try:
            info = os.stat(review_id, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        except OSError as exc:
            _fail(f"could not inspect review destination: {exc}")
        if stat.S_ISLNK(info.st_mode):
            _fail(f"refusing existing destination symlink: {review_id}")
        _fail(f"refusing to overwrite existing destination: {review_id}")
    finally:
        try:
            os.close(root_fd)
        except OSError:
            pass


def _result_parts(result: Any) -> tuple[bytes, dict[str, Any]]:
    if isinstance(result, Mapping):
        png_bytes = result.get("png_bytes", _MISSING)
        metadata = result.get("metadata", _MISSING)
    else:
        png_bytes = getattr(result, "png_bytes", _MISSING)
        metadata = getattr(result, "metadata", _MISSING)
    if type(png_bytes) is not bytes:
        _fail("renderer result.png_bytes must be bytes")
    if len(png_bytes) == 0 or len(png_bytes) > MAX_PNG_BYTES:
        _fail("renderer result.png_bytes is empty or exceeds its bound")
    if metadata is _MISSING:
        _fail("renderer result is missing metadata")
    metadata_obj = _mapping(metadata, "renderer result.metadata")
    copied = _json_copy(
        metadata_obj,
        "renderer result.metadata",
        maximum=MAX_RENDERER_METADATA_BYTES,
    )
    if not isinstance(copied, dict):
        _fail("renderer result.metadata must normalize to an object")
    return png_bytes, copied


def _validate_png(data: bytes) -> tuple[int, int, str]:
    """Validate a bounded, decodable non-interlaced 8-bit PNG."""

    if type(data) is not bytes or len(data) > MAX_PNG_BYTES:
        _fail("renderer PNG is empty or exceeds its byte bound")
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        _fail("renderer PNG has an invalid signature")
    offset = len(signature)
    seen_ihdr = False
    seen_iend = False
    idat_chunks: list[bytes] = []
    width = height = 0
    channels = 0
    mode = ""
    while offset < len(data):
        if len(data) - offset < 12:
            _fail("renderer PNG has a truncated chunk")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        kind = data[offset : offset + 4]
        offset += 4
        if len(kind) != 4 or offset + length + 4 > len(data):
            _fail("renderer PNG has an invalid chunk length")
        payload = data[offset : offset + length]
        offset += length
        expected_crc = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4
        actual_crc = zlib.crc32(kind)
        actual_crc = zlib.crc32(payload, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            _fail("renderer PNG has a CRC mismatch")
        if (kind[0] & 0x20) == 0 and kind not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"}:
            _fail(f"renderer PNG has an unknown critical chunk {kind!r}")
        if not seen_ihdr:
            if kind != b"IHDR" or length != 13:
                _fail("renderer PNG must begin with one IHDR chunk")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if width <= 0 or height <= 0:
                _fail("renderer PNG dimensions must be positive")
            if width > MAX_PNG_WIDTH or height > MAX_PNG_HEIGHT:
                _fail(
                    "renderer PNG dimensions exceed the bounded "
                    f"{MAX_PNG_WIDTH}x{MAX_PNG_HEIGHT} limit"
                )
            if bit_depth != 8 or color_type not in {0, 2, 4, 6}:
                _fail("renderer PNG must use a supported 8-bit color format")
            if compression != 0 or filtering != 0 or interlace != 0:
                _fail("renderer PNG must use the standard non-interlaced encoding")
            channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
            mode = {0: "L", 2: "RGB", 4: "LA", 6: "RGBA"}[color_type]
            seen_ihdr = True
            continue
        if kind == b"IHDR":
            _fail("renderer PNG contains duplicate IHDR")
        if kind == b"IDAT":
            if seen_iend:
                _fail("renderer PNG contains IDAT after IEND")
            idat_chunks.append(payload)
        elif kind == b"IEND":
            if length != 0 or seen_iend:
                _fail("renderer PNG has an invalid IEND chunk")
            seen_iend = True
            if offset != len(data):
                _fail("renderer PNG has data after IEND")
        elif seen_iend:
            _fail("renderer PNG has a chunk after IEND")
    if not seen_ihdr or not seen_iend or not idat_chunks:
        _fail("renderer PNG is missing IHDR, IDAT, or IEND")
    row_bytes = 1 + width * channels
    inflated_size = height * row_bytes
    if inflated_size > MAX_PNG_INFLATED_BYTES:
        _fail(
            "renderer PNG inflated scanlines exceed the bounded "
            f"{MAX_PNG_INFLATED_BYTES} byte limit"
        )
    try:
        decompressor = zlib.decompressobj()
        inflated = decompressor.decompress(b"".join(idat_chunks), inflated_size + 1)
        if len(inflated) <= inflated_size:
            inflated += decompressor.flush(max(1, inflated_size + 1 - len(inflated)))
    except zlib.error as exc:
        _fail(f"renderer PNG IDAT data is not valid zlib: {exc}")
    if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
        _fail("renderer PNG IDAT data is incomplete or has trailing bytes")
    if len(inflated) != height * row_bytes:
        _fail("renderer PNG scanline data does not match its dimensions")
    if any(inflated[row * row_bytes] > 4 for row in range(height)):
        _fail("renderer PNG contains an unsupported scanline filter")
    return width, height, mode


def _validate_prepared_input_identity(
    metadata: dict[str, Any],
    prepared: dict[str, Any],
    canonical_input_sha256: str,
    *,
    expected_source_document: str,
) -> dict[str, Any]:
    """Validate the renderer's canonical identity for the parsed envelope.

    The renderer's ``prepared_input`` identity is deliberately distinct from
    the raw file digest.  Whitespace and key-order changes may change the raw
    source file without changing the validated envelope identity.
    """

    prepared_identity = _mapping(
        metadata.get("prepared_input", _MISSING),
        "renderer metadata.prepared_input",
    )
    prepared_source = _mapping(prepared.get("source"), "prepared input.source")
    _exact_fields(
        prepared_source,
        {"document", "namespace", "resource_profile_id"},
        "prepared input.source",
    )
    if prepared_source.get("document") != expected_source_document:
        _fail(
            "prepared input.source.document must be "
            f"{expected_source_document}"
        )

    if prepared_source.get("namespace") != "main":
        _fail("prepared input.source.namespace must be main")
    if prepared_source.get("resource_profile_id") != common.PROVISIONAL_FORM_RESOURCE_PROFILE:
        _fail("prepared input.source has the wrong resource profile")

    reference_scale = _mapping(
        prepared.get("reference_scale"), "prepared input.reference_scale"
    )
    squared_length = reference_scale.get("squared_length", _MISSING)
    if type(squared_length) is not int or squared_length <= 0:
        _fail("prepared input.reference_scale.squared_length is invalid")
    expected_reference_scale = math.sqrt(float(squared_length))

    _exact_fields(
        prepared_identity,
        {
            "format",
            "sha256",
            "hash_kind",
            "document",
            "namespace",
            "resource_profile_id",
            "reference_scale",
        },
        "renderer metadata.prepared_input",
    )
    expected_identity = {
        "format": common.PROVISIONAL_FORM_FORMAT,
        "sha256": canonical_input_sha256,
        "hash_kind": "canonical-prepared-envelope",
        "document": expected_source_document,
        "namespace": "main",
        "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
        "reference_scale": expected_reference_scale,
    }
    for key, expected in expected_identity.items():
        actual = prepared_identity.get(key, _MISSING)
        if key == "sha256":
            actual = _digest(actual, "renderer metadata.prepared_input.sha256")
        if key == "reference_scale":
            if type(actual) not in {int, float} or not math.isfinite(float(actual)):
                _fail("renderer metadata.prepared_input.reference_scale is invalid")
            actual = float(actual)
        if actual != expected:
            _fail(f"renderer metadata.prepared_input.{key} does not match the validated envelope")

    renderer_source = _mapping(metadata.get("source", _MISSING), "renderer metadata.source")
    _exact_fields(
        renderer_source,
        {
            "format",
            "sha256",
            "hash_kind",
            "document",
            "namespace",
            "resource_profile_id",
            "reference_scale",
            "variant_id",
        },
        "renderer metadata.source",
    )
    expected_source = {
        **expected_identity,
        "variant_id": SOURCE_VARIANT,
    }
    for key, expected in expected_source.items():
        actual = renderer_source.get(key, _MISSING)
        if key == "sha256":
            actual = _digest(actual, "renderer metadata.source.sha256")
        if key == "reference_scale":
            if type(actual) not in {int, float} or not math.isfinite(float(actual)):
                _fail("renderer metadata.source.reference_scale is invalid")
            actual = float(actual)
        if actual != expected:
            _fail(f"renderer metadata.source.{key} does not match the validated envelope")
    return {
        "format": common.PROVISIONAL_FORM_FORMAT,
        "sha256": canonical_input_sha256,
        "hash_kind": "canonical-prepared-envelope",
        "document": expected_source_document,
        "namespace": "main",
        "resource_profile_id": common.PROVISIONAL_FORM_RESOURCE_PROFILE,
        "variant_id": SOURCE_VARIANT,
        "reference_scale": expected_reference_scale,
    }


def _identity_values(
    metadata: dict[str, Any],
    *,
    external_profile_id: str,
) -> dict[str, Any]:
    identity = _mapping(metadata.get("identity", _MISSING), "renderer metadata.identity")
    _exact_fields(
        identity,
        {"candidate", "binding", "core", "renderer", "png_sha256"},
        "renderer metadata.identity",
    )
    candidate = _mapping(identity["candidate"], "renderer candidate identity")
    _exact_fields(
        candidate,
        {
            "format",
            "source_variant_id",
            "profile_id",
            "field_type",
            "base_type",
            "authority_control_names",
            "route_names",
            "interface_ids",
            "interface_relations",
            "skin_source_count",
            "derived_patch_count",
            "authority_control_count",
            "attachment_count",
            "interface_count",
        },
        "renderer candidate identity",
    )
    if candidate["format"] != CANDIDATE_FORMAT:
        _fail("renderer candidate identity has the wrong format")
    if candidate["source_variant_id"] != SOURCE_VARIANT or candidate["profile_id"] != SOURCE_VARIANT:
        _fail("renderer candidate identity has the wrong source variant")
    if candidate["field_type"] != EXPECTED_FINAL_FIELD_TYPE:
        _fail("renderer candidate identity.field_type is not the final field graph")
    if candidate["base_type"] != EXPECTED_BASE_TYPE:
        _fail("renderer candidate identity.base_type is not the axial chain")
    if candidate["authority_control_names"] != EXPECTED_CONTROL_NAMES:
        _fail("renderer candidate identity authority-control order is invalid")
    if candidate["route_names"] != EXPECTED_ROUTE_NAMES:
        _fail("renderer candidate identity route order is invalid")
    if candidate["interface_ids"] != EXPECTED_GRAPH_PATCH_IDS:
        _fail("renderer candidate identity interface inventory is invalid")
    if candidate["interface_relations"] != [list(item) for item in EXPECTED_INTERFACE_GRAPH_RELATIONS]:
        _fail("renderer candidate identity interface relation order is invalid")
    for key in (
        "skin_source_count",
        "derived_patch_count",
        "authority_control_count",
        "attachment_count",
        "interface_count",
    ):
        if type(candidate[key]) is not int:
            _fail("renderer candidate identity counts are invalid")
    if candidate["skin_source_count"] != len(EXPECTED_SKIN_SOURCE_IDENTITIES):
        _fail("renderer candidate identity skin-source count is invalid")
    if candidate["derived_patch_count"] != len(EXPECTED_PATCH_IDENTITIES):
        _fail("renderer candidate identity derived-patch count is invalid")
    if candidate["authority_control_count"] != len(EXPECTED_CONTROL_NAMES):
        _fail("renderer candidate identity authority-control count is invalid")
    if candidate["attachment_count"] != len(EXPECTED_ATTACHMENT_NAMES):
        _fail("renderer candidate identity attachment count is invalid")
    if candidate["interface_count"] != len(EXPECTED_INTERFACE_RELATIONS):
        _fail("renderer candidate identity counts are invalid")

    binding = _mapping(identity["binding"], "renderer binding identity")
    _exact_fields(
        binding,
        {"external_profile_id", "source_variant_id", "geometry_selection"},
        "renderer binding identity",
    )
    if binding != {
        "external_profile_id": external_profile_id,
        "source_variant_id": SOURCE_VARIANT,
        "geometry_selection": "fixed neutral-v0; external profile identity does not branch geometry",
    }:
        _fail("renderer binding identity does not match the current binding contract")

    core = _mapping(identity["core"], "renderer core identity")
    _exact_fields(
        core,
        {
            "axial_base",
            "final_field",
            "final_skin_sources",
            "derived_interface_patches",
            "authority_only_controls",
            "final_attachments",
            "final_term_count",
            "graph_semantics",
        },
        "renderer core identity",
    )
    if core["axial_base"] != "candidate.chain" or core["final_field"] != "candidate.field":
        _fail("renderer core identity does not name the current candidate graph")
    if core["graph_semantics"] != "order-independent hard envelope plus exact parent-targeted interface patches":
        _fail("renderer core identity graph semantics are invalid")
    if any(type(core[key]) is not int for key in (
        "final_skin_sources",
        "derived_interface_patches",
        "authority_only_controls",
        "final_attachments",
        "final_term_count",
    )):
        _fail("renderer core identity counts are invalid")
    if core["final_skin_sources"] != len(EXPECTED_SKIN_SOURCE_IDENTITIES):
        _fail("renderer core identity skin-source count is invalid")
    if core["derived_interface_patches"] != len(EXPECTED_PATCH_IDENTITIES):
        _fail("renderer core identity derived-patch count is invalid")
    if core["authority_only_controls"] != len(EXPECTED_CONTROL_NAMES):
        _fail("renderer core identity authority-control count is invalid")
    if core["final_attachments"] != len(EXPECTED_ATTACHMENT_NAMES):
        _fail("renderer core identity attachment count is invalid")
    if core["final_term_count"] != len(EXPECTED_SKIN_SOURCE_IDENTITIES) + len(EXPECTED_PATCH_IDENTITIES):
        _fail("renderer core identity final-term count is invalid")

    renderer = _mapping(identity["renderer"], "renderer implementation identity")
    _exact_fields(renderer, {"format", "views", "canvas"}, "renderer implementation identity")
    if renderer != {
        "format": PREVIEW_FORMAT,
        "views": EXPECTED_VIEWS,
        "canvas": [EXPECTED_CANVAS["width"], EXPECTED_CANVAS["height"]],
    }:
        _fail("renderer implementation identity does not match the current renderer contract")
    return {
        "candidate": candidate,
        "binding": binding,
        "core": core,
        "renderer": renderer,
        "png_sha256": _digest(identity["png_sha256"], "renderer identity PNG SHA-256"),
    }


def _mesh_identity(metadata: dict[str, Any], mesh_samples: int, mesh_padding: float) -> dict[str, Any]:
    mesh = _mapping(metadata.get("mesh", _MISSING), "renderer metadata.mesh")
    _exact_fields(
        mesh,
        {"samples_per_axis", "padding", "bounds", "topology_proof", "arrays"},
        "renderer metadata.mesh",
    )
    samples = mesh["samples_per_axis"]
    if type(samples) is not int or samples != mesh_samples:
        _fail("renderer mesh samples do not match the requested setting")

    padding = mesh["padding"]
    if type(padding) not in {int, float} or not math.isfinite(float(padding)) or float(padding) != mesh_padding:
        _fail("renderer mesh padding does not match the requested setting")

    bounds = _mapping(mesh["bounds"], "renderer mesh bounds")
    _exact_fields(bounds, {"min", "max"}, "renderer mesh bounds")
    lower = bounds["min"]
    upper = bounds["max"]
    if lower is _MISSING or upper is _MISSING:
        _fail("renderer mesh bounds must contain min and max")
    lower = _vector3(lower, "renderer mesh bounds.min")
    upper = _vector3(upper, "renderer mesh bounds.max")
    if any(left >= right for left, right in zip(lower, upper)):
        _fail("renderer mesh bounds must be ordered")
    topology = _mapping(mesh["topology_proof"], "renderer topology proof")
    _exact_fields(
        topology,
        {
            "connected",
            "closed_triangle_2_manifold",
            "proven",
            "watertight",
            "connected_components",
            "boundary_edge_count",
            "nonmanifold_edge_count",
            "nonmanifold_vertex_count",
        },
        "renderer topology proof",
    )
    for key in ("proven", "watertight", "connected", "closed_triangle_2_manifold"):
        if topology[key] is not True:
            _fail(f"renderer topology proof.{key} must be true")
    if type(topology["connected_components"]) is not int:
        _fail("renderer topology proof.connected_components must be an integer")
    if topology["connected_components"] != 1:
        _fail("renderer topology proof.connected_components must be 1")
    for key in ("boundary_edge_count", "nonmanifold_edge_count", "nonmanifold_vertex_count"):
        if type(topology[key]) is not int:
            _fail(f"renderer topology proof.{key} must be an integer")
        if topology[key] != 0:
            _fail(f"renderer topology proof.{key} must be 0")

    arrays = _mapping(mesh["arrays"], "renderer mesh arrays")
    _exact_fields(arrays, {"vertices", "faces", "normals"}, "renderer mesh arrays")
    normalized_arrays: dict[str, Any] = {}
    for name in ("vertices", "faces", "normals"):
        array = _mapping(arrays[name], f"renderer mesh arrays.{name}")
        _exact_fields(array, {"shape", "dtype", "sha256"}, f"renderer mesh arrays.{name}")
        shape = array["shape"]
        if (
            not isinstance(shape, list)
            or not shape
            or any(type(item) is not int or item <= 0 for item in shape)
            or len(shape) != 2
            or shape[1] != 3
        ):
            _fail(f"renderer mesh arrays.{name}.shape is invalid")
        expected_dtype = "int64" if name == "faces" else "float64"
        if array["dtype"] != expected_dtype:
            _fail(f"renderer mesh arrays.{name}.dtype must be {expected_dtype}")
        normalized_arrays[name] = {
            "shape": list(shape),
            "dtype": expected_dtype,
            "sha256": _digest(array["sha256"], f"renderer mesh arrays.{name}.sha256"),
        }
    if normalized_arrays["normals"]["shape"] != normalized_arrays["vertices"]["shape"]:
        _fail("renderer mesh normals shape does not match vertices shape")
    return {
        "samples": mesh_samples,
        "padding": mesh_padding,
        "bounds": {"min": lower, "max": upper},
        "topology": _json_copy(topology, "renderer topology proof", maximum=4096),
        "arrays": normalized_arrays,
    }


def _vector3(value: Any, where: str) -> list[float | int]:
    if not isinstance(value, list) or len(value) != 3:
        _fail(f"{where} must be a three-vector")
    result: list[float | int] = []
    for item in value:
        if type(item) not in {int, float} or not math.isfinite(float(item)):
            _fail(f"{where} must contain finite numbers")
        result.append(item)
    return result


def _vector2(value: Any, where: str) -> list[float | int]:
    if not isinstance(value, list) or len(value) != 2:
        _fail(f"{where} must be a two-vector")
    result: list[float | int] = []
    for item in value:
        if type(item) not in {int, float} or not math.isfinite(float(item)):
            _fail(f"{where} must contain finite numbers")
        result.append(item)
    return result


def _validate_candidate_binding(
    metadata: dict[str, Any],
    source: dict[str, Any],
    identities: dict[str, Any],
    external_profile_id: str,
    prepared: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], _IdentityUniverse]:
    """Validate the renderer's compact, live-derived candidate contract."""

    binding = _mapping(metadata.get("candidate_binding", _MISSING), "renderer candidate binding")
    _exact_fields(
        binding,
        {
            "module",
            "callable",
            "candidate_format",
            "external_profile_id",
            "source_variant_id",
            "geometry_selection",
        },
        "renderer candidate binding",
    )
    expected_binding = {
        "module": "regional_surface_candidate",
        "callable": "build_regional_surface_candidate",
        "candidate_format": CANDIDATE_FORMAT,
        "external_profile_id": external_profile_id,
        "source_variant_id": SOURCE_VARIANT,
        "geometry_selection": "fixed neutral-v0; external profile identity does not branch geometry",
    }
    if binding != expected_binding:
        _fail("renderer candidate binding does not match the current candidate contract")

    candidate_graph = _mapping(
        metadata.get("candidate_graph", _MISSING), "renderer candidate graph"
    )
    _exact_fields(
        candidate_graph,
        {
            "candidate_type",
            "base",
            "base_type",
            "authority_controls",
            "routes",
            "attachments",
            "interfaces",
            "interface_relations",
            "skin_source_count",
            "derived_patch_count",
            "final_field_type",
        },
        "renderer candidate graph",
    )
    if candidate_graph["candidate_type"] != EXPECTED_CANDIDATE_TYPE:
        _fail("renderer candidate graph type is invalid")
    if candidate_graph["base"] != "candidate.chain":
        _fail("renderer candidate graph base identity is invalid")
    if candidate_graph["base_type"] != EXPECTED_BASE_TYPE:
        _fail("renderer candidate graph base type is invalid")
    if candidate_graph["authority_controls"] != EXPECTED_CONTROL_NAMES:
        _fail("renderer candidate graph authority controls are invalid")
    if candidate_graph["routes"] != EXPECTED_ROUTE_NAMES:
        _fail("renderer candidate graph routes are invalid")
    if candidate_graph["attachments"] != EXPECTED_ATTACHMENT_NAMES:
        _fail("renderer candidate graph route attachments are invalid")
    if candidate_graph["interfaces"] != EXPECTED_GRAPH_PATCH_IDS:
        _fail("renderer candidate graph interfaces are invalid")
    if candidate_graph["interface_relations"] != [list(item) for item in EXPECTED_INTERFACE_GRAPH_RELATIONS]:
        _fail("renderer candidate graph interface relations are invalid")
    if candidate_graph["skin_source_count"] != len(EXPECTED_SKIN_SOURCE_IDENTITIES):
        _fail("renderer candidate graph skin-source count is invalid")
    if candidate_graph["derived_patch_count"] != len(EXPECTED_PATCH_IDENTITIES):
        _fail("renderer candidate graph derived-patch count is invalid")
    if candidate_graph["final_field_type"] != EXPECTED_FINAL_FIELD_TYPE:
        _fail("renderer candidate graph final field type is invalid")

    candidate_metadata = _mapping(
        metadata.get("candidate_metadata", _MISSING), "renderer candidate metadata"
    )
    _exact_fields(
        candidate_metadata,
        {
            "format",
            "source",
            "profile_id",
            "variant_source",
            "torso",
            "routes",
            "interfaces",
            "shoulder_controls",
            "proof",
        },
        "renderer candidate metadata",
    )
    if candidate_metadata["format"] != CANDIDATE_FORMAT or candidate_metadata["profile_id"] != SOURCE_VARIANT:
        _fail("renderer candidate metadata format or profile binding is invalid")
    candidate_source = _mapping(candidate_metadata["source"], "renderer candidate metadata.source")
    _exact_fields(candidate_source, {"document", "namespace", "resource_profile_id"}, "renderer candidate metadata.source")
    if candidate_source != {key: source[key] for key in ("document", "namespace", "resource_profile_id")}:
        _fail("renderer candidate metadata.source does not match the prepared source")

    variant_source = _mapping(candidate_metadata["variant_source"], "renderer candidate metadata.variant_source")
    _exact_fields(variant_source, {"id", "raw_record_present", "descriptor_count", "reference_scale"}, "renderer candidate metadata.variant_source")
    if variant_source["id"] != SOURCE_VARIANT or variant_source["raw_record_present"] is not True:
        _fail("renderer candidate variant binding is invalid")
    if type(variant_source["descriptor_count"]) is not int or variant_source["descriptor_count"] <= 0:
        _fail("renderer candidate descriptor count is invalid")
    if prepared is not None:
        variants = prepared.get("variants")
        selected = [item for item in variants if isinstance(item, dict) and item.get("id") == SOURCE_VARIANT] if isinstance(variants, list) else []
        if len(selected) != 1 or not isinstance(selected[0].get("descriptors"), list) or variant_source["descriptor_count"] != len(selected[0]["descriptors"]):
            _fail("renderer candidate descriptor count does not match the prepared variant")
    if type(variant_source["reference_scale"]) not in {int, float} or not math.isfinite(float(variant_source["reference_scale"])) or float(variant_source["reference_scale"]) != float(source["reference_scale"]):
        _fail("renderer candidate variant reference scale is invalid")
    if identities["binding"]["source_variant_id"] != variant_source["id"]:
        _fail("renderer binding identity and candidate metadata disagree")

    def source_address(anchors: list[str], role: str) -> str:
        return _source_address(anchors, role)

    def source_section(
        route_name: str,
        name: str,
        index: int,
        source_index: int,
        role: str,
        anchors: list[str],
    ) -> dict[str, Any]:
        address = source_address(anchors, role)
        return {
            "index": index,
            "name": name,
            "source_key": f"source-route:{route_name}:{name}:{address}",
            "semantic_key": f"section:{route_name}:{name}:{address}",
            "source_index": source_index,
            "derived": False,
        }

    def expected_sections(
        route_name: str,
        shared_hock: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        names = EXPECTED_ROUTE_SECTION_NAMES[route_name]
        if route_name == "head-neck":
            return [
                source_section(route_name, name, index, index, "neck" if index < 2 else "head", [])
                for index, name in enumerate(names)
            ]
        side = route_name.split("-", 1)[0]
        if route_name.endswith("-arm"):
            return _expected_arm_route_sections(route_name)
        if route_name.endswith("-leg"):
            return _expected_leg_route_sections(route_name)
        if shared_hock is None:
            _fail(f"renderer candidate route {route_name} has no live shared leg hock")
        return _expected_foot_route_sections(route_name, shared_hock)

    def expected_connections(route_name: str) -> list[dict[str, Any]]:
        if route_name == "head-neck":
            return [
                {
                    "name": name,
                    "from_section_index": source_index,
                    "to_section_index": target_index,
                    "route": route,
                }
                for name, source_index, target_index, route in EXPECTED_HEAD_CONNECTIONS
            ]
        names = EXPECTED_ROUTE_SECTION_NAMES[route_name]
        if route_name.endswith("-foot"):
            return [
                {
                    "name": f"{route_name}:hock-to-pad",
                    "from_section_index": 0,
                    "to_section_index": 1,
                    "route": "hock-pad-toe",
                },
                {
                    "name": f"{route_name}:pad-to-toe",
                    "from_section_index": 1,
                    "to_section_index": 2,
                    "route": "hock-pad-to-toe",
                },
            ]
        route = "upper-arm-forearm" if route_name.endswith("-arm") else "thigh-knee-shin-hock"
        return [
            {
                "name": f"{route_name}:{names[index]}-to-{names[index + 1]}",
                "from_section_index": index,
                "to_section_index": index + 1,
                "route": route,
            }
            for index in range(len(names) - 1)
        ]

    def expected_closures(route_name: str, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if route_name == "head-neck":
            return [
                {"name": name, "source_key": sections[index]["source_key"]}
                for name, index in (
                    ("neck-collar-closure", 0),
                    ("cranium-crown-closure", 4),
                    ("muzzle-tip-closure", 7),
                )
            ]
        if route_name.endswith("-arm"):
            side = route_name.split("-", 1)[0]
            return [
                {"name": f"{route_name}:shoulder-closure", "source_key": sections[EXPECTED_ARM_SHOULDER_CLOSURE_ROUTE_INDEX]["source_key"]},
                {
                    "name": f"{route_name}:wrist-closure",
                    "source_key": f"source-route:wrist:{source_address([side], 'hand')}",
                },
            ]
        if route_name.endswith("-leg"):
            return _expected_leg_endpoint_closures(route_name, sections)
        return [
            {"name": f"{route_name}:hock-closure", "source_key": sections[0]["source_key"]},
            {"name": f"{route_name}:toe-closure", "source_key": sections[-1]["source_key"]},
        ]

    torso = _mapping(candidate_metadata["torso"], "renderer candidate metadata.torso")
    _exact_fields(
        torso,
        {"stations", "regions", "station_count", "region_count", "region_intervals"},
        "renderer candidate metadata.torso",
    )
    expected_torso_stations = [
        {
            "index": index,
            "name": name,
            "semantic_key": f"station:{name}:{source_address([], 'pelvis' if index < 2 else 'torso')}",
        }
        for index, name in enumerate(EXPECTED_TORSO_STATION_NAMES)
    ]
    expected_torso_regions = [
        {
            "index": index,
            "name": name,
            "interval": interval,
            "semantic_key": f"region:{name}",
        }
        for index, (name, interval) in enumerate(
            zip(EXPECTED_REGION_NAMES, EXPECTED_TORSO_REGION_INTERVALS)
        )
    ]
    if torso != {
        "stations": expected_torso_stations,
        "regions": expected_torso_regions,
        "station_count": len(EXPECTED_TORSO_STATION_NAMES),
        "region_count": len(EXPECTED_REGION_NAMES),
        "region_intervals": EXPECTED_TORSO_REGION_INTERVALS,
    }:
        _fail("renderer candidate compact torso identity is invalid")

    route_metadata = _mapping(candidate_metadata["routes"], "renderer candidate metadata.routes")
    _exact_fields(
        route_metadata,
        EXPECTED_ROUTE_METADATA_FIELDS,
        "renderer candidate metadata.routes",
    )
    if route_metadata["count"] != len(EXPECTED_ROUTE_NAMES) or route_metadata["names"] != EXPECTED_ROUTE_NAMES:
        _fail("renderer candidate route inventory is invalid")
    if route_metadata["required_head_neck_sections"] is not True or route_metadata["required_head_neck_connections"] is not True or route_metadata["bilateral_arm_authored_sections"] != [5, 5] or route_metadata["bilateral_arm_total_sections"] != [EXPECTED_ARM_TOTAL_SECTION_COUNT, EXPECTED_ARM_TOTAL_SECTION_COUNT] or route_metadata["binding_evidence_count"] != EXPECTED_ROUTE_BINDING_EVIDENCE_COUNT or route_metadata["total_binding_evidence_count"] != EXPECTED_TOTAL_BINDING_EVIDENCE_COUNT or route_metadata["bilateral_leg_authored_sections"] != [EXPECTED_LEG_AUTHORED_SECTION_COUNT, EXPECTED_LEG_AUTHORED_SECTION_COUNT] or route_metadata["bilateral_leg_derived_sections"] != [EXPECTED_LEG_DERIVED_SECTION_NAMES, EXPECTED_LEG_DERIVED_SECTION_NAMES] or route_metadata["bilateral_leg_total_sections"] != [EXPECTED_LEG_TOTAL_SECTION_COUNT, EXPECTED_LEG_TOTAL_SECTION_COUNT] or route_metadata["bilateral_foot_authored_sections"] != [2, 2] or route_metadata["endpoint_closures_explicit"] is not True:
        _fail("renderer candidate route counts or proofs are invalid")
    shared = _mapping(route_metadata["shared_interfaces"], "renderer candidate shared_interfaces")
    _exact_fields(shared, set(_expected_shared_interface_metadata()), "renderer candidate shared_interfaces")
    if shared != _expected_shared_interface_metadata():
        _fail("renderer candidate shared interface metadata is invalid")

    kinds = {
        "head-neck": "head-neck-branch",
        "left-arm": "arm-route", "right-arm": "arm-route",
        "left-leg": "leg-route", "right-leg": "leg-route",
        "left-foot": "foot-route", "right-foot": "foot-route",
    }
    route_records = route_metadata["routes"]
    if not isinstance(route_records, list) or len(route_records) != len(EXPECTED_ROUTE_NAMES):
        _fail("renderer candidate route records are incomplete")
    compact_routes: list[dict[str, Any]] = []
    validated_route_sections: dict[str, list[dict[str, Any]]] = {}
    for route_name, value in zip(EXPECTED_ROUTE_NAMES, route_records):
        record = _mapping(value, f"renderer candidate route {route_name}")
        _exact_fields(
        record,
        {
                "name", "kind", "side", "section_count", "sections", "connection_count",
                "connections", "shared_station_indices", "hip_cup_sections", "endpoint_closures", "attachment",
            },
            f"renderer candidate route {route_name}",
        )
        names = EXPECTED_ROUTE_SECTION_NAMES[route_name]
        expected_side = None if route_name == "head-neck" else route_name.split("-", 1)[0]
        shared_hock = None
        if route_name.endswith("-foot"):
            leg_name = f"{expected_side}-leg"
            leg_sections = validated_route_sections.get(leg_name)
            if leg_sections is None:
                _fail(f"renderer candidate route {route_name} precedes its live leg route")
            shared_hock = leg_sections[-1]
        sections = expected_sections(route_name, shared_hock)
        connections = expected_connections(route_name)
        closures = expected_closures(route_name, sections)
        shared_indices = (
            [3] if route_name == "head-neck"
            else [EXPECTED_ARM_ELBOW_ROUTE_INDEX] if route_name.endswith("-arm")
            else [EXPECTED_LEG_KNEE_ROUTE_INDEX, EXPECTED_LEG_HOCK_ROUTE_INDEX] if route_name.endswith("-leg")
            else [0]
        )
        attachment = {
            "name": route_name,
            "semantic_key": f"route:{route_name}",
            "authority": None,
            "blend_radius": None,
            "skin_component": True,
        }
        expected_record = {
            "name": route_name,
            "kind": kinds[route_name],
            "side": expected_side,
            "section_count": len(sections),
            "sections": sections,
            "connection_count": len(connections),
            "connections": connections,
            "shared_station_indices": shared_indices,
            "hip_cup_sections": EXPECTED_LEG_DERIVED_SECTION_NAMES if route_name.endswith("-leg") else [],
            "endpoint_closures": closures,
            "attachment": attachment,
        }
        if record != expected_record:
            _fail(f"renderer candidate route {route_name} section inventory is invalid")
        validated_route_sections[route_name] = record["sections"]
        compact_routes.append({
            "name": route_name,
            "kind": record["kind"],
            "side": expected_side,
            "section_count": len(sections),
            "connection_count": len(connections),
            "shared_station_indices": shared_indices,
            "attachment": attachment,
        })

    interface_metadata = _mapping(candidate_metadata["interfaces"], "renderer candidate metadata.interfaces")
    _exact_fields(interface_metadata, {"count", "parent_relations", "patches", "registration_order_independent", "authority_source"}, "renderer candidate metadata.interfaces")
    if interface_metadata["count"] != len(EXPECTED_INTERFACE_RELATIONS) or interface_metadata["parent_relations"] != [list(item) for item in EXPECTED_INTERFACE_RELATIONS] or interface_metadata["registration_order_independent"] is not True or interface_metadata["authority_source"] != "interface samples plus side-matched authority-only shoulder controls":
        _fail("renderer candidate interface graph inventory is invalid")
    patch_records = interface_metadata["patches"]
    if not isinstance(patch_records, list) or len(patch_records) != len(EXPECTED_INTERFACE_RELATIONS):
        _fail("renderer candidate interface patches are incomplete")
    compact_patches: list[dict[str, Any]] = []
    for (parent, child), value in zip(EXPECTED_INTERFACE_RELATIONS, patch_records):
        identifier = f"interface:{parent}->{child}"
        record = _mapping(value, f"renderer candidate patch {identifier}")
        _exact_fields(record, {"identifier", "parent", "child", "authority", "semantic_key"}, f"renderer candidate patch {identifier}")
        if record != {
            "identifier": identifier,
            "parent": parent,
            "child": child,
            "semantic_key": identifier,
            "authority": f"authority:{parent}->{child}",
        }:
            _fail(f"renderer candidate patch {identifier} identity is invalid")
        compact_patches.append(record)

    controls = _mapping(candidate_metadata["shoulder_controls"], "renderer candidate metadata.shoulder_controls")
    _exact_fields(
        controls,
        {
            "count", "names", "semantic_binding_complete", "authority_only", "skin_consumer",
            "counterfactual_authority_bound_influence", "control_local_final_skin_influence",
            "control_local_final_skin_influence_status", "shoulder_visual_floor_satisfaction",
            "axilla_visual_floor_satisfaction", "controls",
        },
        "renderer candidate metadata.shoulder_controls",
    )
    if (
        controls["count"] != len(EXPECTED_CONTROL_NAMES)
        or controls["names"] != EXPECTED_CONTROL_NAMES
        or controls["semantic_binding_complete"] is not True
        or controls["authority_only"] is not True
        or controls["skin_consumer"] is not False
        or controls["counterfactual_authority_bound_influence"] != EXPECTED_CONTROL_AUTHORITY_INFLUENCE
        or controls["control_local_final_skin_influence"] is not EXPECTED_CONTROL_LOCAL_INFLUENCE
        or controls["control_local_final_skin_influence_status"] != EXPECTED_CONTROL_LOCAL_INFLUENCE_STATUS
        or controls["shoulder_visual_floor_satisfaction"] != EXPECTED_CONTROL_VISUAL_FLOOR_SATISFACTION
        or controls["axilla_visual_floor_satisfaction"] != EXPECTED_CONTROL_VISUAL_FLOOR_SATISFACTION
    ):
        _fail("renderer candidate shoulder controls are invalid")
    control_records = controls["controls"]
    if not isinstance(control_records, list) or len(control_records) != len(EXPECTED_CONTROL_NAMES):
        _fail("renderer candidate shoulder controls are incomplete")
    compact_controls: list[dict[str, Any]] = []
    for name, value in zip(EXPECTED_CONTROL_NAMES, control_records):
        record = _validate_candidate_control_record(
            value,
            name,
            f"renderer candidate control {name}",
        )
        compact_controls.append(record)

    proof = _mapping(candidate_metadata["proof"], "renderer candidate metadata.proof")
    proof_fields = {
        "seven_ordered_torso_stations", "three_explicit_regions", "complete_head_neck_route",
        "complete_bilateral_limb_routes", "complete_bilateral_foot_routes", "semantic_binding_complete",
        "finite_interface_authorities", "route_authorities_absent", "explicit_source_derived_endpoint_closures",
        "shared_hock_interfaces", "exact_parent_relations",
    }
    _exact_fields(proof, proof_fields, "renderer candidate metadata.proof")
    if any(proof[key] is not True for key in proof_fields):
        _fail("renderer candidate proof is incomplete")

    semantic_keys = {
        *(item["semantic_key"] for item in expected_torso_stations),
        *(item["semantic_key"] for item in expected_torso_regions),
        *(item["semantic_key"] for item in compact_patches),
        *(item["semantic_key"] for item in compact_controls),
    }
    source_keys = {item["source_key"] for item in compact_controls}
    for route_name, route_record in zip(EXPECTED_ROUTE_NAMES, route_records):
        sections = route_record["sections"]
        semantic_keys.update(item["semantic_key"] for item in sections)
        source_keys.update(item["source_key"] for item in sections)
        semantic_keys.update(item["route"] for item in route_record["connections"])
        semantic_keys.add(route_record["attachment"]["semantic_key"])
        for closure in route_record["endpoint_closures"]:
            source_keys.add(closure["source_key"])
            if route_name == "head-neck":
                prefix = f"source-route:{route_name}:"
                source_key = closure["source_key"]
                if not source_key.startswith(prefix) or ":{" not in source_key[len(prefix):]:
                    _fail(f"renderer candidate route {route_name} closure source identity is invalid")
                _, address = source_key[len(prefix):].split(":", 1)
                closure_key = f"closure:{closure['name']}:{address}"
            else:
                prefix = f"{route_name}:"
                closure_name = closure["name"]
                if not closure_name.startswith(prefix) or not closure_name.endswith("-closure"):
                    _fail(f"renderer candidate route {route_name} closure identity is invalid")
                closure_key = f"closure:{route_name}:{closure_name[len(prefix):-len('-closure')]}"
            semantic_keys.add(closure_key)

    identity_universe = _IdentityUniverse(
        semantic_keys=frozenset(semantic_keys),
        source_keys=frozenset(source_keys),
    )
    candidate_contract = {
        "format": candidate_metadata["format"],
        "profile_id": candidate_metadata["profile_id"],
        "variant_source": {
            "id": variant_source["id"],
            "raw_record_present": variant_source["raw_record_present"],
            "descriptor_count": variant_source["descriptor_count"],
            "reference_scale": variant_source["reference_scale"],
        },
        "torso": {
            "station_count": torso["station_count"],
            "region_count": torso["region_count"],
        },
        "routes": {
            "count": len(compact_routes),
            "section_counts": [item["section_count"] for item in compact_routes],
            "connection_counts": [item["connection_count"] for item in compact_routes],
            "bilateral_arm_authored_sections": list(route_metadata["bilateral_arm_authored_sections"]),
            "bilateral_arm_total_sections": list(route_metadata["bilateral_arm_total_sections"]),
            "binding_evidence_count": route_metadata["binding_evidence_count"],
            "total_binding_evidence_count": route_metadata["total_binding_evidence_count"],
            "bilateral_leg_authored_sections": list(route_metadata["bilateral_leg_authored_sections"]),
            "bilateral_leg_total_sections": list(route_metadata["bilateral_leg_total_sections"]),
            "bilateral_foot_authored_sections": list(route_metadata["bilateral_foot_authored_sections"]),
            "direct_skin_attachments": True,
        },
        "interfaces": {
            "count": len(compact_patches),
            "authorities": [item["authority"] for item in compact_patches],
        },
        "authority_controls": {
            "count": len(compact_controls),
            "authority_only": True,
            "skin_consumer": False,
            "counterfactual_authority_bound_influence": controls["counterfactual_authority_bound_influence"],
            "control_local_final_skin_influence": controls["control_local_final_skin_influence"],
            "control_local_final_skin_influence_status": controls["control_local_final_skin_influence_status"],
            "shoulder_visual_floor_satisfaction": controls["shoulder_visual_floor_satisfaction"],
            "axilla_visual_floor_satisfaction": controls["axilla_visual_floor_satisfaction"],
        },
        "live_derived_proof_count": len(proof),
    }
    return candidate_contract, identity_universe


def _validate_camera_and_layout(
    metadata: dict[str, Any], mesh: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    camera = _mapping(metadata.get("camera", _MISSING), "renderer metadata.camera")
    _exact_fields(
        camera,
        {"canvas", "views", "bounds", "projections"},
        "renderer metadata.camera",
    )
    if camera["canvas"] != EXPECTED_CANVAS or camera["views"] != EXPECTED_VIEWS:
        _fail("renderer camera canvas or views do not match the current renderer contract")
    camera_bounds = _mapping(camera["bounds"], "renderer camera bounds")
    _exact_fields(camera_bounds, {"min", "max"}, "renderer camera bounds")
    camera_lower = _vector3(camera_bounds["min"], "renderer camera bounds.min")
    camera_upper = _vector3(camera_bounds["max"], "renderer camera bounds.max")
    if _canonical_bytes(
        {"min": camera_lower, "max": camera_upper},
        "renderer camera bounds",
        maximum=8192,
    ) != _canonical_bytes(mesh["bounds"], "renderer mesh bounds", maximum=8192):
        _fail("renderer camera bounds do not match renderer mesh bounds")

    projections = camera["projections"]
    if not isinstance(projections, list) or len(projections) != len(EXPECTED_VIEWS):
        _fail("renderer camera projections are incomplete")
    for index, (name, projection) in enumerate(zip(EXPECTED_VIEWS, projections)):
        projection_obj = _mapping(projection, f"renderer camera.projections[{index}]")
        _exact_fields(
            projection_obj,
            {"name", "basis", "base", "centre", "scale"},
            f"renderer camera.projections[{index}]",
        )
        if projection_obj["name"] != name or projection_obj["base"] != EXPECTED_PROJECTION_BASES[name]:
            _fail(f"renderer camera projection {name} identity is invalid")
        basis = projection_obj["basis"]
        if (
            not isinstance(basis, list)
            or len(basis) != 3
            or any(not isinstance(row, list) or len(row) != 3 for row in basis)
        ):
            _fail(f"renderer camera projection {name}.basis is invalid")
        for row in basis:
            for value in row:
                if type(value) not in {int, float} or not math.isfinite(float(value)):
                    _fail(f"renderer camera projection {name}.basis is not finite")
        if basis != EXPECTED_PROJECTION_BASES_MATRICES[name]:
            _fail(f"renderer camera projection {name}.basis does not match the current renderer")
        _vector2(projection_obj["centre"], f"renderer camera projection {name}.centre")
        scale = projection_obj["scale"]
        if type(scale) not in {int, float} or not math.isfinite(float(scale)) or float(scale) <= 0.0:
            _fail(f"renderer camera projection {name}.scale is invalid")

    layout = _mapping(metadata.get("layout", _MISSING), "renderer metadata.layout")
    _exact_fields(layout, {"panel_order", "panels", "pairing", "frame"}, "renderer metadata.layout")
    if layout["panel_order"] != EXPECTED_PANEL_ORDER:
        _fail("renderer layout panel order does not match the current renderer")
    if layout["pairing"] != "exact skin/actual final terms/authority-only diagnostics per projection":
        _fail("renderer layout pairing is invalid")
    if layout["frame"] != "one shared candidate mesh bounds and projection basis per view":
        _fail("renderer layout frame is invalid")
    panels = layout["panels"]
    if not isinstance(panels, list) or len(panels) != len(EXPECTED_PANEL_ORDER):
        _fail("renderer layout panels are incomplete")
    panel_width = 580
    panel_height = 460
    column_gap = 18
    row_gap = 14
    for index, (panel_id, panel) in enumerate(zip(EXPECTED_PANEL_ORDER, panels)):
        panel_obj = _mapping(panel, f"renderer layout.panels[{index}]")
        _exact_fields(
            panel_obj,
            {"id", "projection", "content", "box"},
            f"renderer layout.panels[{index}]",
        )
        if panel_obj["projection"] not in EXPECTED_VIEWS:
            _fail(f"renderer layout panel {panel_id} has an invalid projection")
        if panel_obj["content"] not in EXPECTED_PANEL_CONTENTS:
            _fail(f"renderer layout panel {panel_id} has invalid content")
        column = EXPECTED_VIEWS.index(panel_obj["projection"])
        row = EXPECTED_PANEL_CONTENTS.index(panel_obj["content"])
        expected_box = [
            12 + column * (panel_width + column_gap),
            72 + row * (panel_height + row_gap),
            12 + column * (panel_width + column_gap) + panel_width,
            72 + row * (panel_height + row_gap) + panel_height,
        ]
        if panel_obj["id"] != panel_id or panel_obj["box"] != expected_box:
            _fail(f"renderer layout panel {panel_id} is invalid")
    return camera, layout


def _expected_operand_specs() -> list[tuple[str, str, str]]:
    return [
        *EXPECTED_SKIN_SOURCE_IDENTITIES,
        *[(item[0], item[1], item[2]) for item in EXPECTED_PATCH_IDENTITIES],
    ]


def _finite_trace_number(value: Any, where: str, *, nonnegative: bool = False) -> float:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        _fail(f"{where} must be a finite number")
    result = float(value)
    if nonnegative and result < 0.0:
        _fail(f"{where} must be non-negative")
    return result


def _validate_control_ellipsoid_measurement(
    witness: dict[str, Any],
    identifier: str,
) -> float:
    """Validate locality measurements without promoting them to locality proof."""

    normalized_radius = _finite_trace_number(
        witness["control_ellipsoid_normalized_radius"],
        f"{identifier}.control_ellipsoid_normalized_radius",
        nonnegative=True,
    )
    omission_witness = witness["control_ellipsoid_near_zero_omission_witness"]
    if type(omission_witness) is not bool:
        _fail(
            f"{identifier}.control_ellipsoid_near_zero_omission_witness "
            "must be a boolean"
        )

    # The producer records the direct ellipsoid membership measurement.  Keep
    # that measurement internally coherent, while deliberately leaving its
    # locality meaning unproven when final-skin influence is unverified.
    expected_omission_witness = normalized_radius <= 1.0 + TRACE_TOLERANCE
    if omission_witness is not expected_omission_witness:
        _fail(
            f"renderer diagnostic witness {identifier} control ellipsoid "
            "measurement is inconsistent"
        )
    return normalized_radius


def _reconstruct_trace(value: Any, where: str) -> tuple[float, list[dict[str, Any]]]:
    trace = _mapping(value, where)
    _exact_fields(
        trace,
        {
            "operator", "value", "authority_id", "blend_coefficient", "sensitivity",
            "dominance", "tie_state", "semantic_keys", "parameters",
            "parent_id", "child_id", "children",
        },
        where,
    )
    operator = _text(trace["operator"], f"{where}.operator", maximum=128)
    node_value = _finite_trace_number(trace["value"], f"{where}.value")
    if trace["authority_id"] is not None:
        _text(trace["authority_id"], f"{where}.authority_id", maximum=256)
    coefficient = trace["blend_coefficient"]
    if coefficient is not None:
        coefficient = _finite_trace_number(coefficient, f"{where}.blend_coefficient")
        if not 0.0 <= coefficient <= 1.0:
            _fail(f"{where}.blend_coefficient must be within [0, 1]")
    dominance = _text(trace["dominance"], f"{where}.dominance", maximum=256)
    tie_state = _text(trace["tie_state"], f"{where}.tie_state", maximum=64)
    semantic_keys = trace["semantic_keys"]
    if (
        not isinstance(semantic_keys, list)
        or not semantic_keys
        or any(not isinstance(item, str) or not item for item in semantic_keys)
        or len(set(semantic_keys)) != len(semantic_keys)
    ):
        _fail(f"{where}.semantic_keys is not an exact identity list")
    parameters = trace["parameters"]
    if not isinstance(parameters, dict) or any(
        not isinstance(key, str) or not key
        or type(item) not in {int, float}
        or not math.isfinite(float(item))
        for key, item in parameters.items()
    ):
        _fail(f"{where}.parameters are invalid")
    for key in ("parent_id", "child_id"):
        if trace[key] is not None:
            _text(trace[key], f"{where}.{key}", maximum=256)
    children = trace["children"]
    if not isinstance(children, list):
        _fail(f"{where}.children must be an array")
    sensitivities = trace["sensitivity"]
    if not isinstance(sensitivities, list):
        _fail(f"{where}.sensitivity is invalid")
    for item in sensitivities:
        _finite_trace_number(item, f"{where}.sensitivity", nonnegative=True)
    if children and len(sensitivities) != len(children):
        _fail(f"{where}.sensitivity does not match its children")
    if not children and len(sensitivities) != 1:
        _fail(f"{where}.leaf sensitivity must contain one value")
    normalized_sensitivities = [
        _finite_trace_number(item, f"{where}.sensitivity[{index}]", nonnegative=True)
        for index, item in enumerate(sensitivities)
    ]
    child_results: list[float] = []
    nodes = [trace]
    for index, child in enumerate(children):
        reconstructed, child_nodes = _reconstruct_trace(child, f"{where}.children[{index}]")
        child_results.append(reconstructed)
        nodes.extend(child_nodes)
    leaves = {
        "leaf", "regional-axial-leaf", "regional-span-leaf", "axial-cap-leaf",
        "section-span-leaf",
        "section-closure-leaf", "section-control-leaf",
    }
    hard_min = {
        "axial-regional-hard-min", "section-sweep-hard-min",
        "full-section-hard-min", "full-section-interface-hard-min",
        "full-section-interface-composite",
    }
    if operator in leaves:
        if children:
            _fail(f"{where} leaf operator unexpectedly has children")
        if normalized_sensitivities != [1.0]:
            _fail(f"{where} leaf sensitivity must be exactly one")
        if tie_state != "none":
            _fail(f"{where} leaf tie state is invalid")
        reconstructed = node_value
    elif operator == "regional-axial-chain":
        if len(child_results) != 1:
            _fail(f"{where} axial-chain trace is incomplete")
        if normalized_sensitivities != [1.0]:
            _fail(f"{where} axial-chain sensitivity must be exactly one")
        if tie_state != children[0]["tie_state"] or dominance != children[0]["dominance"]:
            _fail(f"{where} axial-chain dominance disagrees with its child")
        reconstructed = child_results[0]
    elif operator == "parent-targeted-interface-patch":
        if len(child_results) != 2 or coefficient is None or trace["authority_id"] is None:
            _fail(f"{where} smooth/interface trace is incomplete")
        if set(parameters) != {"blend_radius", "parent_value", "child_value", "hard_value"}:
            _fail(f"{where} interface trace parameters are invalid")
        if not parameters["blend_radius"] or float(parameters["blend_radius"]) <= 0.0:
            _fail(f"{where} smooth/interface trace has no blend radius")
        first, second = child_results
        radius = float(parameters["blend_radius"])
        if (
            not math.isclose(float(parameters["parent_value"]), first, rel_tol=0.0, abs_tol=TRACE_TOLERANCE)
            or not math.isclose(float(parameters["child_value"]), second, rel_tol=0.0, abs_tol=TRACE_TOLERANCE)
            or not math.isclose(float(parameters["hard_value"]), min(first, second), rel_tol=0.0, abs_tol=TRACE_TOLERANCE)
        ):
            _fail(f"{where} interface trace parameters disagree with its children")
        delta = (second - first) / radius
        soft = min(first, second) - radius * math.log1p(math.exp(-abs(delta)))
        reconstructed = min(first, second) + coefficient * (soft - min(first, second))
        if delta >= 0.0:
            first_soft_weight = 1.0 / (1.0 + math.exp(-delta))
        else:
            exp_delta = math.exp(delta)
            first_soft_weight = exp_delta / (1.0 + exp_delta)
        second_soft_weight = 1.0 - first_soft_weight
        if first < second:
            first_hard_weight, second_hard_weight = 1.0, 0.0
        elif second < first:
            first_hard_weight, second_hard_weight = 0.0, 1.0
        else:
            first_hard_weight = second_hard_weight = 0.5
        expected_sensitivity = (
            (1.0 - coefficient) * first_hard_weight + coefficient * first_soft_weight,
            (1.0 - coefficient) * second_hard_weight + coefficient * second_soft_weight,
        )
        if len(normalized_sensitivities) != 2 or not math.isclose(
            sum(normalized_sensitivities), 1.0, rel_tol=0.0, abs_tol=TRACE_TOLERANCE
        ) or any(
            not math.isclose(actual, expected, rel_tol=0.0, abs_tol=TRACE_TOLERANCE)
            for actual, expected in zip(normalized_sensitivities, expected_sensitivity)
        ):
            _fail(f"{where} interface sensitivity disagrees with its blend operator")
        expected_tie_state = "tie" if first == second else "ordered"
        expected_dominance = (
            "tie"
            if first == second
            else trace["parent_id"] if first < second else trace["child_id"]
        )
        if tie_state != expected_tie_state or dominance != expected_dominance:
            _fail(f"{where} interface dominance disagrees with its operands")
    elif operator in hard_min:
        if not child_results:
            _fail(f"{where} hard-min trace is empty")
        reconstructed = min(child_results)
        active = [index for index, item in enumerate(child_results) if item == reconstructed]
        expected_sensitivity = [
            1.0 / len(active) if index in active else 0.0
            for index in range(len(child_results))
        ]
        if not math.isclose(
            sum(normalized_sensitivities), 1.0, rel_tol=0.0, abs_tol=TRACE_TOLERANCE
        ) or any(
            not math.isclose(actual, expected, rel_tol=0.0, abs_tol=TRACE_TOLERANCE)
            for actual, expected in zip(normalized_sensitivities, expected_sensitivity)
        ):
            _fail(f"{where} hard-min sensitivity disagrees with its active operands")
        sensitivity_active = {
            index
            for index, sensitivity in enumerate(normalized_sensitivities)
            if sensitivity > TRACE_TOLERANCE
        }
        if sensitivity_active != set(active):
            _fail(f"{where} hard-min active operands disagree with its sensitivity")
        expected_tie_state = "tie" if len(active) > 1 else "ordered"
        expected_dominance = (
            "tie" if len(active) > 1 else children[active[0]]["dominance"]
        )
        if tie_state != expected_tie_state or dominance != expected_dominance:
            _fail(f"{where} hard-min dominance disagrees with its active operands")
    else:
        _fail(f"{where} has an unknown operation-trace operator")

    child_semantic_keys = list(dict.fromkeys(
        key
        for child in children
        for key in child["semantic_keys"]
    ))
    if operator in leaves:
        expected_semantic_keys = semantic_keys
    elif operator == "section-sweep-hard-min":
        extras = [key for key in semantic_keys if key not in child_semantic_keys]
        if len(extras) > 1 or (
            extras and extras[0] not in {f"route:{name}" for name in EXPECTED_ROUTE_NAMES}
        ):
            _fail(f"{where} section-sweep semantic identity is invalid")
        expected_semantic_keys = [*child_semantic_keys, *extras]
    elif operator == "parent-targeted-interface-patch":
        if trace["parent_id"] is None or trace["child_id"] is None:
            _fail(f"{where} interface trace relation is incomplete")
        interface_identity = f"interface:{trace['parent_id']}->{trace['child_id']}"
        expected_semantic_keys = [*child_semantic_keys, interface_identity]
    else:
        expected_semantic_keys = child_semantic_keys
    if semantic_keys != expected_semantic_keys:
        _fail(f"{where}.semantic_keys disagree with its parsed trace children")
    if abs(reconstructed - node_value) > TRACE_TOLERANCE:
        _fail(f"{where} does not reconstruct its recorded value")
    return reconstructed, nodes


def _trace_semantic_inventory(value: Any, where: str) -> list[str]:
    identities: list[str] = []

    def visit(node_value: Any, node_where: str) -> None:
        node = _mapping(node_value, node_where)
        keys = node.get("semantic_keys")
        if not isinstance(keys, list) or any(not isinstance(item, str) or not item for item in keys):
            _fail(f"{node_where}.semantic_keys is invalid")
        for key in keys:
            if key not in identities:
                identities.append(key)
        children = node.get("children")
        if not isinstance(children, list):
            _fail(f"{node_where}.children is invalid")
        for index, child in enumerate(children):
            visit(child, f"{node_where}.children[{index}]")

    visit(value, where)
    return identities


def _source_semantic_inventory(value: Any, where: str) -> list[str]:
    identities: list[str] = []

    def visit(item: Any, item_where: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key == "source_semantic_keys":
                    if not isinstance(child, list) or any(
                        not isinstance(identity, str) or not identity for identity in child
                    ):
                        _fail(f"{item_where}.source_semantic_keys is invalid")
                    for identity in child:
                        if identity not in identities:
                            identities.append(identity)
                else:
                    visit(child, f"{item_where}.{key}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{item_where}[{index}]")

    visit(value, where)
    return identities


def _require_allowed_identities(
    identities: list[str],
    allowed: frozenset[str],
    where: str,
) -> None:
    foreign = sorted(set(identities) - allowed)
    if foreign:
        _fail(f"{where} contains identities outside the live candidate universe")


def _active_source_leaves(trace: dict[str, Any], where: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_trace = trace
    if source_trace["operator"] == "regional-axial-chain":
        children = source_trace["children"]
        if len(children) != 1:
            _fail(f"{where} axial source trace is incomplete")
        source_trace = children[0]
    if source_trace["operator"] in {"axial-regional-hard-min", "section-sweep-hard-min"}:
        leaves = [
            child
            for child, sensitivity in zip(source_trace["children"], source_trace["sensitivity"])
            if float(sensitivity) > 0.0
        ]
    else:
        leaves = [source_trace]
    if not leaves:
        _fail(f"{where} has no active source leaves")
    return source_trace, leaves


def _validate_operand_source_provenance(
    value: Any,
    trace: dict[str, Any],
    where: str,
    *,
    route_name: str | None,
) -> None:
    report = _mapping(value, where)
    fields = {
        "diagnostic_kind", "geometric_influence", "selected_leaves", "tie_state",
        "source_semantic_keys", "leaf_parameters",
    }
    if route_name is not None:
        fields.add("route")
    _exact_fields(report, fields, where)
    source_trace, leaves = _active_source_leaves(trace, f"{where}.trace")
    expected_keys = list(dict.fromkeys(
        key for leaf in leaves for key in leaf["semantic_keys"]
    ))
    expected = {
        "diagnostic_kind": "source-provenance",
        "geometric_influence": False,
        "selected_leaves": [leaf["dominance"] for leaf in leaves],
        "tie_state": source_trace["tie_state"],
        "source_semantic_keys": expected_keys,
        "leaf_parameters": [leaf["parameters"] for leaf in leaves],
    }
    if route_name is not None:
        expected["route"] = route_name
    if report != expected:
        _fail(f"{where} disagrees with its live operand trace provenance")


def _validate_final_source_provenance(report: Any, trace: dict[str, Any], where: str) -> None:
    value = _mapping(report, where)
    _exact_fields(value, {"base", "components", "interfaces"}, where)
    if trace["operator"] != "full-section-interface-composite":
        _fail(f"{where} final trace has the wrong root operator")
    final_children = trace["children"]
    if not final_children or final_children[0]["operator"] != "full-section-hard-min":
        _fail(f"{where} final trace has no exact component envelope")
    component_traces = final_children[0]["children"]
    if len(component_traces) != len(EXPECTED_SKIN_SOURCE_IDENTITIES):
        _fail(f"{where} final trace component inventory is incomplete")
    route_traces: dict[str, dict[str, Any]] = {}
    for component_trace in component_traces[1:]:
        route_keys = [
            key for key in component_trace["semantic_keys"]
            if key in {f"route:{name}" for name in EXPECTED_ROUTE_NAMES}
        ]
        if len(route_keys) != 1:
            _fail(f"{where} final route trace identity is invalid")
        route_name = route_keys[0].split(":", 1)[1]
        if route_name in route_traces:
            _fail(f"{where} final route trace identity is duplicated")
        route_traces[route_name] = component_trace
    if set(route_traces) != set(EXPECTED_ROUTE_NAMES):
        _fail(f"{where} final route trace inventory is invalid")

    _validate_operand_source_provenance(
        value["base"], component_traces[0], f"{where}.base", route_name=None
    )
    components = _mapping(value["components"], f"{where}.components")
    if set(components) != set(EXPECTED_ROUTE_NAMES):
        _fail(f"{where}.components identity inventory is invalid")
    for route_name in EXPECTED_ROUTE_NAMES:
        _validate_operand_source_provenance(
            components[route_name],
            route_traces[route_name],
            f"{where}.components.{route_name}",
            route_name=route_name,
        )

    interfaces = _mapping(value["interfaces"], f"{where}.interfaces")
    expected_interfaces = {
        f"interface:{parent}->{child}": {
            "parent": parent,
            "child": child,
            "authority": f"authority:{parent}->{child}",
        }
        for parent, child in EXPECTED_INTERFACE_GRAPH_RELATIONS
    }
    if interfaces != expected_interfaces:
        _fail(f"{where}.interfaces provenance identity is invalid")


def _validate_control_source_provenance(
    report: Any,
    trace: dict[str, Any],
    component_name: str,
    where: str,
) -> None:
    value = _mapping(report, where)
    _exact_fields(
        value,
        {"diagnostic_kind", "geometric_influence", "selected_leaves", "source_semantic_keys"},
        where,
    )
    if trace["operator"] != "section-control-leaf":
        _fail(f"{where} has the wrong source trace operator")
    expected = {
        "diagnostic_kind": "source-provenance",
        "geometric_influence": False,
        "selected_leaves": [component_name],
        "source_semantic_keys": trace["semantic_keys"],
    }
    if value != expected:
        _fail(f"{where} disagrees with its live control trace provenance")


def _validate_operand_record(
    value: Any,
    expected: tuple[str, str, str],
    where: str,
    *,
    surface: bool,
) -> dict[str, Any]:
    fields = {"identifier", "kind", "semantic_identity", "evaluator", "bounds"}
    if surface:
        fields.add("surface")
    record = _mapping(value, where)
    _exact_fields(record, fields, where)
    if (record["identifier"], record["kind"], record["semantic_identity"]) != expected:
        _fail(f"{where} has the wrong typed identity")
    evaluator = _text(record["evaluator"], f"{where}.evaluator", maximum=512)
    if record["kind"] == "skin-source":
        evaluator_key = "skin-source:base" if record["identifier"] == "base" else "skin-source:route"
    else:
        evaluator_key = record["kind"]
    if evaluator != EXPECTED_OPERAND_EVALUATORS[evaluator_key]:
        _fail(f"{where}.evaluator is invalid")
    bounds = _mapping(record["bounds"], f"{where}.bounds")
    _exact_fields(bounds, {"min", "max"}, f"{where}.bounds")
    lower = _vector3(bounds["min"], f"{where}.bounds.min")
    upper = _vector3(bounds["max"], f"{where}.bounds.max")
    if any(float(left) >= float(right) for left, right in zip(lower, upper)):
        _fail(f"{where}.bounds are unordered")
    if surface:
        surface_value = _mapping(record["surface"], f"{where}.surface")
        _exact_fields(surface_value, {"samples_per_axis", "padding", "vertex_count", "face_count", "sample_value_range"}, f"{where}.surface")
        if type(surface_value["samples_per_axis"]) is not int or surface_value["samples_per_axis"] <= 0:
            _fail(f"{where}.surface.samples_per_axis is invalid")
        if type(surface_value["padding"]) not in {int, float} or not math.isfinite(float(surface_value["padding"])) or float(surface_value["padding"]) < 0.0:
            _fail(f"{where}.surface.padding is invalid")
        if type(surface_value["vertex_count"]) is not int or surface_value["vertex_count"] <= 0 or type(surface_value["face_count"]) is not int or surface_value["face_count"] <= 0:
            _fail(f"{where}.surface mesh counts are invalid")
        sample_range = surface_value["sample_value_range"]
        if not isinstance(sample_range, list) or len(sample_range) != 2 or any(type(item) not in {int, float} or not math.isfinite(float(item)) for item in sample_range) or sample_range[0] > sample_range[1]:
            _fail(f"{where}.surface.sample_value_range is invalid")
    return record


def _validate_authority_control_record(
    value: Any,
    expected: tuple[str, str, str],
    where: str,
) -> dict[str, Any]:
    """Validate a control descriptor without promoting it to a skin operand."""

    record = _mapping(value, where)
    name = expected[0].split(":", 1)[1]
    binding = _expected_control_binding(name)
    expected_record = {
        "identifier": expected[0],
        "kind": expected[1],
        "semantic_identity": expected[2],
        **{
            key: binding[key]
            for key in (
                "source_key", "canonical_source_key", "namespace", "side", "owner", "role",
                "frame", "interface_id", "authority_only", "skin_consumer",
                "counterfactual_authority_bound_influence", "control_local_final_skin_influence",
                "control_local_final_skin_influence_status", "visual_floor_satisfaction",
            )
        },
    }
    _exact_fields(record, set(expected_record), where)
    if record != expected_record:
        _fail(f"{where} authority-control provenance is invalid")
    return record


def _validate_influence_report(report: Any, expected_component: str | None, kind: str, where: str) -> float:
    value = _mapping(report, where)
    _exact_fields(value, {"diagnostic_kind", "geometric_influence", "source_provenance"}, where)
    influence = _mapping(value["geometric_influence"], f"{where}.geometric_influence")
    _exact_fields(influence, {"diagnostic_kind", "base", "torso", "components", "interfaces"}, f"{where}.geometric_influence")
    if influence["diagnostic_kind"] != "exact-operator-sensitivity":
        _fail(f"{where} influence diagnostic kind is invalid")
    base = _finite_trace_number(influence["base"], f"{where}.base", nonnegative=True)
    torso = _finite_trace_number(influence["torso"], f"{where}.torso", nonnegative=True)
    if base != torso:
        _fail(f"{where} base and torso influence disagree")
    components = influence["components"]
    interfaces = influence["interfaces"]
    if not isinstance(components, dict) or set(components) != set(EXPECTED_ROUTE_NAMES) or not isinstance(interfaces, dict) or set(interfaces) != set(EXPECTED_GRAPH_PATCH_IDS):
        _fail(f"{where} influence identity inventory is invalid")
    for key, item in components.items():
        _finite_trace_number(item, f"{where}.components.{key}", nonnegative=True)
    for key, item in interfaces.items():
        _finite_trace_number(item, f"{where}.interfaces.{key}", nonnegative=True)
    if kind == "base":
        return base
    if kind == "interface":
        return _finite_trace_number(interfaces.get(expected_component), f"{where}.interfaces.{expected_component}", nonnegative=True)
    if expected_component is None:
        return 0.0
    return _finite_trace_number(components.get(expected_component), f"{where}.components.{expected_component}", nonnegative=True)


def _validate_witnesses(
    witnesses: Any,
    identity_universe: _IdentityUniverse,
) -> list[dict[str, Any]]:
    if not isinstance(witnesses, list) or len(witnesses) != EXPECTED_WITNESS_COUNT:
        _fail("renderer diagnostic witness count is invalid")
    if [item.get("identifier") for item in witnesses if isinstance(item, dict)] != EXPECTED_WITNESS_IDENTITIES:
        _fail("renderer diagnostic witness identity inventory is invalid")
    common_fields = {
        "identifier", "point", "evaluated_value", "reconstructed_value", "reconstruction_error",
        "expected_semantic_identity", "expected_path", "trace_semantic_keys", "source_semantic_keys",
        "trace_identity", "active_trace_contribution", "active_trace_kinds", "expected_component_name",
        "final_term_kind", "expected_component_influence", "nonzero_geometric_influence",
        "influence_status", "contribution_report", "operation_trace",
    }
    control_fields = {
        "identifier", "expected_path", "point", "evaluated_value", "reconstructed_value",
        "reconstruction_error", "counterfactual_value", "counterfactual_delta", "near_zero",
        "expected_semantic_identity", "trace_semantic_keys", "source_trace_semantic_keys",
        "source_semantic_keys", "expected_component_name", "final_term_kind", "interface",
        "expected_component_influence", "authority_bound_influence_weight",
        "counterfactual_authority_bound_influence", "control_local_final_skin_influence",
        "control_local_final_skin_influence_status", "visual_floor_satisfaction",
        "control_ellipsoid_normalized_radius", "control_ellipsoid_near_zero_omission_witness",
        "influence_status", "full_authority_gate", "omitted_input_gate", "blend_radius",
        "maximum_displacement", "contribution_report", "source_report", "operation_trace", "source_trace",
    }
    normalized: list[dict[str, Any]] = []
    for index, value in enumerate(witnesses):
        witness = _mapping(value, f"renderer diagnostic witness[{index}]")
        identifier = EXPECTED_WITNESS_IDENTITIES[index]
        region_end = len(EXPECTED_REGION_NAMES)
        route_end = region_end + len(EXPECTED_ROUTE_NAMES)
        patch_end = route_end + len(EXPECTED_INTERFACE_RELATIONS)
        if index < region_end:
            kind, expected_identity, component = "base", f"region:{EXPECTED_REGION_NAMES[index]}", "base"
        elif index < route_end:
            route_name = EXPECTED_ROUTE_NAMES[index - region_end]
            kind, expected_identity, component = "route", f"route:{route_name}", route_name
        elif index < patch_end:
            parent, child = EXPECTED_INTERFACE_RELATIONS[index - route_end]
            kind, expected_identity, component = "interface", f"interface:{parent}->{child}", f"interface:{parent}->{child}"
        else:
            control_name = EXPECTED_CONTROL_NAMES[index - patch_end]
            kind, expected_identity, component = "control", f"control:{control_name}", control_name
        fields = control_fields if kind == "control" else common_fields | ({"interface"} if kind == "interface" else set())
        _exact_fields(witness, fields, f"renderer diagnostic witness[{index}]")
        if witness["identifier"] != identifier or witness["expected_semantic_identity"] != expected_identity or witness["expected_component_name"] != component or (kind != "control" and witness["expected_path"] != identifier):
            _fail(f"renderer diagnostic witness {identifier} identity is invalid")
        _vector3(witness["point"], f"{identifier}.point")
        evaluated = _finite_trace_number(witness["evaluated_value"], f"{identifier}.evaluated_value")
        reconstructed = _finite_trace_number(witness["reconstructed_value"], f"{identifier}.reconstructed_value")
        error = _finite_trace_number(witness["reconstruction_error"], f"{identifier}.reconstruction_error", nonnegative=True)
        if not math.isclose(error, abs(reconstructed - evaluated), rel_tol=0.0, abs_tol=1.0e-15) or error > TRACE_TOLERANCE:
            _fail(f"renderer diagnostic witness {identifier} reconstruction bound is invalid")
        trace_value, trace_nodes = _reconstruct_trace(witness["operation_trace"], f"{identifier}.operation_trace")
        if not math.isclose(trace_value, evaluated, rel_tol=0.0, abs_tol=TRACE_TOLERANCE):
            _fail(f"renderer diagnostic witness {identifier} trace reconstruction is invalid")
        for node_index, node in enumerate(trace_nodes):
            _require_allowed_identities(
                node["semantic_keys"],
                identity_universe.semantic_keys,
                f"{identifier}.operation_trace.nodes[{node_index}].semantic_keys",
            )
        trace_keys = witness["trace_semantic_keys"]
        source_keys = witness["source_semantic_keys"]
        if not isinstance(trace_keys, list) or not trace_keys or any(not isinstance(item, str) or not item for item in trace_keys) or len(set(trace_keys)) != len(trace_keys):
            _fail(f"renderer diagnostic witness {identifier} trace identity inventory is invalid")
        if not isinstance(source_keys, list) or not source_keys or any(not isinstance(item, str) or not item for item in source_keys) or len(set(source_keys)) != len(source_keys):
            _fail(f"renderer diagnostic witness {identifier} source identity inventory is invalid")
        parsed_trace_keys = _trace_semantic_inventory(
            witness["operation_trace"], f"{identifier}.operation_trace"
        )
        if trace_keys != parsed_trace_keys:
            _fail(f"renderer diagnostic witness {identifier} trace identity inventory disagrees with its parsed trace")
        _require_allowed_identities(
            parsed_trace_keys,
            identity_universe.semantic_keys,
            f"renderer diagnostic witness {identifier} trace identity inventory",
        )
        contribution_report = _mapping(
            witness["contribution_report"], f"{identifier}.contribution_report"
        )
        _validate_final_source_provenance(
            contribution_report.get("source_provenance", _MISSING),
            witness["operation_trace"],
            f"{identifier}.contribution_report.source_provenance",
        )
        if kind == "control":
            interface = _mapping(witness["interface"], f"{identifier}.interface")
            if (
                witness["control_local_final_skin_influence"] is True
                and witness["control_local_final_skin_influence_status"] == "unverified"
            ):
                _fail(
                    f"renderer diagnostic witness {identifier} control local final-skin "
                    "influence is inconsistent with its unverified status"
                )
            if (
                witness["final_term_kind"] != "authority-only-control"
                or witness["expected_path"] != f"authority:{interface.get('identifier', _MISSING)}"
                or witness["influence_status"] != "proven through matching interface authority; local control influence unverified"
                or witness["counterfactual_authority_bound_influence"] != EXPECTED_CONTROL_AUTHORITY_INFLUENCE
                or witness["control_local_final_skin_influence"] is not EXPECTED_CONTROL_LOCAL_INFLUENCE
                or witness["control_local_final_skin_influence_status"] != EXPECTED_CONTROL_LOCAL_INFLUENCE_STATUS
                or witness["visual_floor_satisfaction"] != EXPECTED_CONTROL_VISUAL_FLOOR_SATISFACTION
                or expected_identity in trace_keys
            ):
                _fail(f"renderer diagnostic witness {identifier} is not authority-bound")
            if witness["near_zero"] is not True or abs(evaluated) > TRACE_TOLERANCE:
                _fail(f"renderer diagnostic witness {identifier} is not a near-zero final witness")
            counterfactual = _finite_trace_number(
                witness["counterfactual_value"], f"{identifier}.counterfactual_value"
            )
            counterfactual_delta = _finite_trace_number(
                witness["counterfactual_delta"], f"{identifier}.counterfactual_delta", nonnegative=True
            )
            if not math.isclose(
                counterfactual_delta,
                abs(counterfactual - evaluated),
                rel_tol=0.0,
                abs_tol=TRACE_TOLERANCE,
            ) or counterfactual_delta <= INFLUENCE_TOLERANCE:
                _fail(f"renderer diagnostic witness {identifier} counterfactual delta is invalid")
            full_gate = _finite_trace_number(
                witness["full_authority_gate"], f"{identifier}.full_authority_gate", nonnegative=True
            )
            omitted_gate = _finite_trace_number(
                witness["omitted_input_gate"], f"{identifier}.omitted_input_gate", nonnegative=True
            )
            if abs(full_gate - omitted_gate) <= INFLUENCE_TOLERANCE:
                _fail(f"renderer diagnostic witness {identifier} counterfactual authority is unchanged")
            blend_radius = _finite_trace_number(
                witness["blend_radius"], f"{identifier}.blend_radius"
            )
            maximum_displacement = _finite_trace_number(
                witness["maximum_displacement"], f"{identifier}.maximum_displacement", nonnegative=True
            )
            if blend_radius <= 0.0 or not math.isclose(
                maximum_displacement,
                blend_radius * math.log(2.0),
                rel_tol=0.0,
                abs_tol=TRACE_TOLERANCE,
            ):
                _fail(f"renderer diagnostic witness {identifier} authority bound is invalid")
            expected_influence = _finite_trace_number(
                witness["expected_component_influence"],
                f"{identifier}.expected_component_influence",
                nonnegative=True,
            )
            authority_influence = _finite_trace_number(
                witness["authority_bound_influence_weight"],
                f"{identifier}.authority_bound_influence_weight",
                nonnegative=True,
            )
            normalized_control_radius = _validate_control_ellipsoid_measurement(
                witness,
                identifier,
            )
            if expected_influence <= INFLUENCE_TOLERANCE or not math.isclose(
                expected_influence, authority_influence, rel_tol=0.0, abs_tol=TRACE_TOLERANCE
            ):
                _fail(f"renderer diagnostic witness {identifier} authority influence is invalid")
            side = component.split("-", 1)[0]
            _exact_fields(
                interface,
                {"identifier", "semantic_identity", "parent", "child", "authority"},
                f"{identifier}.interface",
            )
            expected_interface = {
                "identifier": f"interface:torso->{side}-arm",
                "semantic_identity": f"interface:torso->{side}-arm",
                "parent": "torso",
                "child": f"{side}-arm",
                "authority": f"authority:torso->{side}-arm",
            }
            if interface != expected_interface:
                _fail(f"renderer diagnostic witness {identifier} interface identity is invalid")
            matching = [
                node for node in trace_nodes
                if node.get("operator") == "parent-targeted-interface-patch"
                and node.get("authority_id") == interface["authority"]
                and node.get("parent_id") == interface["parent"]
                and node.get("child_id") == interface["child"]
                and interface["semantic_identity"] in node.get("semantic_keys", [])
            ]
            if len(matching) != 1:
                _fail(f"renderer diagnostic witness {identifier} authority reachability is invalid")
            reported = _validate_influence_report(
                contribution_report,
                interface["identifier"],
                "interface",
                f"{identifier}.contribution_report",
            )
            if not math.isclose(reported, expected_influence, rel_tol=0.0, abs_tol=TRACE_TOLERANCE):
                _fail(f"renderer diagnostic witness {identifier} reported authority influence is invalid")
            source_trace_value, source_trace_nodes = _reconstruct_trace(witness["source_trace"], f"{identifier}.source_trace")
            for node_index, node in enumerate(source_trace_nodes):
                _require_allowed_identities(
                    node["semantic_keys"],
                    identity_universe.semantic_keys,
                    f"{identifier}.source_trace.nodes[{node_index}].semantic_keys",
                )
            if not math.isfinite(source_trace_value):
                _fail(f"renderer diagnostic witness {identifier} source trace value is invalid")
            source_report = _mapping(witness["source_report"], f"{identifier}.source_report")
            _validate_control_source_provenance(
                source_report,
                witness["source_trace"],
                component,
                f"{identifier}.source_report",
            )
            parsed_source_trace_keys = _trace_semantic_inventory(
                witness["source_trace"], f"{identifier}.source_trace"
            )
            if witness["source_trace_semantic_keys"] != parsed_source_trace_keys:
                _fail(f"renderer diagnostic witness {identifier} source trace identity inventory disagrees with its parsed trace")
            _require_allowed_identities(
                parsed_source_trace_keys,
                identity_universe.semantic_keys,
                f"renderer diagnostic witness {identifier} source trace identity inventory",
            )
            parsed_source_keys = _source_semantic_inventory(
                source_report, f"{identifier}.source_report"
            )
            _require_allowed_identities(
                parsed_source_keys,
                identity_universe.report_keys,
                f"renderer diagnostic witness {identifier} source report identity inventory",
            )
            if source_keys != parsed_source_keys or expected_identity not in parsed_source_keys:
                _fail(f"renderer diagnostic witness {identifier} source report identity inventory is invalid")
        else:
            parsed_source_keys = _source_semantic_inventory(
                contribution_report, f"{identifier}.contribution_report"
            )
            _require_allowed_identities(
                parsed_source_keys,
                identity_universe.report_keys,
                f"renderer diagnostic witness {identifier} source report identity inventory",
            )
            if source_keys != parsed_source_keys:
                _fail(f"renderer diagnostic witness {identifier} source identity inventory disagrees with its parsed report")
            expected_kind = "derived-interface-patch" if kind == "interface" else "skin-source"
            expected_status = "nonzero final interface influence" if kind == "interface" else "nonzero final skin-source influence"
            if witness["final_term_kind"] != expected_kind or witness["influence_status"] != expected_status or witness["nonzero_geometric_influence"] is not True or expected_identity not in trace_keys:
                _fail(f"renderer diagnostic witness {identifier} final term identity is invalid")
            active = _finite_trace_number(witness["active_trace_contribution"], f"{identifier}.active_trace_contribution", nonnegative=True)
            reported = _validate_influence_report(witness["contribution_report"], component, kind, f"{identifier}.contribution_report")
            expected_influence = _finite_trace_number(witness["expected_component_influence"], f"{identifier}.expected_component_influence", nonnegative=True)
            if expected_influence <= INFLUENCE_TOLERANCE or not math.isclose(expected_influence, active, rel_tol=0.0, abs_tol=TRACE_TOLERANCE) or not math.isclose(expected_influence, reported, rel_tol=0.0, abs_tol=TRACE_TOLERANCE):
                _fail(f"renderer diagnostic witness {identifier} final influence is invalid")
            if not isinstance(witness["active_trace_kinds"], list) or not witness["active_trace_kinds"] or any(not isinstance(item, str) or not item for item in witness["active_trace_kinds"]):
                _fail(f"renderer diagnostic witness {identifier} active trace identity is invalid")
            if kind == "interface":
                parent, child = EXPECTED_INTERFACE_RELATIONS[index - len(EXPECTED_REGION_NAMES) - len(EXPECTED_ROUTE_NAMES)]
                interface = _mapping(witness["interface"], f"{identifier}.interface")
                _exact_fields(interface, {"identifier", "semantic_identity", "parent", "child", "authority"}, f"{identifier}.interface")
                if interface != {"identifier": component, "semantic_identity": expected_identity, "parent": parent, "child": child, "authority": f"authority:{parent}->{child}"}:
                    _fail(f"renderer diagnostic witness {identifier} interface identity is invalid")
                matching = [
                    node for node in trace_nodes
                    if node.get("operator") == "parent-targeted-interface-patch"
                    and node.get("authority_id") == interface["authority"]
                    and node.get("parent_id") == parent
                    and node.get("child_id") == child
                    and expected_identity in node.get("semantic_keys", [])
                ]
                if len(matching) != 1 or witness["trace_identity"] is not None:
                    _fail(f"renderer diagnostic witness {identifier} patch reachability is invalid")
            elif witness["trace_identity"] != expected_identity:
                _fail(f"renderer diagnostic witness {identifier} trace identity is invalid")
        normalized.append(witness)
    return normalized


def _validate_diagnostic_inventory(
    metadata: dict[str, Any],
    identity_universe: _IdentityUniverse,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventory = _mapping(metadata.get("diagnostic_inventory", _MISSING), "renderer diagnostic_inventory")
    _exact_fields(inventory, {"skin_sources", "derived_patches", "authority_controls"}, "renderer diagnostic_inventory")
    diagnostics = _mapping(metadata.get("diagnostics", _MISSING), "renderer metadata.diagnostics")
    _exact_fields(
        diagnostics,
        {
            "skin_sources", "derived_patches", "authority_controls", "operands",
            "base_operand", "skin_source_count", "derived_patch_count", "authority_control_count",
            "attachment_count", "final_field_type", "final_field_graph", "source_identity",
            "witness_count", "witnesses",
        },
        "renderer metadata.diagnostics",
    )
    typed_inventory = (
        (inventory["skin_sources"], EXPECTED_SKIN_SOURCE_IDENTITIES, "skin sources"),
        (inventory["derived_patches"], [(item[0], item[1], item[2]) for item in EXPECTED_PATCH_IDENTITIES], "derived patches"),
    )
    normalized_inventory: list[dict[str, Any]] = []
    for values, specs, label in typed_inventory:
        if not isinstance(values, list) or len(values) != len(specs):
            _fail(f"renderer {label} inventory count is invalid")
        for index, (value, expected) in enumerate(zip(values, specs)):
            normalized_inventory.append(_validate_operand_record(value, expected, f"renderer {label}[{index}]", surface=False))
    control_inventory = inventory["authority_controls"]
    if not isinstance(control_inventory, list) or len(control_inventory) != len(EXPECTED_AUTHORITY_CONTROL_IDENTITIES):
        _fail("renderer authority-control inventory count is invalid")
    normalized_controls = [
        _validate_authority_control_record(value, expected, f"renderer authority_controls[{index}]")
        for index, (value, expected) in enumerate(zip(control_inventory, EXPECTED_AUTHORITY_CONTROL_IDENTITIES))
    ]
    normalized_inventory.extend(normalized_controls)
    for key, expected in (
        ("skin_source_count", len(EXPECTED_SKIN_SOURCE_IDENTITIES)),
        ("derived_patch_count", len(EXPECTED_PATCH_IDENTITIES)),
        ("authority_control_count", len(EXPECTED_AUTHORITY_CONTROL_IDENTITIES)),
        ("attachment_count", len(EXPECTED_ROUTE_NAMES)),
    ):
        if diagnostics[key] != expected:
            _fail(f"renderer diagnostics.{key} is invalid")
    if diagnostics["base_operand"] != "base" or diagnostics["final_field_type"] != EXPECTED_FINAL_FIELD_TYPE:
        _fail("renderer diagnostics final field identity is invalid")
    final_graph = _mapping(diagnostics["final_field_graph"], "renderer diagnostics.final_field_graph")
    _exact_fields(final_graph, {"base", "attachments", "interfaces", "skin_sources", "derived_patches", "authority_controls", "final_term_count"}, "renderer diagnostics.final_field_graph")
    if final_graph != {
        "base": "candidate.chain",
        "attachments": EXPECTED_ATTACHMENT_NAMES,
        "interfaces": EXPECTED_GRAPH_PATCH_IDS,
        "skin_sources": EXPECTED_FINAL_SKIN_SOURCE_PATHS,
        "derived_patches": EXPECTED_GRAPH_PATCH_IDS,
        "authority_controls": EXPECTED_CONTROL_NAMES,
        "final_term_count": len(EXPECTED_SKIN_SOURCE_IDENTITIES) + len(EXPECTED_PATCH_IDENTITIES),
    }:
        _fail("renderer diagnostics final graph inventory is invalid")
    if diagnostics["source_identity"] != "candidate base/routes and parent-targeted patches; controls influence skin only through matching authority":
        _fail("renderer diagnostics source identity is invalid")
    if diagnostics["witness_count"] != EXPECTED_WITNESS_COUNT:
        _fail("renderer diagnostics witness count is invalid")
    _validate_witnesses(diagnostics["witnesses"], identity_universe)
    all_specs = _expected_operand_specs()
    operands = diagnostics["operands"]
    if not isinstance(operands, list) or len(operands) != len(all_specs):
        _fail("renderer diagnostics operands are incomplete")
    for index, (value, expected) in enumerate(zip(operands, all_specs)):
        _validate_operand_record(value, expected, f"renderer diagnostics.operands[{index}]", surface=True)
    grouped = [*diagnostics["skin_sources"], *diagnostics["derived_patches"]]
    for index, (value, expected) in enumerate(zip(grouped, all_specs)):
        _validate_operand_record(value, expected, f"renderer diagnostics.typed[{index}]", surface=True)
        if _canonical_bytes(value, f"renderer diagnostics.typed[{index}]", maximum=MAX_RENDERER_METADATA_BYTES) != _canonical_bytes(operands[index], f"renderer diagnostics.operands[{index}]", maximum=MAX_RENDERER_METADATA_BYTES):
            _fail(f"renderer diagnostics typed inventory disagrees at index {index}")
    diagnostic_controls = diagnostics["authority_controls"]
    if not isinstance(diagnostic_controls, list) or len(diagnostic_controls) != len(EXPECTED_AUTHORITY_CONTROL_IDENTITIES):
        _fail("renderer diagnostics authority-control inventory is incomplete")
    normalized_diagnostic_controls = [
        _validate_authority_control_record(value, expected, f"renderer diagnostics.authority_controls[{index}]")
        for index, (value, expected) in enumerate(zip(diagnostic_controls, EXPECTED_AUTHORITY_CONTROL_IDENTITIES))
    ]
    if normalized_diagnostic_controls != normalized_controls:
        _fail("renderer diagnostics authority controls disagree with the diagnostic inventory")
    return normalized_inventory, diagnostics


def _validate_renderer_metadata(
    metadata: dict[str, Any],
    prepared: dict[str, Any],
    canonical_input_sha256: str,
    raw_prepared_form_sha256: str,
    mesh_samples: int,
    mesh_padding: float,
    png_sha256: str,
    png_width: int,
    png_height: int,
    png_mode: str,
    png_byte_count: int,
    *,
    external_profile_id: str,
    expected_source_document: str,
    renderer_source_identity: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _exact_fields(
        metadata,
        {
            "format",
            "status",
            "profile_id",
            "source_variant_id",
            "source",
            "prepared_input",
            "identity",
            "diagnostic_inventory",
            "candidate_binding",
            "candidate_graph",
            "candidate_metadata",
            "mesh",
            "camera",
            "layout",
            "diagnostics",
            "png",
        },
        "renderer metadata",
    )
    if metadata.get("format") != PREVIEW_FORMAT:
        _fail(f"renderer metadata.format must be {PREVIEW_FORMAT}")
    if metadata.get("status") != "success":
        _fail("renderer metadata status is not success")
    if metadata.get("profile_id") != external_profile_id or metadata.get("source_variant_id") != SOURCE_VARIANT:
        _fail(f"renderer metadata.profile_id must be {external_profile_id}")
    source = _validate_prepared_input_identity(
        metadata,
        prepared,
        canonical_input_sha256,
        expected_source_document=expected_source_document,
    )
    identities = _identity_values(metadata, external_profile_id=external_profile_id)
    candidate_contract, identity_universe = _validate_candidate_binding(
        metadata,
        source,
        identities,
        external_profile_id,
        prepared,
    )
    mesh = _mesh_identity(metadata, mesh_samples, mesh_padding)
    _validate_camera_and_layout(metadata, mesh)
    diagnostic_inventory, diagnostics = _validate_diagnostic_inventory(
        metadata, identity_universe
    )

    png = _mapping(metadata["png"], "renderer metadata.png")
    _exact_fields(
        png,
        {"format", "mode", "width", "height", "sha256", "bytes"},
        "renderer metadata.png",
    )
    if png["format"] != EXPECTED_PNG_FORMAT or png["mode"] != EXPECTED_PNG_MODE:
        _fail("renderer metadata PNG format or mode is invalid")
    if png_mode != png["mode"]:
        _fail("renderer PNG mode does not match renderer metadata")
    if (
        type(png["width"]) is not int
        or type(png["height"]) is not int
        or png["width"] != png_width
        or png["height"] != png_height
        or png_width != EXPECTED_CANVAS["width"]
        or png_height != EXPECTED_CANVAS["height"]
    ):
        _fail("renderer metadata PNG dimensions do not match the current renderer canvas")
    if type(png["bytes"]) is not int or png["bytes"] != png_byte_count:
        _fail("renderer metadata PNG byte count does not match the rendered PNG")
    if _digest(png["sha256"], "renderer metadata.png.sha256") != png_sha256:
        _fail("renderer metadata PNG SHA-256 does not match the rendered bytes")
    if identities["png_sha256"] != png_sha256:
        _fail("renderer identity PNG SHA-256 does not match the rendered bytes")

    renderer_source = _renderer_source_identity(
        renderer_source_identity,
        "executed renderer source identity",
    )

    publisher_identity = _publisher_implementation_identity()
    publication_identity = {
        "prepared_input_sha256": canonical_input_sha256,
        "raw_prepared_form_sha256": raw_prepared_form_sha256,
        "source": source,
        "candidate": _json_copy(identities["candidate"], "candidate identity", maximum=4096),
        "binding": _json_copy(identities["binding"], "binding identity", maximum=4096),
        "core": _json_copy(identities["core"], "core identity", maximum=4096),
        "renderer": _json_copy(identities["renderer"], "renderer identity", maximum=4096),
        "renderer_source": renderer_source,
        "renderer_source_sha256": renderer_source["sha256"],
        "mesh_sha256": _sha256_value(
            metadata["mesh"], "renderer mesh metadata", maximum=MAX_RENDERER_METADATA_BYTES
        ),
        "camera_sha256": _sha256_value(
            metadata["camera"], "renderer camera metadata", maximum=MAX_RENDERER_METADATA_BYTES
        ),
        "layout_sha256": _sha256_value(
            metadata["layout"], "renderer layout metadata", maximum=MAX_RENDERER_METADATA_BYTES
        ),
        "diagnostic_inventory_sha256": _sha256_value(
            metadata["diagnostic_inventory"],
            "renderer diagnostic inventory",
            maximum=MAX_RENDERER_METADATA_BYTES,
        ),
        "candidate_graph_sha256": _sha256_value(
            metadata["candidate_graph"],
            "renderer candidate graph",
            maximum=MAX_RENDERER_METADATA_BYTES,
        ),
        "candidate_metadata_sha256": _sha256_value(
            metadata["candidate_metadata"],
            "renderer candidate metadata",
            maximum=MAX_RENDERER_METADATA_BYTES,
        ),
        "diagnostics_sha256": _sha256_value(
            metadata["diagnostics"],
            "renderer diagnostics",
            maximum=MAX_RENDERER_METADATA_BYTES,
        ),
        "witnesses_sha256": _sha256_value(
            diagnostics["witnesses"],
            "renderer diagnostic witnesses",
            maximum=MAX_RENDERER_METADATA_BYTES,
        ),
        "png_sha256": png_sha256,
        "publisher": publisher_identity,
    }
    publication = {
        "format": PREVIEW_FORMAT,
        "external_id": external_profile_id,
        "source_variant": SOURCE_VARIANT,
        "renderer_metadata_sha256": _sha256_value(
            metadata, "renderer metadata", maximum=MAX_RENDERER_METADATA_BYTES
        ),
        "identity": publication_identity,
        "candidate_contract": candidate_contract,
    }
    return publication, source


def _retained_renderer_metadata(
    metadata: dict[str, Any],
    full_metadata_sha256: str,
) -> dict[str, Any]:
    """Retain validated claims and digests, never an opaque v2 metadata blob."""

    full_bytes = _canonical_bytes(
        metadata,
        "renderer metadata",
        maximum=MAX_RENDERER_METADATA_BYTES,
    )
    if _sha256(full_bytes) != _digest(full_metadata_sha256, "full renderer metadata SHA-256"):
        _fail("full renderer metadata SHA-256 does not match the retained descriptor")

    def digest_entry(value: Any, where: str) -> dict[str, Any]:
        value_bytes = _canonical_bytes(value, where, maximum=MAX_RENDERER_METADATA_BYTES)
        return {"bytes": len(value_bytes), "sha256": _sha256(value_bytes)}

    def inventory_record(value: Any, where: str) -> dict[str, Any]:
        record = _mapping(value, where)
        return {
            key: _json_copy(record[key], f"{where}.{key}", maximum=8192)
            for key in ("identifier", "kind", "semantic_identity")
        }

    typed_diagnostics = _mapping(metadata["diagnostics"], "renderer metadata.diagnostics")
    compact_diagnostics: dict[str, Any] = {
        key: _json_copy(typed_diagnostics[key], f"renderer diagnostics.{key}", maximum=MAX_RENDERER_METADATA_BYTES)
        for key in (
            "base_operand", "skin_source_count", "derived_patch_count", "authority_control_count",
            "attachment_count", "final_field_type", "final_field_graph", "source_identity", "witness_count",
        )
    }
    witnesses = typed_diagnostics["witnesses"]
    if not isinstance(witnesses, list):
        _fail("renderer diagnostics.witnesses is not a list during retention")
    compact_diagnostics["witness_identity_inventory"] = [
        _text(
            _mapping(witness, f"renderer diagnostics.witnesses[{index}]")["identifier"],
            f"renderer diagnostics.witnesses[{index}].identifier",
        )
        for index, witness in enumerate(witnesses)
    ]

    compact_inventory = {}
    inventory = _mapping(metadata["diagnostic_inventory"], "renderer diagnostic inventory")
    for group in ("skin_sources", "derived_patches", "authority_controls"):
        values = inventory[group]
        if not isinstance(values, list):
            _fail(f"renderer diagnostic inventory.{group} is not a list during retention")
        compact_inventory[group] = [
            inventory_record(value, f"renderer diagnostic inventory.{group}[{index}]")
            for index, value in enumerate(values)
        ]

    candidate_metadata_digest = digest_entry(
        metadata["candidate_metadata"], "renderer candidate metadata"
    )
    diagnostic_inventory_digest = digest_entry(
        metadata["diagnostic_inventory"], "renderer diagnostic inventory"
    )
    diagnostics_digest = digest_entry(metadata["diagnostics"], "renderer diagnostics")
    witnesses_digest = digest_entry(witnesses, "renderer diagnostic witnesses")
    layout = _mapping(metadata["layout"], "renderer layout metadata")
    layout_panels = layout["panels"]
    if not isinstance(layout_panels, list):
        _fail("renderer layout panels are not a list during retention")
    compact_layout = {
        "panel_order": _json_copy(layout["panel_order"], "renderer layout panel order", maximum=4096),
        "pairing": layout["pairing"],
        "frame": layout["frame"],
        "panel_boxes": [
            _json_copy(
                _mapping(panel, f"renderer layout.panels[{index}]")["box"],
                f"renderer layout.panels[{index}].box",
                maximum=1024,
            )
            for index, panel in enumerate(layout_panels)
        ],
    }
    retained = {
        "format": metadata["format"],
        "status": metadata["status"],
        "profile_id": metadata["profile_id"],
        "source_variant_id": metadata["source_variant_id"],
        "diagnostic_inventory": compact_inventory,
        "diagnostics": compact_diagnostics,
        "mesh": _json_copy(metadata["mesh"], "renderer mesh metadata", maximum=8192),
        "camera": _json_copy(metadata["camera"], "renderer camera metadata", maximum=8192),
        "layout": compact_layout,
        "png": _json_copy(metadata["png"], "renderer PNG metadata", maximum=4096),
        "full_metadata_sha256": full_metadata_sha256,
        "omitted_fields": {
            "candidate_metadata": candidate_metadata_digest,
            "diagnostic_inventory": diagnostic_inventory_digest,
            "diagnostics": diagnostics_digest,
            "witnesses": witnesses_digest,
        },
    }
    _json_copy(
        retained,
        "bounded renderer metadata descriptor",
        maximum=MAX_RENDERER_DESCRIPTOR_BYTES,
    )
    retained_size = len(_canonical_bytes(
        retained,
        "bounded renderer metadata descriptor",
        maximum=MAX_RENDERER_DESCRIPTOR_BYTES,
    ))
    if retained_size > MAX_RENDERER_DESCRIPTOR_BYTES:
        _fail(
            "bounded renderer metadata descriptor exceeds "
            f"{MAX_RENDERER_DESCRIPTOR_BYTES} bytes"
        )
    return retained


def _write_bytes(path: Path, data: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
    except OSError as exc:
        _fail(f"could not write temporary PNG: {exc}")


def _write_json(path: Path, value: Any) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical_json(value))
            stream.flush()
    except OSError as exc:
        _fail(f"could not write temporary manifest: {exc}")


def render_and_validate_regional_surface_item(
    prepared: dict[str, Any],
    *,
    prepared_input_sha256: str,
    raw_prepared_form_sha256: str,
    external_profile_id: str,
    expected_source_document: str,
    mesh_samples: int,
    mesh_padding: float,
    renderer_source_snapshot: RendererSourceSnapshot | Path | None = None,
) -> dict[str, Any]:
    """Render and validate one identity-scoped item without publishing it."""

    try:
        stable_external_id = validate_id(external_profile_id, "external profile id")
    except ValidationError as exc:
        raise RegionalSurfacePublicationError(str(exc)) from exc
    expected_document = _text(
        expected_source_document,
        "expected source document",
        maximum=1024,
    )
    mesh_samples, mesh_padding = _validate_mesh_settings(mesh_samples, mesh_padding)
    prepared_obj = _mapping(
        _json_copy(
            prepared,
            "prepared input",
            maximum=MAX_PREPARED_INPUT_BYTES,
        ),
        "prepared input",
    )
    try:
        validated_prepared = common._validate_provisional_form_envelope(
            prepared_obj, "prepared input"
        )
    except ValidationError as exc:
        _fail(str(exc))
    canonical_input_sha256 = _sha256_value(
        validated_prepared,
        "prepared validated-envelope identity",
        maximum=MAX_PREPARED_INPUT_BYTES,
    )
    if _digest(
        prepared_input_sha256, "prepared input SHA-256"
    ) != canonical_input_sha256:
        _fail("prepared input SHA-256 does not match the validated envelope")
    raw_input_sha256 = _digest(
        raw_prepared_form_sha256, "raw prepared-form SHA-256"
    )
    prepared_source = _mapping(
        validated_prepared.get("source"), "prepared input.source"
    )
    if prepared_source.get("document") != expected_document:
        _fail(f"prepared input.source.document must be {expected_document}")

    if renderer_source_snapshot is None:
        renderer_source_snapshot = _snapshot_renderer_source()
    elif isinstance(renderer_source_snapshot, Path):
        renderer_source_snapshot = _snapshot_renderer_source(renderer_source_snapshot)
    if not isinstance(renderer_source_snapshot, RendererSourceSnapshot):
        _fail("regional surface renderer source snapshot is invalid")
    renderer_source_identity = _renderer_source_identity(
        renderer_source_snapshot.identity,
        "executed renderer source identity",
    )
    with _materialized_renderer_bundle(renderer_source_snapshot) as execution_path:
        with _isolated_renderer_modules(renderer_source_snapshot):
            renderer, renderer_validation_error = _load_renderer(
                renderer_source_snapshot,
                execution_path,
            )
            try:
                result = renderer(
                    validated_prepared,
                    external_profile_id=stable_external_id,
                    mesh_samples=mesh_samples,
                    mesh_padding=mesh_padding,
                )
            except Exception as exc:
                if type(exc) is not renderer_validation_error:
                    raise
                detail = " ".join(str(exc).split())
                if not detail:
                    detail = "renderer rejected the requested preview"
                if len(detail) > 512:
                    detail = detail[:509] + "..."
                raise RegionalSurfacePublicationError(
                    f"renderer validation failed: {detail}"
                ) from exc
    post_render_prepared = _mapping(
        _json_copy(
            validated_prepared,
            "post-render prepared input",
            maximum=MAX_PREPARED_INPUT_BYTES,
        ),
        "post-render prepared input",
    )
    if _sha256_value(
        post_render_prepared,
        "post-render prepared validated-envelope identity",
        maximum=MAX_PREPARED_INPUT_BYTES,
    ) != canonical_input_sha256:
        _fail("prepared input changed during rendering")
    validated_prepared = post_render_prepared
    png_bytes, renderer_metadata = _result_parts(result)
    png_width, png_height, png_mode = _validate_png(png_bytes)
    png_sha256 = _sha256(png_bytes)
    publication, source = _validate_renderer_metadata(
        renderer_metadata,
        validated_prepared,
        canonical_input_sha256,
        raw_input_sha256,
        mesh_samples,
        mesh_padding,
        png_sha256,
        png_width,
        png_height,
        png_mode,
        len(png_bytes),
        external_profile_id=stable_external_id,
        expected_source_document=expected_document,
        renderer_source_identity=renderer_source_identity,
    )
    retained_renderer_metadata = _retained_renderer_metadata(
        renderer_metadata,
        publication["renderer_metadata_sha256"],
    )
    item_metadata = {
        "external_id": stable_external_id,
        "source_variant": SOURCE_VARIANT,
        "prepared_input_sha256": canonical_input_sha256,
        "raw_prepared_form_sha256": raw_input_sha256,
        "png_sha256": png_sha256,
        "renderer_metadata_sha256": publication["renderer_metadata_sha256"],
        "renderer_source": renderer_source_identity,
        "renderer_source_sha256": renderer_source_identity["sha256"],
        "identity": publication["identity"],
    }
    return {
        "png_bytes": png_bytes,
        "png_sha256": png_sha256,
        "publication": publication,
        "publication_identity": publication["identity"],
        "retained_renderer_metadata": retained_renderer_metadata,
        "item_metadata": item_metadata,
        "source": source,
        "prepared_input_sha256": canonical_input_sha256,
        "raw_prepared_form_sha256": raw_input_sha256,
        "renderer_source": renderer_source_identity,
        "renderer_source_sha256": renderer_source_identity["sha256"],
    }


def publish_regional_surface_preview(
    reviews_root: Path,
    prepared_form_path: Path,
    *,
    review_id: str,
    mesh_samples: int,
    mesh_padding: float,
) -> dict[str, Any]:
    """Render and publish one immutable standard-neutral regional preview."""

    try:
        stable_id = validate_id(review_id, "review id")
    except ValidationError as exc:
        raise RegionalSurfacePublicationError(str(exc)) from exc
    if stable_id == EXTERNAL_ID:
        _fail("review id must differ from the stable external image id")
    _refuse_existing_destination(reviews_root, stable_id)
    mesh_samples, mesh_padding = _validate_mesh_settings(mesh_samples, mesh_padding)
    prepared, canonical_input_sha256, raw_prepared_form_sha256 = _read_prepared_input(
        prepared_form_path,
        expected_source_document=EXPECTED_SOURCE_DOCUMENT,
    )
    item = render_and_validate_regional_surface_item(
        prepared,
        prepared_input_sha256=canonical_input_sha256,
        raw_prepared_form_sha256=raw_prepared_form_sha256,
        external_profile_id=EXTERNAL_ID,
        expected_source_document=EXPECTED_SOURCE_DOCUMENT,
        mesh_samples=mesh_samples,
        mesh_padding=mesh_padding,
    )
    png_bytes = item["png_bytes"]
    png_sha256 = item["png_sha256"]
    publication = item["publication"]
    source = item["source"]
    retained_renderer_metadata = item["retained_renderer_metadata"]
    item_metadata = item["item_metadata"]
    descriptor_snapshot = {
        "format": PREVIEW_FORMAT,
        "external_id": EXTERNAL_ID,
        "source_variant": SOURCE_VARIANT,
        "renderer_metadata": retained_renderer_metadata,
        "publication": publication,
    }
    try:
        descriptor_size = len(
            json.dumps(
                descriptor_snapshot,
                allow_nan=False,
                ensure_ascii=False,
            ).encode("utf-8")
        )
    except (TypeError, ValueError, RecursionError) as exc:
        _fail(f"bounded publication descriptor is not JSON-compatible: {exc}")
    if descriptor_size > MAX_RENDERER_DESCRIPTOR_BYTES:
        _fail(
            "bounded publication descriptor exceeds "
            f"{MAX_RENDERER_DESCRIPTOR_BYTES} bytes"
        )

    with tempfile.TemporaryDirectory(prefix="ck-regional-surface-review-") as temporary:
        temporary_root = Path(temporary)
        png_path = temporary_root / f"{EXTERNAL_ID}.png"
        manifest_path = temporary_root / "review-manifest.json"
        _write_bytes(png_path, png_bytes)
        # The source manifest is intentionally created only after the exact
        # PNG and all deterministic metadata have been validated.  The shared
        # publisher then copies assets before writing review.json last.
        review = {
            "schema_version": 1,
            "id": stable_id,
            "title": TITLE,
            "description": DESCRIPTION,
            "instructions": INSTRUCTIONS,
            "subject_context": {"descriptor_snapshot": descriptor_snapshot},
            "kind": "image",
            "groups": [
                {
                    "id": GROUP_ID,
                    "title": "Standard neutral reference",
                    "selection_mode": "none",
                    "items": [
                        {
                            "id": EXTERNAL_ID,
                            "title": "Standard neutral reference",
                            "source": str(png_path),
                            "description": "Exact renderer PNG for source variant neutral-v0.",
                            "metadata": item_metadata,
                        }
                    ],
                }
            ],
        }
        _write_json(manifest_path, review)
        try:
            summary = publish_session(
                reviews_root,
                manifest_path,
                expected_sources={
                    EXTERNAL_ID: {"bytes": len(png_bytes), "sha256": png_sha256}
                },
            )
        except (ValidationError, PublishError, OSError) as exc:
            raise RegionalSurfacePublicationError(
                f"could not publish regional surface preview: {exc}"
            ) from exc
    return {
        **summary,
        "kind": "regional-surface-preview",
        "external_id": EXTERNAL_ID,
        "source_variant": SOURCE_VARIANT,
        "png_sha256": png_sha256,
        "prepared_input_sha256": source["sha256"],
        "raw_prepared_form_sha256": raw_prepared_form_sha256,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="existing reviews root")
    parser.add_argument(
        "--prepared-form",
        required=True,
        dest="prepared_form_path",
        type=Path,
        help="one complete successful v11 prepared-form envelope",
    )
    parser.add_argument("--id", required=True, dest="review_id", help="unique review/session ID")
    parser.add_argument(
        "--mesh-samples",
        required=True,
        type=int,
        help=f"required integer samples per axis; accepted range {MIN_MESH_SAMPLES}..{MAX_MESH_SAMPLES}",
    )
    parser.add_argument(
        "--mesh-padding",
        required=True,
        type=float,
        help=(
            "required finite non-negative padding in "
            f"0..{int(MAX_MESH_PADDING)}; intended/recommended current value 0.20"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        summary = publish_regional_surface_preview(
            args.root,
            args.prepared_form_path,
            review_id=args.review_id,
            mesh_samples=args.mesh_samples,
            mesh_padding=args.mesh_padding,
        )
    except (RegionalSurfacePublicationError, ValidationError, PublishError, OSError) as exc:
        print(f"publish-regional-surface-preview failed: {exc}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - CLI must normalize unexpected publication failures
        # Keep arbitrary implementation and publisher exception text out of the
        # CLI contract; controlled validation diagnostics have already been
        # converted to RegionalSurfacePublicationError above.
        print(
            "publish-regional-surface-preview failed: unexpected publication failure",
            file=sys.stderr,
        )
        return 2
    print(canonical_json(summary), end="")
    return 0


if globals().get("_PUBLISHER_SNAPSHOT_EXECUTION", False):
    _PUBLISHER_IMPLEMENTATION_SOURCE_SNAPSHOT = PublisherSourceSnapshot(
        path=globals()["_PUBLISHER_SNAPSHOT_PATH"],
        source_bytes=globals()["_PUBLISHER_SNAPSHOT_BYTES"],
        sha256=globals()["_PUBLISHER_SNAPSHOT_SHA256"],
    )
    if __name__ == "__main__":
        raise SystemExit(main())
else:
    if __name__ == "__main__":
        try:
            _bootstrap_publisher_source()
        except Exception:  # noqa: BLE001 - bootstrap failures are opaque at the CLI
            print(
                "publish-regional-surface-preview failed: unexpected publication failure",
                file=sys.stderr,
            )
            raise SystemExit(2)
    else:
        _bootstrap_publisher_source()
