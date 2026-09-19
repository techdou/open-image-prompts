# Public dataset

The distributable archive is `db/prompts.db.gz`. It expands into an immutable, read-only SQLite database at runtime.

## Included tables

- `prompts`
- `images`
- `prompt_translations`
- `label_dimensions`
- `labels`
- `taxonomy_labels`
- `prompt_labels`
- `media_labels`
- `prompt_fts` and its SQLite-managed shadow tables
- `archive_config`, containing only the active public taxonomy version

Operational labeling tables and fields are intentionally absent. Public label rows contain only record IDs, taxonomy IDs, and confidence values; model names, providers, sources, evidence, run IDs, rationales, errors, leases, candidate labels, and timestamps from internal processing are not exported.

## Distribution channel

Dataset assets are published as GitHub Release assets, not Git LFS objects.
`data/dataset-manifest.json` lists every asset with the release tag it was
published under, its sha256, and its size; `scripts/fetch_dataset.py`
(also `npm run data:pull`) downloads and verifies whatever the manifest
lists. The SQLite archive lands at `db/prompts.db.gz`; monthly image packs
(`images-YYYY-MM.tar.gz`) expand into `images/`. Both paths are gitignored.

## Image selection

The dataset ships the full public corpus: every collected image row whose
file exists in the source archive is exported and packed. Image packs are an
optional download — the gallery and the skills fall back to each record's
original source URL when a local file is absent.

This is a mirror of publicly posted material with attribution, not a
statement about copyright ownership or suitability for every jurisdiction.
See `DATA_LICENSE.md` for the license split and the takedown process.

## Manifest

`data/public-corpus.json` records the dataset version, taxonomy version, row
counts, and database digest. Run `npm run verify:data` to check SQLite
integrity, DB/file correspondence for fetched packs, and image signatures.
Set `OIP_REQUIRE_IMAGES=1` to additionally require a complete image set, with
no file left over from an earlier release.

Extraction never deletes, so a release that drops records leaves its files in
`images/`. The check reports them and keeps going, because the gallery simply
never references them. Reclaim the space when you want to:

```bash
python3 scripts/fetch_dataset.py --prune
```

## Content ratings

`data/content-ratings.jsonl` is a small, committed sidecar with per-image
safety ratings produced by an offline classifier pass — it is not part of the
SQLite archive and never written at runtime. One meta line (schema version,
model id, thresholds, counts) is followed by one compact record per rated
image: `{"k":"<tweet_id>/<image_index>","s":<score>,"r":"sfw|borderline|nsfw"}`.
The API layer (`server/content_ratings.py`) reads it and attaches ratings to
`/api/prompts` responses; missing entries simply mean "not rated yet".

Regenerate or extend it with:

```bash
npm run audit:nsfw                       # rate everything still missing
npm run audit:nsfw -- --sample 100       # random subset, for calibration
```

The pass needs a local copy of the model (a directory with `config.json` +
`model.safetensors`); heavy Python dependencies (torch, transformers) are
fetched on the fly by `uv`, not added to `pyproject.toml`. Raw scores are
kept, so threshold changes never require a re-run — only a rewrite.
