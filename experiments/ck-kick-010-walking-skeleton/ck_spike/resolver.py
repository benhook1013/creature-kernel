"""Stdlib-only validation and rooted-tree transform resolution.

This module is intentionally a temporary host seam.  It resolves the small
fixture vocabulary used by CK-KICK-010 and does not implement fields, meshes,
or a durable semantic identity system.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostic, Phase, Severity, ValidationResult
from .model import (
    COORDINATE_CONVENTION,
    Node,
    Primitive,
    ResolvedGraph,
    ResolvedNode,
    Transform,
    multiply_matrices,
)


MANDATORY_MODULES: tuple[str, ...] = (
    "torso",
    "pelvis",
    "head",
    "muzzle",
    "left_arm",
    "left_hand_paw",
    "right_arm",
    "right_hand_paw",
    "left_thigh",
    "left_shin",
    "left_foot_paw",
    "right_thigh",
    "right_shin",
    "right_foot_paw",
)
SUPPORTED_SPIKE_REVISION = 1
ROTATION_UNIT_TOLERANCE = 1e-7


def _diagnostic(
    code: str,
    path: str,
    message: str,
    *,
    related: tuple[str, ...] = (),
    phase: Phase = Phase.VALIDATION,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        phase=phase,
        path=path,
        related_source_labels=related,
        message=message,
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_vector(
    value: Any,
    length: int,
    path: str,
    diagnostics: list[Diagnostic],
) -> tuple[float, ...] | None:
    if not isinstance(value, list) or len(value) != length:
        diagnostics.append(
            _diagnostic(
                "INVALID_VECTOR",
                path,
                f"expected a list of {length} finite numbers",
            )
        )
        return None
    if not all(_is_number(item) and math.isfinite(float(item)) for item in value):
        diagnostics.append(
            _diagnostic("NON_FINITE_VALUE", path, "vector values must be finite")
        )
        return None
    return tuple(float(item) for item in value)


def _parse_transform(
    value: Any,
    path: str,
    diagnostics: list[Diagnostic],
) -> Transform | None:
    if not isinstance(value, dict):
        diagnostics.append(
            _diagnostic("INVALID_TRANSFORM", path, "transform must be an object")
        )
        return None
    translation = _parse_vector(
        value.get("translation"), 3, f"{path}/translation", diagnostics
    )
    rotation = _parse_vector(
        value.get("rotation"), 4, f"{path}/rotation", diagnostics
    )
    if translation is None or rotation is None:
        return None
    norm = math.sqrt(sum(component * component for component in rotation))
    if norm == 0.0:
        diagnostics.append(
            _diagnostic(
                "INVALID_ROTATION",
                f"{path}/rotation",
                "quaternion must have a non-zero norm",
            )
        )
        return None
    if abs(norm - 1.0) > ROTATION_UNIT_TOLERANCE:
        diagnostics.append(
            _diagnostic(
                "INVALID_ROTATION",
                f"{path}/rotation",
                "quaternion norm must be one within the spike-local tolerance 1e-7",
            )
        )
        return None
    normalized_rotation = tuple(component / norm for component in rotation)
    return Transform(translation, normalized_rotation)  # type: ignore[arg-type]


def _parse_primitive(
    value: Any,
    path: str,
    diagnostics: list[Diagnostic],
) -> Primitive | None:
    if not isinstance(value, dict):
        diagnostics.append(
            _diagnostic("INVALID_PRIMITIVE", path, "primitive must be an object")
        )
        return None
    kind = value.get("kind")
    if kind not in {"capsule", "ellipsoid"}:
        diagnostics.append(
            _diagnostic(
                "UNSUPPORTED_PRIMITIVE",
                f"{path}/kind",
                "supported primitive kinds are capsule and ellipsoid",
            )
        )
        return None
    if kind == "capsule":
        endpoints_value = value.get("endpoints")
        if not isinstance(endpoints_value, list) or len(endpoints_value) != 2:
            diagnostics.append(
                _diagnostic(
                    "INVALID_CAPSULE_ENDPOINTS",
                    f"{path}/endpoints",
                    "capsule endpoints must contain exactly two vectors",
                )
            )
            return None
        endpoints: list[tuple[float, float, float]] = []
        for index, endpoint in enumerate(endpoints_value):
            parsed = _parse_vector(
                endpoint, 3, f"{path}/endpoints/{index}", diagnostics
            )
            if parsed is None:
                return None
            endpoints.append(parsed)  # type: ignore[arg-type]
        radius = value.get("radius")
        if not _is_number(radius) or not math.isfinite(float(radius)):
            diagnostics.append(
                _diagnostic(
                    "NON_FINITE_VALUE",
                    f"{path}/radius",
                    "capsule radius must be finite",
                )
            )
            return None
        radius_float = float(radius)
        if radius_float <= 0.0:
            diagnostics.append(
                _diagnostic(
                    "NON_POSITIVE_RADIUS",
                    f"{path}/radius",
                    "capsule radius must be positive",
                )
            )
            return None
        return Primitive("capsule", tuple(endpoints), radius=radius_float)

    radii = _parse_vector(value.get("radii"), 3, f"{path}/radii", diagnostics)
    if radii is None:
        return None
    if any(radius <= 0.0 for radius in radii):
        diagnostics.append(
            _diagnostic(
                "NON_POSITIVE_RADIUS",
                f"{path}/radii",
                "ellipsoid radii must all be positive",
            )
        )
        return None
    return Primitive("ellipsoid", radii=tuple(radii))  # type: ignore[arg-type]


def _parse_nodes(
    raw_nodes: list[Any], diagnostics: list[Diagnostic]
) -> tuple[dict[str, Node], set[str]]:
    nodes: dict[str, Node] = {}
    labels: set[str] = set()
    for index, raw_node in enumerate(raw_nodes):
        path = f"/nodes/{index}"
        if not isinstance(raw_node, dict):
            diagnostics.append(
                _diagnostic("INVALID_NODE", path, "node must be an object")
            )
            continue
        label = raw_node.get("label")
        if not isinstance(label, str) or not label:
            diagnostics.append(
                _diagnostic("INVALID_SOURCE_LABEL", f"{path}/label", "label must be non-empty")
            )
            continue
        labels.add(label)
        if label in nodes:
            diagnostics.append(
                _diagnostic(
                    "DUPLICATE_SOURCE_LABEL",
                    f"{path}/label",
                    "source-node labels must be unique",
                    related=(label,),
                )
            )
            continue

        side = raw_node.get("side")
        if side not in {"left", "right", "center"}:
            diagnostics.append(
                _diagnostic(
                    "INVALID_SIDE_METADATA",
                    f"{path}/side",
                    "side must be left, right, or center",
                    related=(label,),
                )
            )
        elif label.startswith("left_") and side != "left":
            diagnostics.append(
                _diagnostic(
                    "INVALID_SIDE_METADATA",
                    f"{path}/side",
                    "left-labelled nodes must declare side left",
                    related=(label,),
                )
            )
        elif label.startswith("right_") and side != "right":
            diagnostics.append(
                _diagnostic(
                    "INVALID_SIDE_METADATA",
                    f"{path}/side",
                    "right-labelled nodes must declare side right",
                    related=(label,),
                )
            )

        parent = raw_node.get("parent")
        socket = raw_node.get("socket")
        if parent is not None and not isinstance(parent, str):
            diagnostics.append(
                _diagnostic("INVALID_PARENT_REFERENCE", f"{path}/parent", "parent must be a label or null")
            )
            parent = None
        if socket is not None and not isinstance(socket, str):
            diagnostics.append(
                _diagnostic("INVALID_SOCKET_REFERENCE", f"{path}/socket", "socket must be a name or null")
            )
            socket = None

        transform = _parse_transform(raw_node.get("transform"), f"{path}/transform", diagnostics)
        primitive = _parse_primitive(raw_node.get("primitive"), f"{path}/primitive", diagnostics)

        sockets_value = raw_node.get("sockets", {})
        sockets: dict[str, Transform] = {}
        if not isinstance(sockets_value, dict):
            diagnostics.append(
                _diagnostic("INVALID_SOCKETS", f"{path}/sockets", "sockets must be an object")
            )
        else:
            for socket_name in sorted(sockets_value):
                if not isinstance(socket_name, str) or not socket_name:
                    diagnostics.append(
                        _diagnostic("INVALID_SOCKET_NAME", f"{path}/sockets", "socket names must be non-empty")
                    )
                    continue
                parsed_socket = _parse_transform(
                    sockets_value[socket_name],
                    f"{path}/sockets/{socket_name}",
                    diagnostics,
                )
                if parsed_socket is not None:
                    sockets[socket_name] = parsed_socket

        optional = raw_node.get("optional", False)
        if not isinstance(optional, bool):
            diagnostics.append(
                _diagnostic("INVALID_OPTIONAL_METADATA", f"{path}/optional", "optional must be boolean")
            )
            optional = False
        if transform is None or primitive is None:
            continue
        nodes[label] = Node(
            label=label,
            side=side if isinstance(side, str) else "center",
            parent=parent,
            socket=socket,
            transform=transform,
            sockets=sockets,
            primitive=primitive,
            optional=optional,
        )
    return nodes, labels


def _validate_tree(nodes: dict[str, Node], diagnostics: list[Diagnostic]) -> str | None:
    roots = sorted(
        label
        for label, node in nodes.items()
        if node.parent is None and node.socket is None
    )
    if len(roots) != 1:
        diagnostics.append(
            _diagnostic(
                "INVALID_ROOT_COUNT",
                "/nodes",
                "the ownership tree must contain exactly one root",
                related=tuple(roots),
            )
        )
    for label in sorted(nodes):
        node = nodes[label]
        path = f"/nodes/{label}"
        if node.parent is None and node.socket is not None:
            diagnostics.append(
                _diagnostic(
                    "ROOT_SOCKET_REFERENCE",
                    f"{path}/socket",
                    "the root must not reference an attachment socket",
                    related=(label,),
                )
            )
        elif node.parent is not None and node.socket is None:
            diagnostics.append(
                _diagnostic(
                    "MISSING_PARENT_SOCKET",
                    f"{path}/socket",
                    "every non-root node must name one parent socket",
                    related=(label, node.parent),
                )
            )
        if node.parent is not None:
            if node.parent not in nodes:
                diagnostics.append(
                    _diagnostic(
                        "UNKNOWN_PARENT",
                        f"{path}/parent",
                        "parent label is not declared",
                        related=(label, node.parent),
                    )
                )
            elif node.socket is not None and node.socket not in nodes[node.parent].sockets:
                diagnostics.append(
                    _diagnostic(
                        "UNKNOWN_SOCKET",
                        f"{path}/socket",
                        "parent does not declare the named attachment socket",
                        related=(label, node.parent),
                    )
                )

    if len(roots) != 1:
        return None
    root = roots[0]
    state: dict[str, int] = {}

    def visit(label: str) -> bool:
        status = state.get(label, 0)
        if status == 1:
            diagnostics.append(
                _diagnostic(
                    "CYCLE_DETECTED",
                    f"/nodes/{label}/parent",
                    "ownership references must not contain cycles",
                    related=(label,),
                )
            )
            return False
        if status == 2:
            return True
        state[label] = 1
        parent = nodes[label].parent
        if parent is not None and parent in nodes and not visit(parent):
            return False
        state[label] = 2
        return True

    for label in sorted(nodes):
        if not visit(label):
            return None
    reachable: set[str] = set()
    frontier = [root]
    while frontier:
        current = frontier.pop()
        if current in reachable:
            continue
        reachable.add(current)
        frontier.extend(
            child
            for child in sorted(nodes)
            if nodes[child].parent == current
        )
    if reachable != set(nodes):
        unreachable = tuple(sorted(set(nodes) - reachable))
        diagnostics.append(
            _diagnostic(
                "UNREACHABLE_NODE",
                "/nodes",
                "every declared node must be reachable from the root",
                related=unreachable,
            )
        )
        return None
    return root


def resolve_document(document: Any) -> ValidationResult:
    """Validate and resolve one temporary fixture mapping."""

    if not isinstance(document, dict):
        return ValidationResult(
            diagnostics=(_diagnostic("INVALID_ENVELOPE", "/", "fixture must be an object"),)
        )
    diagnostics: list[Diagnostic] = []
    fixture_id = document.get("fixture_id")
    if not isinstance(fixture_id, str) or not fixture_id:
        diagnostics.append(
            _diagnostic("INVALID_FIXTURE_ID", "/fixture_id", "fixture_id must be non-empty")
        )
    spike_revision = document.get("spike_revision")
    if not isinstance(spike_revision, int) or isinstance(spike_revision, bool):
        diagnostics.append(
            _diagnostic("INVALID_SPIKE_REVISION", "/spike_revision", "spike_revision must be an integer")
        )
    seed = document.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        diagnostics.append(_diagnostic("INVALID_SEED", "/seed", "seed must be an integer"))
    required_value = document.get("required_modules")
    required: list[str] = []
    if not isinstance(required_value, list) or not all(
        isinstance(label, str) and bool(label) for label in required_value
    ):
        diagnostics.append(
            _diagnostic(
                "INVALID_REQUIRED_MODULES",
                "/required_modules",
                "required_modules must be a list of non-empty labels",
            )
        )
    else:
        required = list(required_value)
        if len(set(required)) != len(required):
            diagnostics.append(
                _diagnostic(
                    "DUPLICATE_REQUIRED_MODULE",
                    "/required_modules",
                    "required module labels must be unique",
                )
            )
        undeclared_required = sorted(set(MANDATORY_MODULES) - set(required))
        if undeclared_required:
            diagnostics.append(
                _diagnostic(
                    "REQUIRED_MODULE_DECLARATION_MISSING",
                    "/required_modules",
                    "the bounded fixture must declare every mandatory module",
                    related=tuple(undeclared_required),
                )
            )
    raw_nodes = document.get("nodes")
    if not isinstance(raw_nodes, list):
        diagnostics.append(_diagnostic("INVALID_NODES", "/nodes", "nodes must be a list"))
        raw_nodes = []

    # Collect labels before parent/socket validation.  This is intentional:
    # the invalid fixture has one stable primary missing-module result and does
    # not produce a cascade from children that would otherwise reference it.
    labels: set[str] = set()
    for index, raw_node in enumerate(raw_nodes):
        if isinstance(raw_node, dict) and isinstance(raw_node.get("label"), str):
            label = raw_node["label"]
            if label:
                if label in labels:
                    diagnostics.append(
                        _diagnostic(
                            "DUPLICATE_SOURCE_LABEL",
                            f"/nodes/{index}/label",
                            "source-node labels must be unique",
                            related=(label,),
                        )
                    )
                labels.add(label)
    if diagnostics:
        return ValidationResult(diagnostics=tuple(diagnostics))

    missing = sorted(set(required) - labels)
    if missing:
        label = missing[0]
        return ValidationResult(
            diagnostics=(
                _diagnostic(
                    "MISSING_REQUIRED_MODULE",
                    f"/nodes/{label}",
                    f"required module {label!r} is not declared",
                    related=(label,),
                ),
            )
        )

    if spike_revision != SUPPORTED_SPIKE_REVISION:
        return ValidationResult(
            diagnostics=(
                _diagnostic(
                    "UNSUPPORTED_SPIKE_REVISION",
                    "/spike_revision",
                    f"only spike_revision {SUPPORTED_SPIKE_REVISION} is supported",
                ),
            )
        )

    if document.get("coordinate_convention") != COORDINATE_CONVENTION:
        return ValidationResult(
            diagnostics=(
                _diagnostic(
                    "UNSUPPORTED_COORDINATE_CONVENTION",
                    "/coordinate_convention",
                    "fixture coordinate_convention must exactly match the current spike convention",
                ),
            )
        )

    nodes, _ = _parse_nodes(raw_nodes, diagnostics)
    if diagnostics:
        return ValidationResult(diagnostics=tuple(diagnostics))
    root = _validate_tree(nodes, diagnostics)
    if diagnostics or root is None:
        return ValidationResult(diagnostics=tuple(diagnostics))

    resolved: dict[str, tuple[tuple[float, ...], int]] = {}

    def world_for(label: str) -> tuple[tuple[float, ...], int]:
        if label in resolved:
            return resolved[label]
        node = nodes[label]
        local_matrix = node.transform.matrix()
        if node.parent is None:
            result = (local_matrix, 0)
        else:
            parent_matrix, parent_depth = world_for(node.parent)
            socket_matrix = nodes[node.parent].sockets[node.socket].matrix()  # type: ignore[index]
            result = (
                multiply_matrices(
                    multiply_matrices(parent_matrix, socket_matrix), local_matrix
                ),
                parent_depth + 1,
            )
        resolved[label] = result
        return result

    resolved_nodes = tuple(
        ResolvedNode(
            node=nodes[label], world_matrix=world_for(label)[0], depth=world_for(label)[1]
        )
        for label in sorted(nodes)
    )
    graph = ResolvedGraph(
        fixture_id=fixture_id,  # type: ignore[arg-type]
        spike_revision=spike_revision,  # type: ignore[arg-type]
        seed=seed,  # type: ignore[arg-type]
        coordinate_convention=COORDINATE_CONVENTION,
        nodes=resolved_nodes,
    )
    return ValidationResult(graph=graph)


def resolve_json(text: str) -> ValidationResult:
    """Decode and resolve JSON, returning a typed parse diagnostic on failure."""

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        return ValidationResult(
            diagnostics=(
                _diagnostic(
                    "INVALID_JSON",
                    "/",
                    f"invalid JSON at line {error.lineno}, column {error.colno}",
                ),
            )
        )
    return resolve_document(document)


def resolve_file(path: str | Path) -> ValidationResult:
    """Read one fixture path and resolve it without scientific dependencies."""

    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return ValidationResult(
            diagnostics=(_diagnostic("INPUT_READ_ERROR", "/", str(error)),)
        )
    return resolve_json(text)


# Short aliases make this seam convenient for a future CLI adapter while
# keeping the more explicit names useful in tests and documentation.
validate_and_resolve = resolve_document
resolve = resolve_document
