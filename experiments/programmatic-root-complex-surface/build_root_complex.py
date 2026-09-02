"""Build the disposable standard-neutral root-complex evidence package."""

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepared_projection import canonical_json_bytes, prepare_standard_neutral
import render_export
import root_complex_surface as surface


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source: str | Path, output_dir: str | Path) -> Path:
    target = Path(output_dir)
    if os.path.lexists(target) or not target.parent.is_dir():
        raise FileExistsError(f"output directory must be new and have an existing parent: {target}")
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    created_target = False
    try:
        prepared = prepare_standard_neutral(source)
        evaluated = surface.evaluate(prepared, levels=2)
        final, cage = evaluated.levels[-1], evaluated.cage
        (stage / "prepared.json").write_bytes(canonical_json_bytes(prepared))
        render_export.write_skin_ply(stage / "skin.ply", final.vertices, final.quads)
        render_export.render_skin_png(stage / "skin.png", final.vertices, final.quads)
        render_export.render_cage_png(stage / "cage.png", cage.vertices, cage.quads)
        files = {name: _sha256(stage / name) for name in ("prepared.json", "skin.ply", "skin.png", "cage.png")}
        scale = surface.validate_geometry(final, evaluated=True)
        metrics = {"schema": "programmatic-root-complex.metrics.v1", "level": 2, "scale": scale, "cage_vertices": len(cage.vertices), "cage_quads": len(cage.quads), "skin_vertices": len(final.vertices), "skin_quads": len(final.quads), "files": files}
        (stage / "metrics.json").write_bytes(canonical_json_bytes(metrics))
        files["metrics.json"] = _sha256(stage / "metrics.json")
        manifest = {"schema": "programmatic-root-complex.manifest.v1", "source_sha256": prepared["source"]["sha256"], "files": files}
        (stage / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        if os.path.lexists(target):
            raise FileExistsError(f"output directory appeared during build: {target}")
        os.mkdir(target)
        created_target = True
        os.rename(stage, target)
        return target
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        if created_target:
            try:
                target.rmdir()
            except OSError:
                pass
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_root_complex.py SOURCE OUTPUT_DIR")
    build(sys.argv[1], sys.argv[2])
