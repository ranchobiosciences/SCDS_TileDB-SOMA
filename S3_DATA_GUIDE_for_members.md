# SCDS TileDB-SOMA Data — New User Guide

A guide to the single-cell data stored as [TileDB-SOMA](https://tiledbsoma.readthedocs.io/)
objects in `s3://rancho-scds-collections/`: what's there, how it's organized, and how to
start querying it.

> Metrics in this guide were captured on **2026-07-24**.

---

## 1. What's in the bucket

Everything lives under `s3://rancho-scds-collections/`, organized into three prefixes:

| Prefix | What it holds |
| --- | --- |
| `tiledb-experiments/` | The actual data. One TileDB-SOMA **Experiment** per dataset (cells × genes: counts, normalized data, cell/gene annotations, embeddings). Grouped into ingestion `batch14/` … `batch19/`. |
| `collections/` | TileDB-SOMA **Collections** — lightweight groups that *reference* a curated set of experiments. Four collections split by organism and platform: `Human_10x`, `Human_ss2`, `Mouse_10x`, `Mouse_ss2`. |
| `manifests/` | One Parquet **manifest** per collection — an aggregated index of every cell's `obs` metadata across all experiments in that collection, for fast metadata queries without opening each experiment. |

### How the pieces relate

```
tiledb-experiments/batch14/GSE76312/tiledbsoma_expt   <- physical Experiment (the data)
        ▲
        │ referenced by
collections/Human_ss2/   (a SOMA group: batch14_GSE76312, batch16_E-MTAB-6678, ...)
        │
        │ obs aggregated into
        ▼
manifests/Human_ss2_manifest.parquet   (1 row per cell, all obs columns + source tags)
```

- **Experiments** are the source of truth and hold all expression matrices.
- **Collections** are just groups of references (a few KB each) — opening a collection does
  not copy data; it points at experiments under `tiledb-experiments/`.
- **Manifests** are a flat metadata cache built from the collections. Use them to explore and
  filter cell metadata, then open the underlying experiments to pull expression data.

Not every experiment is wired into a collection: there are **189** experiments in
`tiledb-experiments/` but only **159** are currently included across the four collections. The
other **30 experiments are not in any collection** and are therefore **not reflected in the metrics
below** (which are derived from the collection manifests). These are **intentionally excluded**:
they started from **author-provided count matrices** rather than being reprocessed from raw
FASTQ through the standard SCDS pipeline, so their included genes may not be completely consistent with
the pipeline-processed datasets in the collections. Those 30 hold ~**10.0M** cells — almost as
many as the collections themselves — including several large datasets:

| Excluded store | Cells |
| --- | ---: |
| `batch19/CIMA` | 5,846,268 |
| `batch19/dat-ztfn3cc` | 851,922 |
| `batch19/GSE274546` | 644,098 |
| `batch16/LymphoMAP` | 564,146 |
| `batch15/GSE269981` | 390,756 |
| … 25 more | ~1.7M |

So the full physical footprint is ~**24.3M cells across 189 experiments**; the collection
metrics below cover the **14.27M cells in the 159 experiments starting from FASTQ**. 

---

## 2. Summary metrics

**As of 2026-07-24.** These counts cover only the **159 experiments included in the four
collections** (they're computed from the manifests). They exclude the 30 experiments described above that start from author provided counts (~10.0M additional cells) — see [What's in the bucket](#how-the-pieces-relate).

| Collection | Experiments | Cells | Genes | Median cells/expt | Max cells/expt |
| --- | ---: | ---: | ---: | ---: | ---: |
| Human_10x | 104 | 11,827,751 | 36,601 | 63,482 | 794,782 |
| Human_ss2 | 7 | 14,853 | 36,522 | 1,102 | 7,128 |
| Mouse_10x | 46 | 2,420,528 | 32,285 | 34,276 | 627,495 |
| Mouse_ss2 | 2 | 3,414 | 31,992 | 1,707 | 3,050 |
| **Total** | **159** | **14,266,546** | — | — | — |

**Storage footprint** (in `tiledb-experiments/`, the physical data):

| Metric | Value |
| --- | ---: |
| Total data size | ~225 GiB (241.6 GB) |
| S3 objects | 185,228 |
| Experiments | 189 (batches 14–19) |
| Manifest files | 4 (~1.6 GB total) |

Collections themselves are negligible in size (reference groups, a few KB each).

---

## 3. Getting set up

You need the `tiledbsoma` conda environment (includes `tiledbsoma`, `pandas`, `pyarrow`,
`s3fs`, `scanpy`) and AWS credentials with read access to the bucket.

```bash
conda env create -f tiledbsoma_environment.yml   # first time only
conda activate tiledbsoma
```

Quick check that everything works:

```python
import tiledbsoma as soma
import pandas as pd

# Read a collection's manifest straight from S3
manifest = pd.read_parquet(
    "s3://rancho-scds-collections/manifests/Human_ss2_manifest.parquet"
)
print(manifest.shape)  # (cells, columns)
```

---

## 4. Common tasks — where to look

Worked, runnable examples for all of the below are in
[`tiledbsoma_examples.ipynb`](tiledbsoma_examples.ipynb):

| I want to… | Approach |
| --- | --- |
| Explore cell metadata across a whole collection | Load its manifest with `pd.read_parquet(...)` and use normal pandas (`value_counts`, filtering, `groupby`). See the **Manifests** section. |
| Open one experiment and inspect `obs` / `var` / `X` | `soma.Experiment.open(<expt_uri>)`. See the **Experiments** section. |
| Query cells by annotation (e.g. cell type) and pull expression | `ExperimentAxisQuery` with an `obs_query` value filter → `to_anndata()`. See **Slicing and Filtering**. |
| Find which experiments contain a cell type across a collection | `query_cell_type_in_collection(...)` in the **Collections** section. |
| Find which experiments express a gene | `find_experiments_expressing_gene(...)` — uses a `var_query` (gene lives in `X`, not `obs`). See the **Collections** section. |

### Key identifiers

- **Experiment URI:** `s3://rancho-scds-collections/tiledb-experiments/<batch>/<dataset>/tiledbsoma_expt`
- **Collection URI:** `s3://rancho-scds-collections/collections/<Organism_Platform>`
- **Manifest URI:** `s3://rancho-scds-collections/manifests/<Organism_Platform>_manifest.parquet`
- **Gene identifiers** (in `var`): `var_id` / `gene_symbols` = symbol (e.g. `CD8A`); `gene_ids` = Ensembl ID.
- **Cell-type prediction** (in `obs`): `popv_prediction_ontology_name` (consensus popV call).

