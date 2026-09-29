---
name: tiledb-pipeline
description: Generate TileDB-SOMA experiments for a batch, upload them to S3, add them to collections, and update collection manifests. Use when asked to process/convert a batch to TileDB, run tiledbsoma_experiment.py / tiledbsoma_collection.py / tiledbsoma_manifest.py, upload experiments to S3, add experiments to Human_10x/Mouse_10x/etc collections, or refresh a manifest parquet.
---

# TileDB-SOMA batch pipeline

Four sequential steps per batch. Each is independently resumable — later steps
skip work already done, so re-running is safe.

```
generate  ->  upload to S3  ->  add to collections  ->  update manifests
```

## Step 0: identify the dataset group

Everything branches on this. **Always confirm which group before running
anything** — the two groups use different buckets, and a wrong bucket writes to
another group's production data.

| | `scds` | `scrnalive` |
|---|---|---|
| Input batches | `/data/batch<N>/` | `/data/scrnalive_complete/batch<N>/` |
| Local experiment root | `/data/tiledb/` | `/data/scrnalive_tiledb/` |
| S3 bucket | `s3://rancho-scds-collections` | `s3://rancho-scrna-live` |
| `--dataset-group` | `scds` (the default; omit) | `scrnalive` (must pass) |
| Standard obs columns | `batch17_universal_obs_columns.txt` (137) | `scrnalive_universal_obs_columns.txt` (116) |
| Collections | Human_10x, Human_ss2, Mouse_10x, Mouse_ss2 | + Cynomolgus_10x, Rhesus_10x |

S3 layout is identical in both buckets:

```
{bucket}/tiledb-experiments/batch<N>/<dataset>/tiledbsoma_expt/
{bucket}/collections/<CollectionName>
{bucket}/manifests/<CollectionName>_manifest.parquet
```

## Running python

In non-interactive shells `python` is **not on PATH**. Use the absolute path:

```
/home/anne.cooley/conda/envs/tiledbsoma/bin/python
```

Typed interactively by the user, plain `python` works (conda is activated by
their profile). Long steps should run in the background with output redirected
to a log.

## Step 1: generate experiments

```bash
python tiledbsoma_experiment.py /data/batch20/ \
  --output /data/tiledb/ \
  --log-file /data/tiledb/batch20.log
# scrnalive additionally needs: --dataset-group scrnalive
```

Writes to `{output}/batch<N>/<dataset>/tiledbsoma_expt`. Recursively globs for
`*annotated.h5ad`, so stray top-level files (`release.json`, `deliveryhawk.log`)
are ignored.

**Critical gotcha — never regenerate over an existing directory.** The script
uses `next_available_dir`, so if `tiledbsoma_expt` already exists it silently
writes `tiledbsoma_expt_2` instead. Anything referencing the original URI
(collections in particular) then points at stale data. Before a re-run, either
delete the old directory or skip datasets that already have one. Use
`run_batch*_missing.sh` as the template for a skip-existing wrapper.

Check for accidents: `ls -d {root}/batch<N>/*/tiledbsoma_expt_*` should be empty.

## Step 2: upload to S3

```bash
./upload_expts_to_s3.sh --group scds batch20
DRY_RUN=1 ./upload_expts_to_s3.sh --group scds batch20   # preview first
```

`--group` is required and takes `scds` or `scrnalive`; it resolves the local
root and bucket. Skips datasets already on S3, writes per-dataset logs to
`{local_root}/batch<N>_upload_logs/`, and verifies each dataset by comparing
local file count to remote object count.

Object-count verification catches truncated uploads but not content corruption.

## Step 3: add to collections

```bash
python tiledbsoma_collection.py s3://rancho-scds-collections/tiledb-experiments/batch20/ \
  --collections-path s3://rancho-scds-collections/collections/ \
  --log-file /data/tiledb/batch20_collection.log
```

Only three arguments exist: the positional path, `--collections-path`, and
`--log-file`. There is **no `--dataset-group`** — routing comes from each
experiment's own `obs` (`donor_organism` + `dataset_workflow`).

`--collections-path` is required in practice: its default
(`/wip/scds/delivery-zips/tiledbsoma_collections/`) is a stale path that does
not exist on this machine.

The positional path can be a whole batch prefix or a single
`.../<dataset>/tiledbsoma_expt` URI — use the latter to retry one dataset.

**Members are URI references, not copies.** A collection of 500+ experiments is
only a couple of MB. So regenerating an experiment at the *same* URI is picked
up automatically with no re-add. But the script is **add-only**: it skips any
`expt_name` already present (`batch<N>_<dataset>`) and can never update a
member. To repoint one, delete the member first.

### Expected skips

Expect a substantial fraction of any batch to be skipped. Check the reason:

- **`unrecognized dataset_workflow 'author_provided_counts'`** — intentional.
  Datasets built from author-provided count matrices are deliberately excluded
  because their upstream QC differs. Often 30-70% of a batch. Not a problem.
- **`unrecognized dataset_workflow '<other>'`** (e.g. `dropseq_4`) — *not*
  intentional. `workflow_map` only knows `smartseq` and `cellranger`. Needs a
  human decision about which collection suffix applies before adding a mapping.
- **`gene count mismatch`** — compare against `CELLRANGER_EXPECTED_GENES` /
  `SS2_EXPECTED_GENES`. If the count is legitimately different for that dataset,
  add it to `SS2_DATASET_EXCEPTIONS`, then re-run on just that experiment URI.
- **`mixed donor_organism` / `mixed dataset_workflow` / all-null** — data
  problem upstream; report rather than work around.
- **`var columns inconsistent`** — schema drift against the collection's
  existing members.

## Step 4: update manifests

```bash
python tiledbsoma_manifest.py s3://rancho-scds-collections/collections/Mouse_10x \
  --manifest-path s3://rancho-scds-collections/manifests/Mouse_10x_manifest.parquet \
  > ~/Mouse_10x_manifest.log 2>&1
```

**Only run this for collections that actually gained members** in step 3. For
others it is a no-op. Determine which by diffing collection membership against
manifest contents (see Verification below).

This script has **no `--log-file`** — redirect the shell instead. The user
prefers manifest logs in their home directory.

Run collections **sequentially, smallest first**. The script loads the entire
existing manifest into pandas, concatenates, and rewrites it; Human_10x is
>1.5 GB and several tens of millions of rows. Two at once risks exhausting
memory.

Neither bucket has versioning enabled, so the parquet write is **irreversible**.

Known wart: `obs_df.replace("NA", np.nan)` normalizes literal `"NA"` strings,
but only for newly appended rows — rows written before that change are
untouched, so null handling is inconsistent across a manifest's history. It also
emits a pandas `FutureWarning` on categorical columns and will become a no-op in
a future pandas.

## Verification

Do not rely on exit codes or log lines alone — read the result back.

```bash
# Step 1: every input dataset produced an experiment, no _2 duplicates
ls -d /data/tiledb/batch20/*/tiledbsoma_expt | wc -l
ls -d /data/tiledb/batch20/*/tiledbsoma_expt_* 2>/dev/null

# Step 2: local file count == remote object count
aws s3 ls s3://<bucket>/tiledb-experiments/batch20/<ds>/tiledbsoma_expt/ --recursive | grep -c .
find /data/tiledb/batch20/<ds>/tiledbsoma_expt -type f | wc -l
```

```python
# Steps 3 and 4: collections vs manifests, per collection
import tiledbsoma as soma, pandas as pd
BUCKET = "rancho-scds-collections"
for c in ["Human_10x", "Human_ss2", "Mouse_10x", "Mouse_ss2"]:
    with soma.Collection.open(f"s3://{BUCKET}/collections/{c}") as coll:
        members = set(coll.keys())
    df = pd.read_parquet(f"s3://{BUCKET}/manifests/{c}_manifest.parquet",
                         columns=["experiment"])
    in_manifest = set(df["experiment"].unique())
    print(f"{c}: collection={len(members)} manifest={len(in_manifest)} "
          f"rows={len(df):,} missing={len(members - in_manifest)} "
          f"stale={len(in_manifest - members)}")
```

Also spot-check that a new experiment opens and has sane counts:

```python
with soma.Experiment.open(uri) as e:
    print(e.obs.count, e.ms["RNA"].var.count)
```

## Reporting

State counts explicitly: generated, uploaded, added, skipped — and always give
the skip *reasons*, separating intentional author-counts exclusions from
genuine gaps that need a decision. "Batch N is done" is misleading when a third
of it was skipped.
