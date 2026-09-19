#!/usr/bin/env python3
"""Offline NSFW rating pass over the local image archive.

Runs a local Falconsai/nsfw_image_detection classifier over every image row in
the SQLite archive and appends the results to data/content-ratings.jsonl,
which the API and the gallery consume. Nothing here touches the database - the
SQLite connection is read-only.

Heavy dependencies (torch, transformers) are injected by uv at run time
instead of living in pyproject, so server installs stay light:

  npm run audit:nsfw                          # rate everything still missing
  npm run audit:nsfw -- --sample 100          # random stratified subset
  npm run audit:nsfw -- --report .oip/ratings-report --sample 100
  npm run audit:nsfw -- --model E:/models/nsfw_image_detection

Images are loaded one batch at a time (never the whole corpus at once) and
results are flushed per batch, so an interrupted pass keeps its progress. The
sidecar is rewritten atomically with a fresh meta line at the end. Raw scores
are kept (`s`), so re-thresholding later never needs a re-run.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import shutil
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from runtime.archive_db import connect_read_only, ensure_working_database

RATINGS_PATH = REPOSITORY_ROOT / "data" / "content-ratings.jsonl"
SCHEMA_VERSION = 1
HF_MODEL_ID = "Falconsai/nsfw_image_detection"
DEFAULT_MODEL_DIRS = [
    Path(r"E:\models\nsfw_image_detection"),
    REPOSITORY_ROOT / ".oip" / "models" / "nsfw_image_detection",
]
NSFW_MIN = 0.85
BORDERLINE_MIN = 0.40
NSFW_LABEL = "nsfw"
VALID_RATINGS = ("sfw", "borderline", "nsfw")


def classify(score: float) -> str:
    if score >= NSFW_MIN:
        return "nsfw"
    if score >= BORDERLINE_MIN:
        return "borderline"
    return "sfw"


def read_sidecar(path: Path) -> tuple[dict, dict[str, dict]]:
    meta: dict = {}
    rated: dict[str, dict] = {}
    if not path.exists():
        return meta, rated
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # torn tail line from an interrupted append
        if "schema_version" in record:
            meta = record
            continue
        key = record.get("k")
        if isinstance(key, str) and record.get("r") in VALID_RATINGS:
            rated[key] = record
    return meta, rated


def image_rows() -> list[dict]:
    database = ensure_working_database()
    with connect_read_only(database) as connection:
        rows = connection.execute(
            "SELECT tweet_id,image_index,local_path,url FROM images "
            "ORDER BY CAST(tweet_id AS INTEGER),image_index"
        ).fetchall()
    return [
        {
            "key": f"{row['tweet_id']}/{row['image_index']}",
            "local_path": row["local_path"],
            "url": row["url"],
        }
        for row in rows
    ]


def model_revision(model_path: Path) -> str:
    # snapshot_download(local_dir=...) keeps its manifest under .cache/;
    # best effort - "local" is an acceptable fallback for a manual copy.
    cache = model_path / ".cache" / "huggingface"
    for metadata in sorted(cache.rglob("*.json")):
        try:
            payload = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for value in payload.values() if isinstance(payload, dict) else []:
            if isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value):
                return value
    return "local"


def resolve_model(requested: str | None) -> Path:
    candidates = [Path(requested)] if requested else DEFAULT_MODEL_DIRS
    for candidate in candidates:
        if (candidate / "config.json").exists():
            return candidate
    available = ", ".join(str(path) for path in candidates) or "(none)"
    raise SystemExit(
        f"model files not found; pass --model with the directory containing "
        f"config.json + model.safetensors. Looked in: {available}"
    )


def fetch_image(row: dict):
    """Load one image: prefer the local pack, fall back to the source URL."""
    from PIL import Image

    if row["local_path"]:
        candidate = REPOSITORY_ROOT / row["local_path"]
        if candidate.exists():
            with Image.open(candidate) as image:
                return image.convert("RGB")
    if row["url"]:
        request = urllib.request.Request(
            row["url"],
            headers={"User-Agent": "Mozilla/5.0 (compatible; open-image-prompts-audit/1)"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
        with Image.open(io.BytesIO(payload)) as image:
            return image.convert("RGB")
    return None


def rewrite_sidecar(path: Path, meta: dict, rated: dict[str, dict]) -> None:
    counts = Counter(record["r"] for record in rated.values())

    def order(record: dict):
        tweet_id, _, index = record["k"].partition("/")
        return (int(tweet_id or 0), int(index or 0))

    meta = {
        "schema_version": SCHEMA_VERSION,
        "model": meta.get("model", {"id": HF_MODEL_ID, "revision": "unknown"}),
        "thresholds": {"nsfw_min": NSFW_MIN, "borderline_min": BORDERLINE_MIN},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "sfw": counts.get("sfw", 0),
            "borderline": counts.get("borderline", 0),
            "nsfw": counts.get("nsfw", 0),
            "total": len(rated),
        },
    }
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as sink:
        sink.write(json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n")
        for record in sorted(rated.values(), key=order):
            sink.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tmp, path)


def build_report(report_dir: Path, rows: list[dict], records: list[dict]) -> None:
    """Copy the rated sample images next to an HTML index for eyeballing."""
    report_dir.mkdir(parents=True, exist_ok=True)
    by_key = {row["key"]: row for row in rows}
    entries = []
    for record in records:
        row = by_key.get(record["k"])
        if not row:
            continue
        source = REPOSITORY_ROOT / row["local_path"] if row["local_path"] else None
        if not source or not source.exists():
            continue
        target = report_dir / (record["k"].replace("/", "_") + source.suffix.lower())
        shutil.copyfile(source, target)
        entries.append((record["s"], record["r"], target.name, record["k"]))
    entries.sort(reverse=True)
    cells = "\n".join(
        f'<figure><a href="{name}"><img loading="lazy" src="{name}"></a>'
        f"<figcaption>{key}<br><b>{rating}</b> · nsfw score {score:.4f}</figcaption></figure>"
        for score, rating, name, key in entries
    )
    (report_dir / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>NSFW audit sample</title>"
        "<style>body{font:13px system-ui;background:#111;color:#ddd;margin:20px}"
        "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}"
        "figure{margin:0;background:#1c1c1c;padding:8px;border-radius:8px}"
        "img{width:100%;height:180px;object-fit:cover;border-radius:4px}"
        "figcaption{margin-top:6px;font:11px/1.5 monospace;word-break:break-all}</style>"
        f"<h1>NSFW audit sample — {len(entries)} images (sorted by score)</h1>"
        f"<main>{cells}</main>",
        encoding="utf-8",
    )


def rate_pending(pending: list[dict], args, started: float) -> tuple[dict[str, dict], list[dict], list[str]]:
    """Stream the pending rows through the classifier batch by batch."""
    import torch
    from transformers import pipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        torch.set_num_threads(max(1, os.cpu_count() or 4))
    classifier = pipeline("image-classification", model=str(args.model), device=device, top_k=None)
    print(f"classifier ready on {device}", flush=True)

    rated: dict[str, dict] = {}
    records: list[dict] = []
    failures: list[str] = []
    with open(args.output, "a", encoding="utf-8", newline="\n") as sink:
        for start in range(0, len(pending), args.batch):
            batch: list[tuple[dict, object]] = []
            for row in pending[start : start + args.batch]:
                try:
                    image = fetch_image(row)
                except Exception as error:  # noqa: BLE001 - a dead URL must not stop the pass
                    failures.append(f"{row['key']}: {error}")
                    continue
                if image is not None:
                    batch.append((row, image))
            if not batch:
                continue
            try:
                predictions = classifier([image for _, image in batch], batch_size=len(batch))
            except Exception as error:  # noqa: BLE001
                failures.extend(f"{row['key']}: {error}" for row, _ in batch)
                for _, image in batch:
                    image.close()
                continue
            for (row, image), scores in zip(batch, predictions):
                image.close()
                score = next(
                    (item["score"] for item in scores if item["label"] == NSFW_LABEL),
                    0.0,
                )
                record = {"k": row["key"], "s": round(score, 4), "r": classify(score)}
                rated[row["key"]] = record
                records.append(record)
                sink.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            sink.flush()
            done = min(start + args.batch, len(pending))
            rate = done / max(time.time() - started, 0.001)
            remaining = (len(pending) - done) / max(rate, 1e-6)
            print(
                f"rated {done}/{len(pending)} ({rate:.2f}/s, ~{remaining/60:.0f}m left)",
                flush=True,
            )
    return rated, records, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline NSFW rating pass")
    parser.add_argument("--model", help="directory with config.json + model.safetensors")
    parser.add_argument("--output", type=Path, default=RATINGS_PATH)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--sample", type=int, help="rate a random subset of N unrated images")
    parser.add_argument("--limit", type=int, help="rate at most N unrated images, in archive order")
    parser.add_argument("--report", type=Path, help="copy rated images + an HTML index here for review")
    args = parser.parse_args()

    started = time.time()
    meta, rated = read_sidecar(args.output)
    rows = image_rows()
    pending = [row for row in rows if row["key"] not in rated]
    print(f"{len(rows)} image rows, {len(rated)} already rated, {len(pending)} pending")

    if args.sample is not None:
        random.seed(42)
        pending = random.sample(pending, min(args.sample, len(pending)))
    if args.limit is not None:
        pending = pending[: args.limit]
    if not pending:
        rewrite_sidecar(args.output, meta, rated)
        print("nothing to rate; sidecar refreshed")
        return 0

    args.model = resolve_model(args.model)
    print(f"loading classifier from {args.model} ...", flush=True)
    new_rated, records, failures = rate_pending(pending, args, started)
    rated.update(new_rated)
    meta = meta | {"model": {"id": HF_MODEL_ID, "revision": model_revision(args.model)}}
    rewrite_sidecar(args.output, meta, rated)

    if args.report:
        build_report(args.report, rows, records)
        print(f"review report: {(args.report / 'index.html').resolve()}")

    counts = Counter(record["r"] for record in records)
    summary = ", ".join(f"{name}={counts.get(name, 0)}" for name in VALID_RATINGS)
    print(f"pass complete: {len(records)} rated ({summary}), {len(failures)} failed")
    for failure in failures[:5]:
        print(f"  failed: {failure}")
    if len(failures) > 5:
        print(f"  ... {len(failures) - 5} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
