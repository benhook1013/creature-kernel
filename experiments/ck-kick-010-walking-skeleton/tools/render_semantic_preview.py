#!/usr/bin/env python3
"""Render a CK-KICK-010 PLY as a simple semantic orthographic preview.

This is disposable diagnostic tooling.  Its colours are source-region debug
colours, not material or visual-intent data.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh


PALETTE = {
    "torso": (55, 130, 205),
    "pelvis": (45, 165, 175),
    "head": (225, 145, 55),
    "muzzle": (245, 195, 90),
    "left_ear": (235, 115, 145),
    "right_ear": (205, 90, 125),
    "left_arm": (75, 170, 105),
    "right_arm": (55, 140, 90),
    "left_hand_paw": (125, 205, 115),
    "right_hand_paw": (95, 180, 95),
    "left_thigh": (135, 100, 205),
    "right_thigh": (105, 80, 175),
    "left_shin": (165, 125, 225),
    "right_shin": (130, 100, 195),
    "left_foot_paw": (195, 150, 235),
    "right_foot_paw": (155, 120, 205),
}

CANVAS_SIZE = (1620, 900)
VIEW_BOXES = {
    "front": (20, 60, 530, 880),
    "side": (555, 60, 1065, 880),
    "three-quarter": (1090, 60, 1600, 880),
}


def face_labels(faces: np.ndarray, labels: list[str]) -> list[str]:
    output = []
    for a, b, c in faces:
        values = (labels[int(a)], labels[int(b)], labels[int(c)])
        output.append(max(sorted(set(values)), key=values.count))
    return output


def render_view(
    image: Image.Image,
    vertices: np.ndarray,
    faces: np.ndarray,
    labels: list[str],
    basis: np.ndarray,
    box: tuple[int, int, int, int],
    title: str,
) -> None:
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = box
    camera_vertices = vertices @ basis.T
    triangles = camera_vertices[faces]
    edge_one = triangles[:, 1] - triangles[:, 0]
    edge_two = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(edge_one, edge_two)
    visible = normals[:, 2] > 0.0
    indices = np.flatnonzero(visible)
    indices = indices[np.argsort(np.mean(triangles[indices, :, 2], axis=1))]

    projected = camera_vertices[:, :2]
    lower = projected.min(axis=0)
    upper = projected.max(axis=0)
    span = np.maximum(upper - lower, 1e-9)
    margin = 34
    width = x1 - x0 - margin * 2
    height = y1 - y0 - margin * 2 - 34
    scale = min(width / span[0], height / span[1])
    center = (lower + upper) * 0.5

    def screen(points: np.ndarray) -> list[tuple[float, float]]:
        values = (points - center) * scale
        return [
            (x0 + (x1 - x0) * 0.5 + float(px), y0 + 34 + height * 0.5 - float(py))
            for px, py in values
        ]

    light = np.array([0.35, 0.55, 0.76], dtype=np.float64)
    light /= np.linalg.norm(light)
    for index in indices:
        normal = normals[index]
        normal /= max(np.linalg.norm(normal), 1e-12)
        brightness = 0.48 + 0.52 * max(0.0, float(np.dot(normal, light)))
        base = PALETTE.get(labels[index], (160, 165, 175))
        colour = tuple(min(255, int(value * brightness)) for value in base)
        draw.polygon(screen(triangles[index, :, :2]), fill=colour)

    draw.rectangle(box, outline=(65, 72, 86), width=2)
    draw.text((x0 + 18, y0 + 10), title, fill=(235, 238, 244), font=ImageFont.load_default())


def render_preview(mesh_path: Path, regions_path: Path) -> Image.Image:
    mesh = trimesh.load(mesh_path, process=False)
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    region_data = json.loads(regions_path.read_text(encoding="utf-8"))
    vertex_labels = region_data["source_node_labels"]
    labels = face_labels(faces, vertex_labels)

    image = Image.new("RGB", CANVAS_SIZE, (22, 25, 32))
    front = np.eye(3)
    side = np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
    root_two = np.sqrt(2.0)
    three_quarter = np.array(
        [
            [1.0 / root_two, 0.0, -1.0 / root_two],
            [0.0, 1.0, 0.0],
            [1.0 / root_two, 0.0, 1.0 / root_two],
        ]
    )
    render_view(image, vertices, faces, labels, front, VIEW_BOXES["front"], "Front (+Z camera)")
    render_view(image, vertices, faces, labels, side, VIEW_BOXES["side"], "Side (+X camera)")
    render_view(
        image,
        vertices,
        faces,
        labels,
        three_quarter,
        VIEW_BOXES["three-quarter"],
        "Three-quarter",
    )
    ImageDraw.Draw(image).text(
        (20, 20),
        "CK-KICK-010 exact generated mesh — semantic source-region colours",
        fill=(245, 247, 250),
        font=ImageFont.load_default(),
    )
    return image


def path_exists(path: Path) -> bool:
    """Return true for regular paths and dangling symlinks alike."""

    return os.path.lexists(path)


def ensure_new_target(path: Path, description: str) -> None:
    if path_exists(path):
        raise RuntimeError(f"refusing to overwrite existing {description}: {path}")
    if not path.parent.is_dir():
        raise RuntimeError(f"{description} parent must already exist: {path.parent}")


def write_png_no_overwrite(image: Image.Image, path: Path) -> None:
    """Write one PNG using exclusive creation and clean a partial own file."""

    created = False
    try:
        with path.open("xb") as handle:
            created = True
            image.save(handle, format="PNG")
    except Exception:
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise


def cleanup(created_files: list[Path], created_directories: list[Path]) -> None:
    for path in reversed(created_files):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    for path in reversed(created_directories):
        try:
            path.rmdir()
        except (FileNotFoundError, OSError):
            # Do not remove anything not created by this invocation.
            pass


def run(args: argparse.Namespace) -> None:
    ensure_new_target(args.output, "output file")
    if args.views_dir is not None:
        ensure_new_target(args.views_dir, "views directory")

    created_files: list[Path] = []
    created_directories: list[Path] = []
    try:
        image = render_preview(args.mesh, args.regions)

        write_png_no_overwrite(image, args.output)
        created_files.append(args.output)

        if args.views_dir is not None:
            args.views_dir.mkdir()
            created_directories.append(args.views_dir)
            for name, box in VIEW_BOXES.items():
                view_path = args.views_dir / f"{name}.png"
                write_png_no_overwrite(image.crop(box), view_path)
                created_files.append(view_path)
    except Exception:
        cleanup(created_files, created_directories)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a disposable CK-KICK-010 semantic diagnostic preview."
    )
    parser.add_argument("--mesh", type=Path, required=True, help="generated PLY mesh")
    parser.add_argument("--regions", type=Path, required=True, help="semantic region JSON sidecar")
    parser.add_argument("--output", type=Path, required=True, help="combined preview PNG")
    parser.add_argument(
        "--views-dir",
        type=Path,
        help="new directory for exact front.png, side.png, and three-quarter.png panel crops",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError, trimesh.exceptions.TrimeshException) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
