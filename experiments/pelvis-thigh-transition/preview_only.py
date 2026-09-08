"""Capture UNVERIFIED surfaces before the independent numeric checks finish.

This is the geometry/render phase of an attempt, not a passing result. The
complete mesh is retained for inspection and later comparison. No fallbacks.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path

import construction
import render


def capture(job):
    case, destination = job
    destination = Path(destination)
    destination.mkdir()
    report = {"case": case["id"], "technical": "unverified", "visual": "pending"}
    try:
        levels = construction.evaluate(construction.build(
            case["components"], case["attachments"], diagnostic=True), levels=2)
        for index, mesh in enumerate(levels):
            (destination / f"mesh-level-{index}.json").write_text(
                json.dumps(mesh, sort_keys=True, allow_nan=False) + "\n")
        human = case["role"] == "executable_cross_family_challenge"
        bounds = ((-.30, -.42, -.20), (.30, .16, .20)) if human else (
            (-2.40, -2.70, -1.30), (2.40, 1.00, 1.30))
        overlays = [{"start": row["centre"], "end": row["knee"],
                     "color": [40, 100, 210], "label": f"{side} source intention"}
                    for side, row in case["attachments"].items()]
        report["admission"] = levels[0]["metadata"]["admission_status"]
        status = "REJECTED INPUT" if report["admission"] == "rejected" else "UNVERIFIED"
        report["render"] = render.render_views(
            levels[-1]["vertices"], levels[-1]["quads"], destination / "surface.png",
            case["id"], status, bounds=bounds, overlays=overlays,
            allow_crop=True, underside=True)
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    (destination / "preview-report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(f"{case['id']}: {report.get('error', 'unverified surface captured')}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists():
        parser.error("output must be an absent absolute path")
    document = json.loads(args.inputs.read_text())
    args.output.mkdir()
    (args.output / "inputs.json").write_bytes(args.inputs.read_bytes())
    with ProcessPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(capture, [(case, str(args.output / case["id"]))
                                         for case in document["cases"]]))
    (args.output / "preview-report.json").write_text(json.dumps(
        {"technical": "unverified", "cases": reports}, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
