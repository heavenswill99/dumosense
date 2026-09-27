"""Package a completed ML run's weights and aggregate metrics for version control."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package(source: Path, destination: Path) -> dict:
    status_path = source / "run_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if status["status"] != "completed" or status["run_id"] != source.name:
        raise ValueError("Source run is not completed")
    for relative, details in status["artifacts"].items():
        if sha(source / relative) != details["sha256"]:
            raise ValueError(f"Source run artifact changed: {relative}")
    weights = sorted((source / "weights").glob("*.joblib"))
    if len(weights) != 13:
        raise ValueError("Expected 13 saved estimators")
    metrics = json.loads((source / "metrics.json").read_text(encoding="utf-8"))
    if set(metrics["families"]) != {"linear", "random_forest", "catboost", "lightgbm", "isolation_forest"}:
        raise ValueError("Expected five model families")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "weights").mkdir()
    shutil.copy2(source / "metrics.json", destination / "metrics.json")
    for path in weights:
        shutil.copy2(path, destination / "weights" / path.name)
    files = [destination / "metrics.json"] + sorted((destination / "weights").glob("*.joblib"))
    manifest = {
        "schema_version": "1.0", "source_ml_run_id": status["run_id"],
        "statistical_source_run": status["statistical_source_run"],
        "statistical_source_manifest_sha256": metrics["source_manifest_sha256"],
        "release_status": "engineering_validation_only",
        "model_families": list(metrics["families"]),
        "estimators": [path.name for path in weights],
        "dependencies": status["dependencies"],
        "source_sha256": {name: sha(ROOT / "src" / "modeling" / name) for name in
                          ("train_ml_models.py", "tune_ml_models.py", "package_ml_models.py", "verify_ml_run.py")},
        "files": {str(path.relative_to(destination)).replace("\\", "/"): {"bytes": path.stat().st_size, "sha256": sha(path)}
                  for path in files},
        "note": "Contains aggregate metrics and fitted estimators only; no session or user-level predictions.",
    }
    (destination / "package_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=None)
    parser.add_argument("--destination", type=Path, default=None)
    args = parser.parse_args()
    pointer = json.loads((ROOT / "outputs" / "ml_runs" / "latest_successful_ml_run.json").read_text(encoding="utf-8"))
    source = args.run or Path(pointer["path"])
    if source.resolve() != Path(pointer["path"]).resolve() or sha(source / "run_status.json") != pointer["status_sha256"]:
        raise ValueError("ML run pointer hash mismatch")
    destination = args.destination or ROOT / "weights" / pointer["run_id"]
    result = package(source, destination)
    print(json.dumps({"destination": str(destination), "families": result["model_families"],
                      "saved_estimators": len(result["estimators"])}, indent=2))


if __name__ == "__main__":
    main()
