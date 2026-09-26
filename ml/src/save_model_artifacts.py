"""Export the verified statistical coefficients and replay the fidelity surrogate.

The JSON coefficients are portable population-level model parameters. The
surrogate is a separate sklearn estimator and is never a change detector.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score


ROOT = Path(__file__).resolve().parent.parent
FEATURES = ["per_domain_z", "cross_domain_z", "rt_z"]
MODEL_NAMES = ["accuracy", "rt", "rt_clustered_ols", "accuracy_binomial_clustered"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_verified_run(run: Path) -> tuple[dict, dict]:
    pointer = json.loads((ROOT / "outputs" / "latest_successful_run.json").read_text(encoding="utf-8"))
    if run.resolve() != Path(pointer["path"]).resolve():
        raise ValueError("Only the latest successful run can be exported")
    manifest_path = run / "manifest.json"
    if digest(manifest_path) != pointer["manifest_sha256"]:
        raise ValueError("Run manifest hash differs from latest-successful pointer")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["status"] != "completed":
        raise ValueError("Run was not completed")
    required = ["model_results.json", "statistical_models_results.json", "surrogate_results.json",
                "session_intelligence_results.jsonl", "training_reference.csv", "config.json"]
    for name in required:
        if digest(run / name) != manifest["artifacts"][name]["sha256"]:
            raise ValueError(f"Run artifact hash mismatch: {name}")
    return pointer, manifest


def origin_and_categories(manifest: dict) -> tuple[str, list[int], list[str]]:
    for item in ["cognitive_results", "assessment_sessions", "assessment_types"]:
        info = manifest["inputs"][item]
        if digest(Path(info["path"])) != info["sha256"]:
            raise ValueError(f"Source input changed: {item}")
    cr = pd.read_csv(manifest["inputs"]["cognitive_results"]["path"],
                     usecols=["session_id", "assessment_type_id", "difficulty_level"])
    sessions = pd.read_csv(manifest["inputs"]["assessment_sessions"]["path"],
                           usecols=["session_id", "started_at", "session_status"])
    types = pd.read_csv(manifest["inputs"]["assessment_types"]["path"],
                        usecols=["assessment_type_id", "cognitive_domain"])
    joined = cr.merge(sessions.loc[sessions.session_status.eq("completed")],
                      on="session_id", how="left", validate="one_to_one")
    if joined.started_at.isna().any():
        raise ValueError("Missing training start timestamp")
    joined = joined.merge(types, on="assessment_type_id", how="left", validate="many_to_one")
    if joined.cognitive_domain.isna().any():
        raise ValueError("Missing training domain")
    origin = pd.to_datetime(joined.started_at, utc=True).min().isoformat()
    return origin, sorted(int(x) for x in joined.difficulty_level.unique()), sorted(joined.cognitive_domain.unique().tolist())


def replay_surrogate(run: Path, expected: dict) -> tuple[RandomForestClassifier, dict]:
    selected = json.loads((run / "statistical_models_results.json").read_text(encoding="utf-8"))["selection"]
    cutoff = pd.Timestamp(selected["cutoff"])
    x_train, y_train, x_test, y_test = [], [], [], []
    train_users, test_users = set(), set()
    with (run / "session_intelligence_results.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["change"]["hybrid"] == "insufficient_data":
                continue
            timestamp = pd.Timestamp(row["index_time"])
            features = [0.0 if row["deviation"][name] is None else float(row["deviation"][name])
                        for name in ["per_domain", "cross_domain", "rt"]]
            if row["split"] == "train" and timestamp < cutoff:
                x_train.append(features); y_train.append(row["change"]["hybrid"]); train_users.add(row["user_id"])
            elif row["split"] == "test" and timestamp >= cutoff:
                x_test.append(features); y_test.append(row["change"]["hybrid"]); test_users.add(row["user_id"])
    if train_users & test_users or len(x_train) != expected["train_rows"] or len(x_test) != expected["test_rows"]:
        raise ValueError("Surrogate replay cohorts differ from verified run")
    train = pd.DataFrame(x_train, columns=FEATURES)
    test = pd.DataFrame(x_test, columns=FEATURES)
    model = RandomForestClassifier(n_estimators=60, max_depth=8, min_samples_leaf=5,
                                   random_state=42, n_jobs=1).fit(train, y_train)
    predictions = model.predict(test)
    actual = {
        "accuracy": accuracy_score(y_test, predictions),
        "macro_f1": f1_score(y_test, predictions, average="macro"),
        "balanced_accuracy": balanced_accuracy_score(y_test, predictions),
        "classes": model.classes_.tolist(),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=model.classes_).tolist(),
    }
    for key in ["accuracy", "macro_f1", "balanced_accuracy"]:
        if not np.isclose(actual[key], expected[key], atol=1e-12, rtol=0):
            raise ValueError(f"Surrogate metric mismatch: {key}")
    for key in ["classes", "confusion_matrix"]:
        if actual[key] != expected[key]:
            raise ValueError(f"Surrogate output mismatch: {key}")
    return model, actual


def export(run: Path, destination: Path) -> dict:
    pointer, manifest = read_verified_run(run)
    results = json.loads((run / "model_results.json").read_text(encoding="utf-8"))
    summary = json.loads((run / "statistical_models_results.json").read_text(encoding="utf-8"))
    surrogate = json.loads((run / "surrogate_results.json").read_text(encoding="utf-8"))
    origin, difficulties, domains = origin_and_categories(manifest)
    if any(results[name]["status"] != "fitted" for name in MODEL_NAMES) or surrogate["status"] != "fitted":
        raise ValueError("A model required for the export did not fit")
    model, replay = replay_surrogate(run, surrogate)
    destination.mkdir(parents=True, exist_ok=False)
    files = []
    for name in MODEL_NAMES:
        fit = results[name]
        payload = {
            "schema_version": "1.0",
            "run_id": pointer["run_id"],
            "pipeline_version": manifest["version"],
            "model_name": name,
            "fit": fit,
            "inference": {
                "scope": "population fixed effects; fitted user random intercepts are not exported",
                "time_days_origin_utc": origin,
                "time_days_source": "started_at",
                "difficulty_levels": difficulties,
                "cognitive_domains": domains if name in ["rt_clustered_ols", "accuracy_binomial_clustered"] else None,
                "reference_difficulty": 1,
                "reference_domain": "attention" if name in ["rt_clustered_ols", "accuracy_binomial_clustered"] else None,
                "link": "logit" if name == "accuracy_binomial_clustered" else "log" if name in ["rt", "rt_clustered_ols"] else "identity",
                "output": "probability_correct_per_trial" if name == "accuracy_binomial_clustered" else "median_reaction_time_ms" if name in ["rt", "rt_clustered_ols"] else "accuracy_rate",
            },
        }
        path = destination / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        files.append(path)
    run_config = json.loads((run / "config.json").read_text(encoding="utf-8"))
    rule = {
        "schema_version": "1.0", "run_id": pointer["run_id"],
        "purpose": "Historical personal baseline and development-selected research rule; no learned neural weights",
        "config": {key: value for key, value in run_config.items() if not key.endswith("_dir")},
        "selection": summary["selection"],
        "heldout": summary["heldout"],
        "reference_file": "training_reference.csv",
    }
    rule_path = destination / "baseline_rule.json"
    rule_path.write_text(json.dumps(rule, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    files.append(rule_path)
    ref_path = destination / "training_reference.csv"
    ref_path.write_bytes((run / "training_reference.csv").read_bytes())
    files.append(ref_path)
    surrogate_path = destination / "fidelity_surrogate.joblib"
    joblib.dump(model, surrogate_path, compress=3)
    reloaded = joblib.load(surrogate_path)
    if reloaded.classes_.tolist() != replay["classes"] or list(reloaded.feature_names_in_) != FEATURES:
        raise ValueError("Reloaded surrogate differs from fitted estimator")
    files.append(surrogate_path)
    bundle = {
        "schema_version": "1.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "source_run_id": pointer["run_id"], "source_manifest_sha256": pointer["manifest_sha256"],
        "pipeline_version": manifest["version"], "release_status": "internal_validation_only",
        "model_inventory": MODEL_NAMES + ["baseline_rule", "fidelity_surrogate"],
        "surrogate_replay": replay,
        "artifact_hashes": {path.name: digest(path) for path in files},
        "notes": ["Four statistical fits are represented by coefficient/variance JSON, not serialized statsmodels objects.",
                  "Mixed-model population predictions exclude user random intercepts.",
                  "The rule uses prior user observations and a training reference; it has no global learned weights.",
                  "The surrogate learns the engine output, not clinical ground truth."],
    }
    (destination / "bundle_manifest.json").write_text(json.dumps(bundle, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=None)
    parser.add_argument("--destination", type=Path, default=None)
    args = parser.parse_args()
    pointer = json.loads((ROOT / "outputs" / "latest_successful_run.json").read_text(encoding="utf-8"))
    run = args.run or Path(pointer["path"])
    destination = args.destination or ROOT / "model_artifacts" / pointer["run_id"]
    bundle = export(run, destination)
    print(json.dumps({"destination": str(destination), "model_inventory": bundle["model_inventory"],
                      "surrogate_replay": bundle["surrogate_replay"]}, indent=2))


if __name__ == "__main__":
    main()
