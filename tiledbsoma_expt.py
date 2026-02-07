#!/usr/bin/env python3


"""

tiledbsoma_expt.py

Script to generate TileDB-SOMA experiment for the scds datasets

Usage: python tiledbsoma.expt.py /path/to/anndata_file
Arguments:
    anndata_file: The path to the anndata file (h5ad)

Example:
    tiledbsoma_expt.py /wip/scds/delivery-zips/batch14/GSE76312/deliverables_2025-05-16/Giustacchini_2017_Nat_Med-GSE76312-anndata-annotated.h5ad 

Output:
    A TileDB-SOMA experiment folder in the dataset directory (e.g. /wip/scds/delivery-zips/batch14/GSE76312/tiledbsoma_expt)

Author: Sinu Paul
Created: 2026-02-05

"""


import os
import argparse
from pathlib import Path
import tiledbsoma as soma
import tiledbsoma.io
import tiledb
import scanpy as sc
import pandas as pd
import matplotlib.pyplot as plt


def create_tiledbsoma_expt(h5ad_path):
    """
    Creates a TileDB-SOMA experiment from the provided AnnData (.h5ad) file.

    Parameters
    ----------
    h5ad_path : Path
        The path to the AnnData .h5ad file.

    This function reads the AnnData file, determines the appropriate output directory,
    and converts the data into a TileDB-SOMA experiment, saving it in the dataset directory.
    """

    adata = sc.read_h5ad(h5ad_path)

    dataset_path = h5ad_path.parent.parent
    tiledbsoma_expt_path = str(dataset_path/"tiledbsoma_expt")

    tiledbsoma.io.from_anndata(
    experiment_uri=tiledbsoma_expt_path,
    anndata=adata,
    measurement_name="RNA"
    )

    return(tiledbsoma_expt_path)


def main():
    parser = argparse.ArgumentParser(description="Generate TileDB-SOMA experiment for the scds datasets")
    parser.add_argument("h5ad_path", type=Path, help="Path to the anndata file (h5ad)")
    args = parser.parse_args()
    h5ad_path = args.h5ad_path
    if not h5ad_path.exists():
        raise FileNotFoundError(f"H5AD file not found: {h5ad_path}")
    if not h5ad_path.is_file():
        raise FileNotFoundError(f"H5AD file path is not correct: {h5ad_path}")
    if h5ad_path.suffix != '.h5ad':
        raise FileNotFoundError(f"The given file is not a h5ad file: {h5ad_path}")
    tiledbsoma_expt_path = create_tiledbsoma_expt(h5ad_path)
    print(f"TileDB-SOMA experiment has been created at {tiledbsoma_expt_path}")


if __name__ == "__main__":
    main()