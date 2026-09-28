#!/usr/bin/env python3

"""
s3_data_summary.py

Print summary metrics for the TileDB-SOMA data in s3://rancho-scds-collections/.

The per-collection cell/gene/experiment counts are derived from the manifest
parquet files under manifests/ (see tiledbsoma_manifest.py), so this reads only
a few columns per manifest rather than opening every experiment.

Usage:
    python s3_data_summary.py
    python s3_data_summary.py --bucket s3://rancho-scds-collections
"""

import argparse

import pandas as pd


COLLECTIONS = ["Human_10x", "Human_ss2", "Mouse_10x", "Mouse_ss2"]


def summarize(bucket: str) -> pd.DataFrame:
    manifests_base = f"{bucket.rstrip('/')}/manifests"
    cols = ["experiment", "collection_name", "n_cells", "n_genes"]

    rows = []
    for name in COLLECTIONS:
        uri = f"{manifests_base}/{name}_manifest.parquet"
        df = pd.read_parquet(uri, columns=cols)
        per_expt = df.drop_duplicates(subset="experiment")
        rows.append(
            {
                "collection": name,
                "experiments": int(per_expt["experiment"].nunique()),
                "cells": int(len(df)),
                "genes": int(per_expt["n_genes"].iloc[0]),
                "median_cells_per_expt": int(per_expt["n_cells"].median()),
                "max_cells_per_expt": int(per_expt["n_cells"].max()),
            }
        )

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bucket",
        default="s3://rancho-scds-collections",
        help="Base S3 bucket/prefix (default: s3://rancho-scds-collections).",
    )
    args = parser.parse_args()

    summary = summarize(args.bucket)

    print(f"TileDB-SOMA data summary for {args.bucket}\n")
    print(summary.to_string(index=False))
    print(
        f"\nTOTAL: {len(summary)} collections, "
        f"{summary['experiments'].sum()} experiments, "
        f"{summary['cells'].sum():,} cells"
    )


if __name__ == "__main__":
    main()
