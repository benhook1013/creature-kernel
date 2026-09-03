import ctypes, errno, hashlib, math, os, shutil, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepared_projection import canonical_json_bytes, prepare_standard_neutral
import render_export
import root_complex_surface as surface


MAX_NORMAL_ANGLE_DIAGNOSTIC_FACES = 2048
MAX_NORMAL_ANGLE_DIAGNOSTIC_INTERIOR_EDGES = 4096
FOLD_ANGLE_THRESHOLD_RADIANS = math.pi / 2.0


def _sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def _face_normal(mesh, face):
    points = tuple(tuple(float(component) for component in mesh.vertices[index]) for index in face)
    if len(points) != 4 or any(len(point) != 3 or any(not math.isfinite(component) for component in point) for point in points):
        raise ValueError("normal-angle diagnostic encountered a nonfinite or non-quad face")
    points = min(points[offset:] + points[:offset] for offset in range(4))
    try:
        normal = tuple(math.fsum((current[(axis + 1) % 3] - following[(axis + 1) % 3]) *
                                (current[(axis + 2) % 3] + following[(axis + 2) % 3])
                                for current, following in zip(points, points[1:] + points[:1]))
                       for axis in range(3))
    except OverflowError as exc:
        raise ValueError("normal-angle diagnostic encountered a nonfinite face normal") from exc
    length = math.hypot(*normal)
    if not math.isfinite(length) or length == 0.0:
        raise ValueError("normal-angle diagnostic encountered a degenerate face")
    return tuple(component / length for component in normal)


def normal_angle_fold_diagnostics(levels):
    """Report bounded adjacent-face normal angles without a continuity claim."""
    if not levels or len(levels) > 2:
        raise ValueError("normal-angle diagnostic requires one or two evaluated levels")
    reports = []
    for level_number, mesh in enumerate(levels, start=1):
        if len(mesh.quads) > MAX_NORMAL_ANGLE_DIAGNOSTIC_FACES:
            raise ValueError("normal-angle diagnostic face cap exceeded")
        normals = tuple(_face_normal(mesh, face) for face in mesh.quads)
        edge_faces = {}
        for face_index, face in enumerate(mesh.quads):
            for a, b in zip(face, face[1:] + face[:1]):
                edge = tuple(sorted((int(a), int(b))))
                edge_faces.setdefault(edge, []).append(face_index)
        interior_edges = tuple(sorted((edge, tuple(face_indices))
                                      for edge, face_indices in edge_faces.items()
                                      if len(face_indices) == 2))
        if len(interior_edges) > MAX_NORMAL_ANGLE_DIAGNOSTIC_INTERIOR_EDGES:
            raise ValueError("normal-angle diagnostic interior-edge cap exceeded")
        angles = []
        for _, (first, second) in interior_edges:
            cosine = sum(normals[first][axis] * normals[second][axis] for axis in range(3))
            cosine = max(-1.0, min(1.0, cosine))
            angles.append(math.acos(cosine))
        if angles:
            minimum, maximum = min(angles), max(angles)
            mean = math.fsum(angles) / len(angles)
        else:
            minimum = maximum = mean = 0.0
        folded = sum(angle > FOLD_ANGLE_THRESHOLD_RADIANS for angle in angles)
        reports.append({"level": level_number, "interior_edge_count": len(angles),
                        "normal_angle_min_radians": minimum,
                        "normal_angle_mean_radians": mean,
                        "normal_angle_max_radians": maximum,
                        "fold_threshold_radians": FOLD_ANGLE_THRESHOLD_RADIANS,
                        "folded_edge_count": folded,
                        "folded_edge_fraction": folded / len(angles) if angles else 0.0})
    return {"schema": "programmatic-root-complex.normal-angle-fold.v1",
            "normal_definition": "unit Newell normal of each full outward-wound quad",
            "angle_definition": "acos(clamp(dot(adjacent normals), -1, 1)) in radians",
            "fold_definition": "adjacent normal angle strictly greater than pi/2",
            "levels": tuple(reports)}


def _publish_no_replace(stage: Path, target: Path) -> None:
    if sys.platform != "linux":
        raise RuntimeError("atomic no-replace publication requires Linux renameat2")
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError) as exc:
        raise RuntimeError("Linux renameat2 is unavailable; refusing unsafe publication") from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(stage), -100, os.fsencode(target), 1) == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise FileExistsError(error, os.strerror(error), target)
    if error in {errno.EINVAL, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP}:
        raise RuntimeError("Linux renameat2 no-replace publication is unavailable")
    raise OSError(error, os.strerror(error), target)


def build(source: str | Path, output_dir: str | Path) -> Path:
    target = Path(output_dir)
    if os.path.lexists(target) or not target.parent.is_dir():
        raise FileExistsError(f"output directory must be new and have an existing parent: {target}")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    try:
        prepared = prepare_standard_neutral(source); evaluated = surface.evaluate(prepared, levels=2); intersection_counts = tuple(evaluated.intersection_counts)
        if any(intersection_counts): raise ValueError("refusing publication with nonzero evaluated intersections")
        final, cage = evaluated.levels[-1], evaluated.cage
        scale = surface.validate_geometry(final, evaluated=True)
        (stage / "prepared.json").write_bytes(canonical_json_bytes(prepared))
        render_export.write_skin_ply(stage / "skin.ply", final.vertices, final.quads)
        render_export.render_skin_png(stage / "skin.png", final.vertices, final.quads)
        render_export.render_cage_png(stage / "cage.png", cage.vertices, cage.quads)
        files = {name: _sha256(stage / name) for name in ("prepared.json", "skin.ply", "skin.png", "cage.png")}
        metrics = {"schema": "programmatic-root-complex.metrics.v1", "level": 2,
                   "scale": scale, "cage_vertices": len(cage.vertices),
                   "cage_quads": len(cage.quads), "skin_vertices": len(final.vertices),
                   "skin_quads": len(final.quads), "intersection_status": "zero" if not any(intersection_counts) else "nonzero",
                   "intersection_count": sum(intersection_counts), "intersection_counts_by_level": intersection_counts,
                   "clearance_ratios": dict(evaluated.clearance_ratios),
                   "normal_angle_fold_diagnostics": normal_angle_fold_diagnostics(evaluated.levels),
                   "files": files.copy()}
        (stage / "metrics.json").write_bytes(canonical_json_bytes(metrics))
        files["metrics.json"] = _sha256(stage / "metrics.json")
        manifest = {"schema": "programmatic-root-complex.manifest.v1", "source_sha256": prepared["source"]["sha256"], "files": files}
        (stage / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        _publish_no_replace(stage, target)
        return target
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_root_complex.py SOURCE OUTPUT_DIR")
    build(sys.argv[1], sys.argv[2])
