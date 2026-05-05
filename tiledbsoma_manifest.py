#!/usr/bin/env python3

"""
tiledbsoma_manifest.py

Script to build or incrementally update a parquet manifest for a TileDB-SOMA collection.

The manifest is a parquet file containing an aggregate of adata.obs across all experiments
in the collection, with additional columns for the source experiment, collection name, and
per-experiment cell and gene counts. It acts as a central index for metadata queries across
the collection without needing to open individual experiments.

Usage:
    python tiledbsoma_manifest.py <collection_uri>

Arguments:
    collection_uri: URI of the TileDB-SOMA collection (local path or S3 URI).

Options:
    --manifest-path: Path to write the manifest parquet file.
                     Defaults to {collection_uri}_manifest.parquet.

Behavior:
    - If the manifest already exists, reads it to determine which experiments are already
      included and skips them (incremental update).
    - For each new experiment, reads obs, appends experiment/collection metadata columns,
      and adds it to the manifest.
    - Writes the updated manifest to the parquet file.

Examples:
    python tiledbsoma_manifest.py s3://rancho-scds-collections/collections/Human_10x
    python tiledbsoma_manifest.py s3://rancho-scds-collections/collections/Human_10x \\
        --manifest-path s3://rancho-scds-collections/manifests/Human_10x_manifest.parquet

Author: Sinu Paul
Created: 2026-04-21
"""


import argparse
import pandas as pd
import tiledbsoma as soma
import utils
from utils import is_s3_path


def _path_exists(path: str) -> bool:
    if is_s3_path(path):
        return utils._get_s3fs().exists(path)
    from pathlib import Path
    return Path(path).exists()


def main():
    parser = argparse.ArgumentParser(
        description="Build or incrementally update a parquet manifest for a TileDB-SOMA collection."
    )
    parser.add_argument(
        "collection_uri",
        type=str,
        help="URI of the TileDB-SOMA collection (local path or S3 URI)."
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        default=None,
        help="Path to write the manifest parquet file. Defaults to {collection_uri}_manifest.parquet."
    )
    args = parser.parse_args()

    collection_uri = args.collection_uri.rstrip("/")
    collection_name = collection_uri.split("/")[-1]
    manifest_path = args.manifest_path or f"{collection_uri}_manifest.parquet"

    print(f"Collection: {collection_uri}")
    print(f"Manifest path: {manifest_path}")

    # Load existing manifest to find already-processed experiments
    existing_experiments = set()
    existing_df = pd.DataFrame()
    if _path_exists(manifest_path):
        existing_df = pd.read_parquet(manifest_path)
        existing_experiments = set(existing_df["experiment"].unique())
        print(f"Found existing manifest with {len(existing_df):,} rows covering {len(existing_experiments)} experiments.")
    else:
        print("No existing manifest found — building from scratch.")

    new_chunks = []

    with soma.Collection.open(collection_uri) as coll:
        for expt_name, expt in coll.items():
            if not isinstance(expt, soma.Experiment):
                continue
            if expt_name in existing_experiments:
                print(f" - Skipping {expt_name}: already in manifest.")
                continue

            print(f" - Reading obs for {expt_name}...")
            obs_df = expt.obs.read().concat().to_pandas()
            obs_df = obs_df.drop(columns=["soma_joinid"], errors="ignore")

            n_cells = len(obs_df)
            n_genes = expt.ms["RNA"].var.count

            obs_df["experiment"] = expt_name
            obs_df["collection_name"] = collection_name
            obs_df["n_cells"] = n_cells
            obs_df["n_genes"] = n_genes

            new_chunks.append(obs_df)
            print(f"   {n_cells:,} cells, {n_genes:,} genes")

    if not new_chunks:
        print("\nNo new experiments to add. Manifest is up to date.")
        return

    new_df = pd.concat(new_chunks, ignore_index=True)
    manifest_df = pd.concat([existing_df, new_df], ignore_index=True) if not existing_df.empty else new_df

    manifest_df.to_parquet(manifest_path, index=False)
    print(f"\nManifest updated: {len(manifest_df):,} total rows, {manifest_df['experiment'].nunique()} experiments.")
    print(f"Written to: {manifest_path}")


if __name__ == "__main__":
    main()
