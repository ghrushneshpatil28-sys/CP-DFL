"""Validate and select an inference checkpoint. Selection is not clinical approval."""
import argparse
import json
from pathlib import Path
import shutil
import os

from ml.checkpoints import file_sha256, load_checkpoint
from ml.dataset import ROOT, load_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("--manifest", default=str(ROOT / "ml/data/manifest.json"))
    parser.add_argument("--destination", default=str(ROOT / "ml/saved_models/approved.pt"))
    parser.add_argument("--evaluation", help="Completed experiment results.json; bound to the selected model hash")
    args = parser.parse_args()
    _, meta, _ = load_checkpoint(args.checkpoint)
    manifest = load_manifest(args.manifest)
    if meta["classes"] != manifest["classes"] or meta["manifest_sha256"] != file_sha256(args.manifest):
        parser.error("Checkpoint mapping or dataset provenance mismatch")
    source, destination = Path(args.checkpoint).resolve(), Path(args.destination).resolve()
    results_path = Path(args.evaluation) if args.evaluation else source.parent / "results.json"
    evidence = None
    if results_path.is_file():
        from ml.evaluation_evidence import build_evidence
        evidence = build_evidence(source, results_path)
    elif args.evaluation:
        parser.error("Evaluation results file is missing")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source != destination:
        temporary = destination.with_suffix(".pt.tmp")
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    destination.with_suffix(".metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    evidence_path = destination.with_suffix(".evaluation.json")
    if evidence:
        temporary = evidence_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        os.replace(temporary, evidence_path)
    else:
        evidence_path.unlink(missing_ok=True)
    print(f"Selected research checkpoint {meta['version']}; {meta['validation_scope']}; clinical validation not established")


if __name__ == "__main__":
    main()
