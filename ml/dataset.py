"""Non-destructive dataset audit and deterministic, content-grouped manifests."""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scan(source, metadata=None):
    source = Path(source).resolve()
    if not source.is_dir():
        raise ValueError(f"Dataset directory does not exist: {source}")
    identities = {}
    if metadata:
        with open(metadata, newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                identities[row["path"].replace("\\", "/")] = row
    rows, invalid = [], []
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in EXTENSIONS or not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.load()
                pixel_hash = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
        except Exception as error:
            invalid.append({"path": relative, "error": str(error)})
            continue
        identity = identities.get(relative, {})
        rows.append({"path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                     "label": path.parent.name, "sha256": digest(path), "pixel_sha256": pixel_hash,
                     "patient_id": identity.get("patient_id", ""), "study_id": identity.get("study_id", ""),
                     "original_split": path.relative_to(source).parts[0]})
    if not rows:
        raise ValueError("No valid images found; refusing to report an empty audit as clean")
    return rows, invalid


def group_rows(rows):
    # Union content duplicates AND patient identities, including transitive links.
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        for key in ["sha256", "pixel_sha256", "patient_id", "study_id"]:
            if not row.get(key):
                continue
            identity = (key, row[key])
            if identity in seen:
                parent[find(i)] = find(seen[identity])
            seen[identity] = i
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    return list(groups.values())


def create_manifest(rows, seed=42, ratios=(.70, .15, .15), preserve_test=True):
    if len(ratios) != 3 or abs(sum(ratios) - 1) > 1e-8 or min(ratios) <= 0:
        raise ValueError("Three positive split ratios must sum to one")
    rng = random.Random(seed)
    groups = group_rows(rows)
    assignments, counts = [], Counter()
    total = len({r["pixel_sha256"] for r in rows})
    targets = dict(zip(["train", "val", "test"], [r * total for r in ratios]))
    rng.shuffle(groups)
    groups.sort(key=lambda g: not any(r["original_split"] == "test" for r in g))
    class_counts = defaultdict(Counter)
    for index, group in enumerate(groups):
        unique = {r["pixel_sha256"]: r for r in group}
        labels = {r["label"] for r in group}
        if len(labels) > 1 and len(unique) == 1:
            raise ValueError(f"Conflicting labels for duplicate content: {sorted(labels)}")
        if preserve_test and any(r["original_split"] == "test" for r in group):
            split = "test"
        else:
            candidates = ["train", "val"] if preserve_test else ["train", "val", "test"]
            label = sorted(labels)[0]
            split = min(candidates, key=lambda s: (class_counts[label][s] / max(targets[s], 1), counts[s] / max(targets[s], 1)))
        for row in unique.values():
            assignments.append({**row, "split": split, "group_id": f"g{index:06d}"})
            counts[split] += 1
            class_counts[row["label"]][split] += 1
    return sorted(assignments, key=lambda r: r["path"])


def verify_manifest(rows):
    if not rows:
        raise ValueError("Empty manifest")
    for key in ["sha256", "pixel_sha256", "patient_id", "study_id", "group_id"]:
        seen = {}
        for row in rows:
            identity = row.get(key)
            if identity and identity in seen and seen[identity] != row["split"]:
                raise ValueError(f"Cross-split {key} overlap")
            if identity:
                seen[identity] = row["split"]
    for split in ["train", "val", "test"]:
        if not any(r["split"] == split for r in rows):
            raise ValueError(f"No {split} samples; supply enough independent groups")


def load_manifest(path, verify_files=True):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    verify_manifest(data["rows"])
    if verify_files:
        for row in data["rows"]:
            if digest(ROOT / row["path"]) != row["sha256"]:
                raise ValueError(f"Dataset changed: {row['path']}")
    return data


def audit(source, output, metadata=None, seed=42, ratios=(.7, .15, .15), preserve_test=True):
    rows, invalid = scan(source, metadata)
    by_hash, by_pixel = defaultdict(list), defaultdict(list)
    for row in rows:
        by_hash[row["sha256"]].append(row)
        by_pixel[row["pixel_sha256"]].append(row)
    duplicates = [v for v in by_hash.values() if len(v) > 1]
    if any(len({r["label"] for r in v}) > 1 for v in by_pixel.values()):
        raise ValueError("Conflicting duplicate labels; resolve before splitting")
    manifest = create_manifest(rows, seed, ratios, preserve_test)
    verify_manifest(manifest)
    result = {"schema_version": 1, "seed": seed, "requested_ratios": ratios,
              "preserved_existing_test": preserve_test,
              "validation_scope": "patient-independent" if all(r["patient_id"] for r in rows) else "provisional image-group split; patient independence unverified",
              "classes": sorted({r["label"] for r in rows}),
              "image_files": len(rows), "unique_images": len(manifest), "duplicate_groups": len(duplicates),
              "original_train_test_duplicate_groups": sum(any(r["original_split"] == "train" for r in v) and any(r["original_split"] == "test" for r in v) for v in by_pixel.values()),
              "missing_patient_ids": sum(not r["patient_id"] for r in rows), "invalid": invalid,
              "distribution": {s: dict(Counter(r["label"] for r in manifest if r["split"] == s)) for s in ["train", "val", "test"]},
              "duplicate_examples": [[r["path"] for r in v] for v in duplicates[:10]], "rows": manifest}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "backend/DataSet"))
    parser.add_argument("--output", default=str(ROOT / "ml/data/manifest.json"))
    parser.add_argument("--metadata", help="CSV with source-relative path,patient_id,study_id")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ratios", nargs=3, type=float, default=[.7, .15, .15])
    parser.add_argument("--repartition-test", action="store_true", help="Explicitly abandon old evaluation boundary")
    args = parser.parse_args()
    result = audit(args.source, args.output, args.metadata, args.seed, args.ratios, not args.repartition_test)
    print(json.dumps({k: v for k, v in result.items() if k not in ["rows", "duplicate_examples"]}, indent=2))


if __name__ == "__main__":
    main()
