import argparse
import json
from ml.checkpoints import file_sha256, load_checkpoint
from ml.dataset import load_manifest
from ml.engine import evaluate, loader, seed_everything


def main():
    parser = argparse.ArgumentParser(description="Evaluate a strict checkpoint on its original held-out test manifest")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--manifest", default="ml/data/manifest.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    seed_everything(42)
    model, metadata, _ = load_checkpoint(args.checkpoint)
    manifest = load_manifest(args.manifest)
    if metadata["manifest_sha256"] != file_sha256(args.manifest) or metadata["classes"] != manifest["classes"]:
        parser.error("Checkpoint/evaluation manifest or class mapping mismatch")
    rows = [r for r in manifest["rows"] if r["split"] == "test"]
    metrics = evaluate(model, loader(rows, manifest["classes"], metadata["preprocessing"], 16), manifest["classes"])
    from pathlib import Path
    Path(args.output).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
