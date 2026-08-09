"""Small typed in-memory model for the CK-KICK-010 disposable host."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


COORDINATE_CONVENTION: dict[str, str] = {
    "handedness": "right-handed",
    "up": "+Y",
    "forward": "+Z creature-forward",
    "creature_right": "-X",
    "units": "metres",
    "rotation": "quaternion_xyzw",
}


def _matmul(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(
        sum(left[row * 4 + index] * right[index * 4 + column] for index in range(4))
        for row in range(4)
        for column in range(4)
    )


def matrix_rows(matrix: tuple[float, ...]) -> list[list[float]]:
    return [list(matrix[row * 4 : row * 4 + 4]) for row in range(4)]


@dataclass(frozen=True)
class Transform:
    """A rigid transform with a temporary JSON quaternion convention.

    Rotations are unit quaternions in ``[x, y, z, w]`` order.  Matrices are
    row-major representations of the usual column-vector transform.
    """

    translation: tuple[float, float, float]
    rotation: tuple[float, float, float, float]

    def matrix(self) -> tuple[float, ...]:
        x, y, z, w = self.rotation
        xx, yy, zz = x * x, y * y, z * z
        xy, xz, yz = x * y, x * z, y * z
        wx, wy, wz = w * x, w * y, w * z
        tx, ty, tz = self.translation
        return (
            1.0 - 2.0 * (yy + zz),
            2.0 * (xy - wz),
            2.0 * (xz + wy),
            tx,
            2.0 * (xy + wz),
            1.0 - 2.0 * (xx + zz),
            2.0 * (yz - wx),
            ty,
            2.0 * (xz - wy),
            2.0 * (yz + wx),
            1.0 - 2.0 * (xx + yy),
            tz,
            0.0,
            0.0,
            0.0,
            1.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "translation": list(self.translation),
            "rotation": list(self.rotation),
            "matrix": matrix_rows(self.matrix()),
        }


@dataclass(frozen=True)
class Primitive:
    kind: str
    endpoints: tuple[tuple[float, float, float], ...] = ()
    radius: float | None = None
    radii: tuple[float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.kind == "capsule":
            return {
                "kind": self.kind,
                "endpoints": [list(endpoint) for endpoint in self.endpoints],
                "radius": self.radius,
            }
        return {"kind": self.kind, "radii": list(self.radii or ())}


@dataclass(frozen=True)
class Node:
    label: str
    side: str
    parent: str | None
    socket: str | None
    transform: Transform
    sockets: Mapping[str, Transform]
    primitive: Primitive
    optional: bool = False


@dataclass(frozen=True)
class ResolvedNode:
    node: Node
    world_matrix: tuple[float, ...]
    depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.node.label,
            "side": self.node.side,
            "parent": self.node.parent,
            "socket": self.node.socket,
            "optional": self.node.optional,
            "local_transform": self.node.transform.to_dict(),
            "world_transform": {"matrix": matrix_rows(self.world_matrix)},
            "sockets": {
                name: transform.to_dict()
                for name, transform in sorted(self.node.sockets.items())
            },
            "primitive": self.node.primitive.to_dict(),
        }


@dataclass(frozen=True)
class ResolvedGraph:
    fixture_id: str
    spike_revision: int
    seed: int
    coordinate_convention: Mapping[str, str]
    nodes: tuple[ResolvedNode, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "spike_revision": self.spike_revision,
            "seed": self.seed,
            "coordinate_convention": dict(self.coordinate_convention),
            "nodes": [node.to_dict() for node in self.nodes],
        }


def compose_transforms(
    parent: Transform, child: Transform
) -> tuple[float, ...]:
    """Compose two local transforms as ``parent * child``."""

    return _matmul(parent.matrix(), child.matrix())


def multiply_matrices(
    left: tuple[float, ...], right: tuple[float, ...]
) -> tuple[float, ...]:
    """Multiply two row-major 4x4 matrices for resolver composition."""

    return _matmul(left, right)
