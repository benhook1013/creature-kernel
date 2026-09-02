import ctypes, errno, hashlib, os, shutil, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepared_projection import canonical_json_bytes, prepare_standard_neutral
import render_export
import root_complex_surface as surface


def _sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


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
                   "clearance_ratios": dict(evaluated.clearance_ratios), "files": files.copy()}
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
