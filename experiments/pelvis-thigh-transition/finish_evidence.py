"""Compare completed captured runs and render stored L2 evidence; never run checks."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def read(path):
    def invalid(token):
        raise ValueError(f"nonfinite JSON token: {token}")
    return json.loads(path.read_bytes(), parse_constant=invalid)


def normal(value, root):
    # Only exact root strings or paths under that root; never replace prose/substrings.
    if isinstance(value, str):
        return "<RUNROOT>" + value[len(root):] if value == root or value.startswith(root + "/") else value
    if isinstance(value, list):
        return [normal(item, root) for item in value]
    if isinstance(value, dict):
        return {key: normal(item, root) for key, item in value.items()}
    return value


def local(root, relative):
    path = root / relative
    require(not Path(relative).is_absolute() and path.resolve().is_relative_to(root), "artifact escapes run root")
    require(path.is_file() and not path.is_symlink(), f"missing/nonregular artifact: {path}")
    return path


def complete(root):
    report, inputs = read(local(root, "run-report.json")), read(local(root, "inputs.json"))
    require(report["schema"] == "creature-kernel.pelvis-thigh-transition-run-report.v1", "wrong report schema")
    rows = report["cases"]
    require(len(rows) == report["case_count"] == len(inputs["cases"]), "incomplete case count")
    require([r["case_id"] for r in rows] == [c["id"] for c in inputs["cases"]], "case inventory mismatch")
    require(len({r["case_id"] for r in rows}) == len(rows), "duplicate case IDs")
    require(len(inputs["mandatory_case_ids"]) == len(set(inputs["mandatory_case_ids"])) == 6, "six mandatory IDs required")
    comparisons = report["perturbation_comparisons"]
    require([c["case_id"] for c in comparisons] == inputs["perturbation_case_ids"], "incomplete comparisons")
    by_id = {}
    for index, row in enumerate(rows):
        case_id = row["case_id"]
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", case_id), "unsafe case ID")
        require(row["index"] == index and row["phase"] == "checkscomplete", "case not complete")
        require(isinstance(row["check_result"], dict) and isinstance(row["outcome"], str), "missing case result")
        directory = Path("cases") / f"case-{index:02d}-{case_id}"
        require([a["level"] for a in row["artifacts"]] == [0, 1, 2], "missing mesh levels")
        paths = [local(root, directory / a["path"]) for a in row["artifacts"]]
        require(any((root / directory).glob("*.png")), "missing direct views")
        by_id[case_id] = (row, paths[2])
    require(set(inputs["mandatory_case_ids"]).issubset(by_id), "missing mandatory cases")
    return report, inputs, by_id


def inventory(root):
    paths = sorted(p for p in root.rglob("*") if p.suffix.lower() == ".png" or p.match("mesh-level-*.json"))
    return {p.relative_to(root).as_posix(): local(root, p.relative_to(root)) for p in paths}


def finish(first, repeat, output):
    for path in (first, repeat, output):
        require(path.is_absolute() and path == path.resolve(), "paths must be absolute and canonical")
    require(first != repeat and first.is_dir() and repeat.is_dir(), "two distinct run roots required")
    require(not output.exists() and not output.is_symlink() and output.parent.is_dir(), "output must be absent with existing parent")
    require(not any(output.is_relative_to(root) for root in (first, repeat)), "output must be outside runs")
    a, ai, ac = complete(first)
    b, bi, bc = complete(repeat)
    left, right = inventory(first), inventory(repeat)
    mismatches, hashes = [], [{}, {}]
    for name in sorted(left.keys() | right.keys()):
        x, y = left[name].read_bytes() if name in left else None, right[name].read_bytes() if name in right else None
        for table, data in zip(hashes, (x, y)):
            if data is not None:
                table[name] = {"bytes": len(data), "sha256": digest(data)}
        if x != y:
            mismatches.append({"path": name, "first": hashes[0].get(name), "repeat": hashes[1].get(name)})
    numeric, outcomes = [], []
    for case_id in sorted(ac.keys() | bc.keys()):
        x = ac[case_id][0] if case_id in ac else None
        y = bc[case_id][0] if case_id in bc else None
        outcomes.append({"case_id": case_id, "first": x["outcome"] if x else None, "repeat": y["outcome"] if y else None})
        numeric.append((case_id, {k: x[k] for k in ("outcome", "check_result")} if x else None,
                        {k: y[k] for k in ("outcome", "check_result")} if y else None))
    numeric.extend((("perturbation_comparisons", a["perturbation_comparisons"], b["perturbation_comparisons"]), ("inputs", ai, bi)))
    numeric_rows = []
    for name, x, y in numeric:
        x, y = encoded(normal(x, str(first))), encoded(normal(y, str(repeat)))
        numeric_rows.append({"name": name, "equal": x == y, "first_sha256": digest(x), "repeat_sha256": digest(y)})
    summary = {"schema": "pelvis-thigh-transition/determinism-v1", "first": str(first), "repeat": str(repeat),
               "equal": not mismatches and all(r["equal"] for r in numeric_rows), "artifact_counts": [len(left), len(right)],
               "inventory_sha256": [digest(encoded(h)) for h in hashes], "artifact_mismatches": mismatches,
               "numeric_comparisons": numeric_rows, "per_case_outcomes": outcomes,
               "normalization": "Only exact run-root strings and root/ path prefixes; all other data retained."}
    meshes = {case_id: read(ac[case_id][1]) for case_id in ai["mandatory_case_ids"]}
    renderer_path = Path(__file__).resolve().with_name("render.py")
    spec = importlib.util.spec_from_file_location("finish_captured_render", renderer_path)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    output.mkdir()
    (output / "determinism-report.json").write_bytes(encoded(summary))
    rendered = []
    for case_id, mesh in meshes.items():
        # Exact declared lower-crop frames from runner._case_bounds; no geometry import.
        bounds = [[-0.30, -0.42, -0.20], [0.30, 0.16, 0.20]] if case_id == "ordinary_human_reference" else [[-2.4, -2.7, -1.3], [2.4, 1.0, 1.3]]
        require(mesh["level"] == 2 and ac[case_id][0]["bounds"]["lowercrop"] == bounds, "L2/frame declaration mismatch")
        directory = output / case_id
        directory.mkdir()
        metadata = renderer.render_views(mesh["vertices"], mesh["quads"], directory / "surface.png", title=case_id,
                                         status="REJECTED - FINAL BUDGET", bounds=bounds, allow_crop=True, underside=True)
        rendered.append({"case_id": case_id, "source_mesh": str(ac[case_id][1]),
                         "source_mesh_sha256": digest(ac[case_id][1].read_bytes()), "render": metadata})
    manifest = {"schema": "pelvis-thigh-transition/finish-manifest-v1",
                "parent_judgment": {"status": "REJECTED - FINAL BUDGET", "source": "supplied parent instruction",
                                    "automatically_inferred": False, "independent_of_technical_outcomes": True},
                "helper_sha256": digest(Path(__file__).read_bytes()), "renderer_sha256": digest(renderer_path.read_bytes()),
                "renders": rendered, "files": [], "self_hash": "manifest SHA-256 returned on stdout; self excluded from files"}
    for path in sorted(output.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            manifest["files"].append({"path": path.relative_to(output).as_posix(), "bytes": len(data), "sha256": digest(data)})
    raw = encoded(manifest)
    (output / "output-manifest.json").write_bytes(raw)
    return {"deterministic": summary["equal"], "output_manifest_sha256": digest(raw)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("first", "repeat", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finish(args.first, args.repeat, args.output), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
